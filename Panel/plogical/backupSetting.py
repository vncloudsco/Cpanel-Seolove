#!/usr/bin/env python3

from backupManager.models import BackupLog
from websiteManager.models import Provision
import os
import sys
import shutil
import pathlib
import rclone
from datetime import datetime
import re
import django
from plogical.phpSetting import execute, execute_outputfile
from django.core.exceptions import ObjectDoesNotExist
import threading


class BackupManager:

    def __init__(self, argv=None):
        self.provi = argv
        self.log = '/home/kusanagi/'+argv+'/log/backup.log'
        self.pwrd = self.get_root_pass()
        self.dbinfo = Provision.objects.get(provision_name='%s' % self.provi)
    
    @staticmethod
    def append_log(log, message):
        f = open(log, "a+")
        today = datetime.now()
        f.write("%s %s \n" % (today.strftime("%Y-%m-%d %H:%M:%S"), message))
        f.close()
    
    @staticmethod
    def get_root_pass():
        pwrd = None
        try:
            with open("/root/.my.cnf") as fp: lines = fp.read().splitlines()
            for line in lines:
                grep = re.findall(r'password', line)
                if grep:
                    pwrd = line.split('"')[1]
        except FileNotFoundError:
            return False
        return pwrd

    def backup_db(self):
        db_name = self.dbinfo.db_name
        try:
            sqldir = '/home/kusanagi/%s/sql_backup/' % self.provi
            p = pathlib.Path(sqldir)
            if not p.exists():
                p.mkdir(mode=0o775, parents=True, exist_ok=True)
                shutil.chown(sqldir, 'kusanagi', 'www')
        except BaseException as error:
            print(error)

        mess = 'Back up database ' + db_name
        self.append_log(self.log, mess)

        cmd = 'mysqldump --single-transaction -p' + self.pwrd + ' --databases ' + db_name + ' | gzip > ' + sqldir + db_name + '.sql.gz'
        execute_outputfile(cmd, self.log)

    def update_backup_record(self, backup_type, result):
        provi_id = self.dbinfo.id
        try:
            record = BackupLog.objects.get(provision_id='%d' % provi_id, status='0', backup_type='%d' % backup_type)
        except ObjectDoesNotExist as error:
            print(error)
            return False

        if result:
            record.status = 1
            record.message = 'Done'
        else:
            record.status = -1
            record.message = 'Failed. See %s' % self.log

        record.save()

    def compress_provision_dir(self, chdir=None):
        date = datetime.now()
        today = date.strftime("%Y-%m-%d")
        if chdir:
            p = pathlib.Path(chdir)
            if not p.exists():
                p.mkdir(mode=0o775, parents=True, exist_ok=True)
                shutil.chown(chdir, 'kusanagi', 'www')
            tarname = chdir + self.provi + '.' + today
        else:
            tarname = '/home/kusanagi/backup/' + self.provi + '.' + today
        source_dir = '/home/kusanagi/' + self.provi
        shutil.make_archive(tarname, "gztar", source_dir)
        shutil.chown('%s.tar.gz' % tarname, 'kusanagi', 'www')
        return tarname

    def local_backup(self, chdir=None):
        self.append_log(self.log, '--- Local backup')
        self.backup_db()
        tarname = self.compress_provision_dir(chdir)

        tar_file = pathlib.Path(tarname + '.tar.gz')
        if tar_file.exists():
            self.update_backup_record(0, 1)
            # return {'status': 1, 'msg': 'Backup completed successfully'}
        else:
            self.update_backup_record(0, 0)
            # return {'status': 0, 'msg': 'Not found backed up file'}

    def check_ssh_conn(self, remote_user, remote_host, remote_port, remote_pass):
        cmd = 'sshpass -p "' + remote_pass + '" ssh -o StrictHostKeyChecking=no -p ' + remote_port + ' -q ' + remote_user + '@' + remote_host + ' exit;echo $?'
        res = execute(cmd)
        if int(res) == 0:
            # print('Connect OK \n')
            pass
        else:
            self.append_log(self.log, 'Remote connection failed. Can not issue remote backup')
            self.update_backup_record(1, 0)
            # return {'status': 0, 'msg': 'Remote connection failed'}
            sys.exit(1)

    def remote_backup(self, remote_user, remote_host, remote_port, remote_pass, remote_dest):

        self.append_log(self.log, '--- Remote backup')
        self.check_ssh_conn(remote_user, remote_host, remote_port, remote_pass)
        self.backup_db()
        tarname = self.compress_provision_dir('/home/kusanagi/')

        conf_ssh = '/etc/ssh/ssh_config'
        with open(conf_ssh) as fp:
            lines = fp.read().splitlines()
        for line in lines:
            grep = re.findall(remote_host, line)
            if grep:
                break
        if not grep:
            # configure stricthostkey ssh
            f = open(conf_ssh, "a+")
            f.write('Host %s\n\tStrictHostKeyChecking no\n' % remote_host)
            f.close()

        cmd = 'sshpass -p "' + remote_pass + '" rsync --remove-source-files -azhe \'ssh -p' + remote_port + '\' ' + tarname + '.tar.gz ' + remote_user + '@' + remote_host + ':' + remote_dest + ' 2>> ' + self.log + ' ; echo $?'
        res = execute(cmd)

        if int(res) == 0:
            self.update_backup_record(1, 1)
            # return {'status': 1, 'msq': 'Backup completed successfully'}
        else:
            self.update_backup_record(1, 0)
            # return {'status': 0, 'msg': 'Check %s for more details' % self.log}

    def drive_backup(self, drive_dir=None):

        self.append_log(self.log, '--- Backup to Google Drive')
        self.backup_db()
        tarname = self.compress_provision_dir('/home/kusanagi/')

        cfg_file = '/root/.config/rclone/rclone.conf'
        with open(cfg_file, 'rt') as f:
            cfg = f.read()
        # rc_options = ['--buffer-size=64M', '--transfers=5', '--drive-chunk-size=16M', '--drive-upload-cutoff=16M',
        #              '--log-file=%s' % self.log]
        rc_options = ['--buffer-size=64M', '--log-level=INFO', '--log-file=%s' % self.log]
        result = rclone.with_config(cfg).copy('%s.tar.gz' % tarname, 'GGD1:%s' % drive_dir, rc_options)
        res = result.get('code')
        if int(res) == 0:
            self.update_backup_record(2, 1)
            # return {'status': 1, 'msq': 'Backup completed successfully'}
        else:
            self.update_backup_record(2, 0)
            # return {'status': 0, 'msg': 'Check %s for more details' % self.log}
        os.remove('%s.tar.gz' % tarname)

    def initial_backup_record(self, backup_type):
        provi_id = self.dbinfo.id
        new_record = BackupLog(provision_id='%s' % provi_id, status='0', backup_type='%s' % backup_type)
        new_record.save()

    def delete_old_local_backup(self, chdir=None, number=999):
        count = 0
        pattern = chdir+self.provi+'\.\d+'
        regex = re.compile(pattern)
        filelist = []
        for root, dirs, files in os.walk(chdir):
            for name in files:
                if regex.match(os.path.join(root, name)):
                    count = count + 1
                    filelist.append(os.path.join(root, name))
        left = count - number
        filelist.sort(key=os.path.getmtime)
        for i in range(left):
            os.remove(filelist[i])

    def run_thread(self, name_fuc='local_backup', params=None):
        if name_fuc == 'local_backup':
            t = threading.Thread(target=self.local_backup)
        elif name_fuc == 'remote_backup':
            t = threading.Thread(target=self.remote_backup, args=params)
        elif name_fuc == 'drive_backup':
            t = threading.Thread(target=self.drive_backup, args=params)
        t.start()


class BackupAllProvision:

    def __init__(self):
        self.password = BackupManager.get_root_pass()
        self.pro_list = Provision.objects.filter(deactive_flg="0")

    def local_backup(self, chdir=None):
        for k in self.pro_list:
            BackupManager(k.provision_name).initial_backup_record(0)
            BackupManager(k.provision_name).local_backup(chdir)

    def remote_backup(self, remote_user, remote_host, remote_port, remote_pass, remote_dest):
        for k in self.pro_list:
            BackupManager(k.provision_name).initial_backup_record(1)
            BackupManager(k.provision_name).remote_backup(remote_user, remote_host, remote_port, remote_pass, remote_dest)

    def drive_backup(self, drive_dir):
        for k in self.pro_list:
            BackupManager(k.provision_name).initial_backup_record(2)
            BackupManager(k.provision_name).drive_backup(drive_dir)

    def delete_old_local_backup_all_provision(self, chdir=None, number=999):
        for k in self.pro_list:
            BackupManager(k.provision_name).delete_old_local_backup(chdir, number)
