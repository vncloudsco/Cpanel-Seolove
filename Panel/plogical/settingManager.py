#!/usr/bin/env python3

import os
import subprocess
import re
import glob
import shutil
import pathlib
import urllib.parse
import plogical.functionLib as fLib
from plogical.phpSetting import execute
from django.conf import settings
from lib.common import write_log


class SettingManager:

    def __init__(self, provision=None):
        self.provision = provision
        self.path = '/etc/nginx/conf.d/%s_*.conf' % self.provision
        self.template_file = '/etc/nginx/restrict_access/rule.template'
        self.filter_template_file = '/etc/nginx/restrict_rule/rule.template'
        self.app_id = fLib.get_app_id(self.provision)
        self.kusanagi_dir = '/home/kusanagi/%s' % self.provision

    @staticmethod
    def check_existence_in_file(pattern, source_files):
        regex = re.compile(pattern)
        for fi in glob.glob(source_files):
            with open(fi, 'rt') as fp: lines = fp.read().splitlines()
            for line in lines:
                if regex.search(line):
                    return True
        return False

    def backup_nginx_conf(self):
        for fi in glob.glob(self.path):
            shutil.copy(fi, '/etc/backup_restrict/')

    def rollback_nginx_only(self):
        bk_path = '/etc/backup_restrict/%s_*' % self.provision
        for fi in glob.glob(bk_path):
            shutil.copy(fi, '/etc/nginx/conf.d/')

    @staticmethod
    def replace_multiple(input_file=None, output_file=None, pattern=None, replacement=None):
        f = open(input_file, 'rt')
        g = open(output_file, 'wt')
        for line in f:
            for pat, rep in zip(pattern, replacement):
                line = line.replace(pat, rep)
            g.write(line)
        f.close()
        g.close()

    @staticmethod
    def replace_multiple_in_file(file_path=None, pattern=None, replacement=None):
        for fi in glob.glob(file_path):
            with open(fi, 'rt') as f:
                g = open('/opt/tmp_nginx.conf', 'wt')
                for line in f:
                    for pat, repl in zip(pattern, replacement):
                        line = re.sub(pat, repl, line)
                    g.write(line)
            g.close()
            shutil.copy('/opt/tmp_nginx.conf', fi)

    def inject_rule_to_nginx(self, anchor_string=None, file_included=None):
        for fi in glob.glob(self.path):
            f = open(fi, 'rt')
            data = f.read()
            data = data.replace(anchor_string, '%s \n\tinclude %s;' % (anchor_string, file_included))
            f.close()
            f = open(fi, 'wt')
            f.write(data)
            f.close()

    def add_authentication(self, url=None, user=None, password=None, rule_id=None):
        # if not fLib.verify_prov_existed(self.provision):
        #    return False
        # if not fLib.verify_nginx_prov_existed(self.provision):
        #    return False
        if self.check_existence_in_file('au_%s_%s' % (self.provision, rule_id), self.path):
            print('the rule authentication ID already existed')
            return False
        if os.path.isfile('/etc/nginx/restrict_access/au_%s_%s' % (self.provision, rule_id)):
            print('the authentication file already existed')
            return False
        if os.path.isfile('/etc/nginx/restrict_access/user_%s_%s' % (self.provision, rule_id)):
            print('the user conf file already existed')
            return False
        self.backup_nginx_conf()

        output_file = '/etc/nginx/restrict_access/au_%s_%s' % (self.provision, rule_id)

        if url == 'wp-admin':
            pattern = ('location', '#auth_basic', '#auth_basic_user_file', 'provision_name', '}')
            replacement = ('#location', 'auth_basic', 'auth_basic_user_file', 'user_%s_%s' % (self.provision, rule_id), '#}')
            self.replace_multiple(self.template_file, output_file, pattern, replacement)
            fLib.execute('htpasswd -nb  %s %s > /etc/nginx/restrict_access/user_%s_%s' % (user, password, self.provision, rule_id))
            self.inject_rule_to_nginx('#Restric filter here', output_file)
        elif url == 'wp-login':
            print('can not add restriction rule to wp-login url')
            return False
        else:
            if self.check_existence_in_file(url, self.path):
                print(' the %s location has been added' % url)
                return False
            else:
                pattern = ('url', '#auth_basic', '#auth_basic_user_file', 'provision_name')
                replacement = (url, 'auth_basic', 'auth_basic_user_file', 'user_%s_%s' % (self.provision, rule_id))
                self.replace_multiple(self.template_file, output_file, pattern, replacement)
                fLib.execute('htpasswd -nb  %s %s > /etc/nginx/restrict_access/user_%s_%s' % (user, password, self.provision, rule_id))
                self.inject_rule_to_nginx('#Addnew Restrict Filter', output_file)

        nginx_check = fLib.check_nginx_valid()
        if nginx_check == 0:
            fLib.reload_service('nginx')
            print('Done')
            return True

        self.rollback_nginx_only()
        os.remove(output_file)
        os.remove('/etc/nginx/restrict_access/user_%s_%s' % (self.provision, rule_id))
        return False

    def add_filterip(self, url=None, ip_address=None, rule_id=None):

        self.backup_nginx_conf()
        if self.check_existence_in_file('filter_%s_%s' % (self.provision, rule_id), self.path):
            print('the filter ID already existed')
            return False

        output_file = '/etc/nginx/restrict_rule/filter_%s_%s' % (self.provision, rule_id)

        if url == 'wp-admin':
            pattern = ('location', '#deny all', '#allow ipas', '}')
            replacement = ('#location', 'deny all', 'allow %s' % ip_address, '#}')
            self.replace_multiple(self.filter_template_file, output_file, pattern, replacement)
            self.inject_rule_to_nginx('#Restric filter here', output_file)
        elif url == 'wp-login':
            print('can not add restriction rule to wp-login url')
            return False
        else:
            if self.check_existence_in_file(url, self.path):
                print(' the %s location has been added' % url)
                return False
            else:
                pattern = ('url', '#deny all', '#allow ipas')
                replacement = (url, 'deny all', 'allow %s' % ip_address)
                self.replace_multiple(self.filter_template_file, output_file, pattern, replacement)
                self.inject_rule_to_nginx('#Addnew Restrict Filter', output_file)

        nginx_check = fLib.check_nginx_valid()
        if nginx_check == 0:
            fLib.reload_service('nginx')
            print('Done')
            return True

        self.rollback_nginx_only()
        os.remove(output_file)
        return False

    def remove_conf_related_nginx(self, pat=None):
        for fi in glob.glob(self.path):
            f = open(fi, 'rt')
            # g = open(self.tmp_file, 'wt')
            g = open('/opt/tmp_nginx.conf', 'wt')
            for line in f:
                if pat not in line:
                    g.write(line)
            f.close()
            g.close()
            shutil.copy('/opt/tmp_nginx.conf', fi)
        os.remove('/opt/tmp_nginx.conf')

    def delete_authentication(self, url=None, rule_id=None):

        self.backup_nginx_conf()

        if not self.check_existence_in_file('au_%s_%s' % (self.provision, rule_id), self.path):
            print('Not found the rule authentication ID as %s' % rule_id)
            return False

        if url == 'wp-login':
            print('can not configure wp-login url')
            return False
        else:
            self.remove_conf_related_nginx('au_%s_%s' % (self.provision, rule_id))

        nginx_check = fLib.check_nginx_valid()
        if nginx_check == 0:
            os.remove('/etc/nginx/restrict_access/user_%s_%s' % (self.provision, rule_id))
            os.remove('/etc/nginx/restrict_access/au_%s_%s' % (self.provision, rule_id))
            print('Done')
            fLib.reload_service('nginx')
            return True
        else:
            print('NGINX config check failed')
            self.rollback_nginx_only()
            return False

    def delete_filterip(self, url=None, rule_id=None):

        self.backup_nginx_conf()

        if url == 'wp-login':
            print('can not configure wp-login url')
            return False
        else:
            if not self.check_existence_in_file('filter_%s_%s' % (self.provision, rule_id), self.path):
                print('Not found the rule ID as %s in nginx config' % rule_id)
                return False
            else:
                self.remove_conf_related_nginx('filter_%s_%s' % (self.provision, rule_id))

        nginx_check = fLib.check_nginx_valid()
        if nginx_check == 0:
            os.remove('/etc/nginx/restrict_rule/filter_%s_%s' % (self.provision, rule_id))
            print('Done')
            fLib.reload_service('nginx')
            return True
        else:
            print('NGINX config check failed')
            self.rollback_nginx_only()
            return False

    def before_edit_nginx(self):

        nginx_check = fLib.check_nginx_valid()
        if nginx_check > 0:
            print('nginx config check failed. Please abort')
            return False
        else:
            if not fLib.verify_nginx_prov_existed(self.provision):
                return False
            else:
                for fi in glob.glob(self.path):
                    shutil.copy(fi, '/etc/nginx/bk_nginx_conf/')
                    shutil.copy(fi, '/etc/temp_nginx_conf/')
                shutil.chown('/etc/temp_nginx_conf/', 'httpd', 'www')
                for root, dirs, files in os.walk('/etc/temp_nginx_conf/'):
                    for name in files:
                        shutil.chown(os.path.join(root, name), 'httpd', 'www')
                return True

    def edit_nginx(self, domain_name):

        if not os.path.isfile('/etc/temp_nginx_conf/%s_http.conf' % self.provision) \
                or not os.path.isfile('/etc/temp_nginx_conf/%s_ssl.conf' % self.provision):
            print('No temporary nginx file exists. Please backup firstly')
            return False
        # check new nginx conf right after editing
        for fi in glob.glob('/etc/temp_nginx_conf/%s_*.conf' % self.provision):
            shutil.copy(fi, '/etc/nginx/conf.d/')
        nginx_check = fLib.check_nginx_valid()
        if nginx_check > 0:
            # rollback
            for fi in glob.glob('/etc/nginx/bk_nginx_conf/%s_*.conf' % self.provision):
                shutil.copy(fi, '/etc/nginx/conf.d/')
            print('Insert failed. Might your conf is invalid')
            return False
        else:
            # if editing nginx okie, apply new conf
            nginx_check = fLib.check_nginx_valid()
            if nginx_check == 0:
                fLib.reload_service('nginx')
                return True
            else:
                print('nginx conf check failed. Please run "nginx -t" for more details')
                return False

    @staticmethod
    def replace_in_file(regex_pattern, replacement, file_path):
        regex = re.compile(regex_pattern)
        for fi in glob.glob(file_path):
            f = open(fi, 'rt')
            g = open('/opt/tmp_nginx.conf', 'wt')
            for line in f:
                line = regex.sub(replacement, line)
                g.write(line)
            f.close()
            g.close()
            shutil.copy('/opt/tmp_nginx.conf', fi)
        os.remove('/opt/tmp_nginx.conf')

    def f_cache(self, action=None, uri=None):
        if action == 'status':
            pat = r"set\s* \$do_not_cache\s*0\s*;\s*#+\s*page\s*cache"
            if self.check_existence_in_file(pat, '/etc/nginx/conf.d/%s_http.conf' % self.provision):
                return 'on'
            else:
                return 'off'
        if action == 'on':
            print('Turning on')
            pat = r'set\s+\$do_not_cache\s+1\s*;\s+#+\s+page\s+cache'
            repl = r'set $do_not_cache 0; ## page cache'
            self.replace_in_file(pat, repl, self.path)
        if action == 'off':
            print('Turning off')
            pat = r'set\s+\$do_not_cache\s+0\s*;\s*#+\s*page\s*cache'
            repl = r'set $do_not_cache 1; ## page cache'
            self.replace_in_file(pat, repl, self.path)
        if action == 'clear':
            print('Clearing cache')
            nginx_cache_dir = '/var/cache/nginx/wordpress'
            p = pathlib.Path(nginx_cache_dir)
            if p.exists():
                res = fLib.execute('ls -dl %s | wc -l' % nginx_cache_dir) # meo hieu de lam gi
                if p.owner() == 'httpd' and int(res) == 1:
                    fqdn = fLib.get_fqdn(self.provision)
                    if uri:
                        url_unicode = urllib.parse.quote(uri)
                        if not url_unicode.startswith('/', 0, 1):
                            url_unicode = '/%s' % url_unicode
                        command = 'grep -i -a -r -m 1 -E "^KEY.*:https?://%s%s" %s' % (
                        fqdn, url_unicode, nginx_cache_dir)
                        try:
                            res = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE, universal_newlines=True)
                            g = open('/opt/tmp_nginx.conf', 'w')
                            g.write(res.stdout)
                            g.close()
                            g = open('/opt/tmp_nginx.conf', 'r')
                            for line in g:
                                binary_file = line.replace(':KEY:', '').split()[0]
                                os.remove(binary_file)
                            g.close()
                        except subprocess.CalledProcessError as error:
                            if error.returncode > 0:
                                print("URL has not been cached")
                                return True
                    else:
                        command = 'grep -r -E "%s" %s' % (fqdn, nginx_cache_dir)
                        try:
                            res = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE, universal_newlines=True)
                            g = open('/opt/tmp_nginx.conf', 'w')
                            g.write(res.stdout)
                            g.close()
                            g = open('/opt/tmp_nginx.conf', 'r')
                            for line in g:
                                binary_file = line.split()[2]
                                os.remove(binary_file)
                            g.close()
                        except subprocess.CalledProcessError as error:
                            if error.returncode > 0:
                                print("No cache found")
                                return True
            else:
                print('Nginx cache dir %s is not found' % nginx_cache_dir)
                return False

        nginx_check = fLib.check_nginx_valid()
        if nginx_check == 0:
            fLib.reload_service('nginx')
            print('Done')
            return True
        else:
            print('Nginx conf check failed. Please run "nginx -t" for more details')
            return False

    def b_cache(self, action=None, uri=None):
        if not pathlib.Path(self.kusanagi_dir).exists():
            print("%s is not found" % self.kusanagi_dir)
            return False
        wpconfig = None
        if self.app_id == "WordPress":
            if os.path.isfile('%s/wp-config.php' % self.kusanagi_dir):
                wpconfig = '%s/wp-config.php' % self.kusanagi_dir
            elif os.path.isfile('%s/DocumentRoot/wp-config.php' % self.kusanagi_dir):
                wpconfig = '%s/DocumentRoot/wp-config.php' % self.kusanagi_dir
            else:
                wpconfig = ""
        if wpconfig == "":
            print("WordPress is not installed. Nothing to do")
            return False
        regex = re.compile(r"^.*define\('WP_CACHE'")
        count = 0
        with open(wpconfig, 'r') as f:
            for line in f:
                if regex.search(line):
                    count += 1
        if count > 1 or count == 0:
            print('None or multiple WP_CACHE constant')
            # return False
            return 'mul'

        if action == 'status':
            pat = r"^\s*define\s*\(\s*'WP_CACHE'\s*,\s*true"
            if self.check_existence_in_file(pat, wpconfig):
                return 'on'
            else:
                return 'off'

        if action == 'on':
            print('Turning on')
            pat = r"^\s*#+\s*define\s*\(\s*'WP_CACHE'.*$"
            repl = r"define('WP_CACHE', true);"
            self.replace_in_file(pat, repl, wpconfig)
        if action == 'off':
            print('Turning off')
            pat = r"^\s*define\('WP_CACHE'.*$"
            repl = r"#define('WP_CACHE', true);"
            self.replace_in_file(pat, repl, wpconfig)
        if action == 'clear':
            print('Clearing cache')
            os.chdir('%s/tools' % self.kusanagi_dir)
            command = 'php ./bcache.clear.php %s' % uri
            fLib.execute(command)
        print('Done')
        return True


class Waf(SettingManager):

    def install_httpd_waf_modules(self):
        e = fLib.yum_install('kusanagi-httpd-waf')
        fLib.yum_install('mod_security')
        fLib.yum_install('mod_security_crs')
        crs_conf = '/etc/httpd/modsecurity.d/modsecurity_crs_10_config.conf'
        if os.path.isfile(crs_conf):
            pat = r"HTTP/0.9 HTTP/1.0 HTTP/1.1'"
            repl = r"HTTP/0.9 HTTP/1.0 HTTP/1.1 HTTP/2.0'"
            self.replace_in_file(pat, repl, crs_conf)
        if pathlib.Path('/var/lib/mod_security').exists():
            shutil.chown('/var/lib/mod_security', 'httpd', 'www')
        if not os.path.isfile('/var/lib/mod_security/global'):
            pathlib.Path('/var/lib/mod_security/global').touch()
        if not os.path.isfile('/var/lib/mod_security/ip'):
            pathlib.Path('/var/lib/mod_security/ip').touch()
        return e

    def perform(self, action=None):
        nginx_waf_root_conf = '/etc/nginx/conf.d/kusanagi_naxsi_core.conf'
        apache_waf_root_conf = '/etc/httpd/conf.d/mod_security.conf'
        waf_comment = '#kusanagi_comment_do_not_delete;'

        if action == 'status':
            if fLib.is_active('nginx') == 0 and os.path.isfile(nginx_waf_root_conf) \
                    and not self.check_existence_in_file('#kusanagi_comment_do_not_delete;', nginx_waf_root_conf):
                return 'on'
            elif fLib.is_active('httpd') == 0 and os.path.isfile(apache_waf_root_conf) \
                    and not self.check_existence_in_file('#kusanagi_comment_do_not_delete;', apache_waf_root_conf):
                return 'on'
            else:
                return 'off'

        if action == 'on':
            print('Turning on')
            pat = waf_comment
            repl = ''
            self.replace_in_file(pat, repl, nginx_waf_root_conf)
            pat = r'#+\t*\s*include\t*\s*(naxsi\.d/.*)'
            repl = r'include \1'
            self.replace_in_file(pat, repl, '/etc/nginx/conf.d/*_http.conf')
            self.replace_in_file(pat, repl, '/etc/nginx/conf.d/*_ssl.conf')
            # http-install mod security modules
            if self.install_httpd_waf_modules() == 0:
                pat = waf_comment
                repl = ''
                self.replace_in_file(pat, repl, apache_waf_root_conf)
                pat = (r'#+[ \t]*IncludeOptional[ \t]+(modsecurity\.d/.*)', r'#+[ \t]*SecAuditLog[ \t]+(.*)')
                repl = (r'IncludeOptional \1', r'SecAuditLog \1')
                self.replace_multiple_in_file('/etc/httpd/conf.d/*_http.conf', pat, repl)
                self.replace_multiple_in_file('/etc/httpd/conf.d/*_ssl.conf', pat, repl)

        if action == 'off':
            print('Turning off')
            pat = r'^'
            repl = r'#kusanagi_comment_do_not_delete;'
            self.replace_in_file(pat, repl, nginx_waf_root_conf)
            self.replace_in_file(pat, repl, apache_waf_root_conf)
            pat = r'([^#]+)include[ \t]+(naxsi\.d/.*)'
            repl = r'\1#include \2'
            self.replace_in_file(pat, repl, '/etc/nginx/conf.d/*_http.conf')
            self.replace_in_file(pat, repl, '/etc/nginx/conf.d/*_ssl.conf')
            pat = (r'([^#]+)IncludeOptional[ \t]+(modsecurity\.d/.*)', r'([^#]+)SecAuditLog[ \t]+(.*)')
            repl = (r'\1#IncludeOptional \2', r'\1#SecAuditLog \2')
            self.replace_multiple_in_file('/etc/httpd/conf.d/*_http.conf', pat, repl)
            self.replace_multiple_in_file('/etc/httpd/conf.d/*_ssl.conf', pat, repl)

        fLib.reload_service('httpd')
        if fLib.check_nginx_valid() == 0:
            fLib.reload_service('nginx')
            print('Done')
            return True
        else:
            print('Nginx conf check failed.')
            return False

def updateBash():
    """
    function call script update bash shell
    :return:
    """
    write_log(os.path.join(settings.DIR_LOG, 'update_bash.log'), '-------------start----------------')
    res = execute('curl http://initial.secureweb.vn/update_priv_host_kscript.sh |sh')
    write_log(os.path.join(settings.DIR_LOG, 'update_bash.log'), "LOG_BAH: {}".format(res))

def updatePanel():
    """
    function call script update code panel
    :return:
    """
    write_log(os.path.join(settings.DIR_LOG, 'update_bash.log'), '-------------start----------------')
    res = execute('curl http://initial.secureweb.vn/update_priv_host_panel.sh |sh')
    write_log(os.path.join(settings.DIR_LOG, 'update_panel.log'),"LOG_BAH: {}".format(res))


