from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect, HttpResponse,JsonResponse
from loginSys.models import Account
from websiteManager.models import Provision
from plogical import hashPassword,website,settingManager,sslSetting,phpSetting
import json
from .forms import CreateWebsiteForm
import urllib.request
import websiteManager.define as define
import bcrypt
import re,socket
from django.utils import timezone
from django.core import serializers
from django.conf import settings
import mysql.connector as MySQLdb
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
import os.path

def createWebsite(request):
    try:
        userId = request.session['userID']
        account = Account.objects.get(id=userId)
        form = CreateWebsiteForm(initial={'app_id': 1,'account_id': userId,'email': account.email,'db_password': hashPassword.generate_pass(10)})
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/create_website.html', {'form': form, 'account': account, 'page_title': 'Create Website'})

def createProvision(request):
    """
    create provision website ajax action
    :param request:
    :return:
    """
    data_result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        account = Account.objects.get(id=userId)
        if request.method == 'POST':
            data = request.POST.copy()
            form = CreateWebsiteForm(data)
            if form.is_valid():
                pro = form.save(commit=False)
                proName = generateProvision(data['domain'])
                # call Shell create Account
                ws = website.Website(proName)
                result = ws.createWebsite(data)
                if result['status']:
                    pro.username = account.login_id
                    pro.provision_name = proName
                    pro.account_id = userId
                    pro.save()
                    data_result['status'] = 1
                else:
                    raise KeyError(result['msg'])
            else:
                data_result['errors'] = form.errors
                data_result['msg'] = 'Params is validate! Please check value'
    except KeyError as msg:
        data_result['msg'] = str(msg)+' Key Error!'

    return HttpResponse(json.dumps(data_result))

def index(request):
    """
    list website
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/index.html', {'page_title': 'Website Setting'})

def listDomain(request):
    try:
        userId = request.session['userID']
        provisions = Provision.objects.filter(account_id=userId, deactive_flg=0)
        count = provisions.count()
        php_current = phpSetting.phpManager.get_current_ver()
        list_php = {
            'php53': 'PHP 5.3',
            'php': 'PHP 5.6',
            'php70': 'PHP 7.0',
            'php71': 'PHP 7.1',
            'php72': 'PHP 7.2',
            'php73': 'PHP 7.3',
            'php74': 'PHP 7.4',
        }
        if php_current not in list_php.keys():
            php_current = 'php70'
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/list_website.html',{'provisions':provisions,'count': count,'php_current': list_php[php_current]})

def deleteProvision(request):
    """
    Delete Provision
    :param request:
    :return:
    """
    data_result = {'status':0,'msg':''}
    try:
        userId = request.session['userID']
        account = Account.objects.get(pk=userId)
        if request.POST:
            pro = Provision.objects.get(pk=request.POST['id'],account_id=userId,deactive_flg=0)
            if not pro:
                data_result['msg'] = 'Provision is not exits!'
                return HttpResponse(json.dumps(data_result))
            ws = website.Website(pro.provision_name)
            result = ws.deleteWebsite()
            if result['status']:
                pro.delete()
                data_result['status'] = 1
                data_result['msg'] = 'Delete provision {} is success!'.format(pro.provision_name)
            else:
                data_result['msg'] = result['msg']
        else:
            return HttpResponseRedirect('/websites/')
    except KeyError:
        return HttpResponseRedirect('/login')

    return HttpResponse(json.dumps(data_result))

def cacheManager(request):
    """
    list website action cache
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        provisions = Provision.objects.filter(account_id=userId,deactive_flg=0)
        count = provisions.count()
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/list_website_cache.html',{'provisions': provisions, 'count': count, 'page_title': 'Cache Manager'})

def showCache(request,pro_id=None):
    """
    show cache type provision
    :param request:
    :param pro_id:
    :return:
    """
    result = {'status': 0,'msg': ''}
    try:
        userId = request.session['userID']
        provision = Provision.objects.get(pk=pro_id,account_id=userId, deactive_flg=0)
        if request.POST:
            type_cache = int(request.POST['type'])
            Cache = settingManager.SettingManager(provision.provision_name)
            if type_cache == 1:
                status = Cache.f_cache(action='status')
            elif type_cache == 2:
                status = Cache.b_cache(action='status')
            else:
                raise ValueError('Can not find cache infomation!')

            if status == 'on':
                html = """<div class="btn-group btn-group-xs group-btn-margin">
                            <button type="{}" myId="{}" status="1" data-toggle="tooltip" title="Currently turned on" class="btn btn-primary btn-change" disabled>On</button>
                            <button type="{}" myId="{}" status="0" data-toggle="tooltip" title="Click to turn off" class="btn btn-danger btn-change bg-grey">Off</button>
                        </div>
                """.format(type_cache,pro_id,type_cache,pro_id)
            elif status == 'off':
                html = """<div class="btn-group btn-group-xs group-btn-margin">
                            <button type="{}" myId="{}" status="1" data-toggle="tooltip" title="Currently turned on" class="btn btn-primary btn-change" disabled>On</button>
                            <button type="{}" myId="{}" status="0" data-toggle="tooltip" title="Click to turn off" class="btn btn-danger btn-change bg-grey">Off</button>
                        </div>
                """.format(type_cache, pro_id, type_cache, pro_id)
            elif status == 'mul':
                raise ValueError('None or multiple WP_CACHE constant!')
            else:
                raise ValueError('Web not yet installed!')
            html += """
            <div class="btn-group btn-group-xs">
                <a data-type="{}" myId="{}" data-toggle="tooltip" title="Clear cache" class="btn btn-info btn-sm btn-clear-cache" href="javascript:void(0)" data-loading-text="<i class=\'fa fa-circle-o-notch fa-spin\'></i>"><i class="fa fa-refresh" aria-hidden="true"></i></a>
            </div>
            """.format(type_cache,pro_id)
            result['status'] = 1
            result['msg'] = html
    except KeyError:
        return HttpResponseRedirect('/login')
    except ObjectDoesNotExist:
        result['msg'] = "Provision is not exist!"
    except BaseException as e:
        result['msg'] = str(e)

    return JsonResponse(result)

def actionCache(request,pro_id):
    """
    change status cache provision
    :param request:
    :param pro_id:
    :return:
    """
    result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        provision = Provision.objects.get(pk=pro_id, account_id=userId, deactive_flg=0)
        if request.POST:
            list_status = {0: 'off', 1: 'on',2: 'clear'}
            list_type = {1: 'fcache',2: 'bcache'}
            type_cache = int(request.POST['type'])
            status_cache = int(request.POST['status'])
            Cache = settingManager.SettingManager(provision.provision_name)
            if type_cache == 1:
                status = Cache.f_cache(action=list_status[status_cache])
            elif type_cache == 2:
                status = Cache.b_cache(action=list_status[status_cache])
            else:
                status = False
            if status:
                result['status'] = 1
                if status_cache == 2:
                    pass
                else:
                    result['msg'] = 'Turn <strong>{}</strong> {} for <strong>{}</strong> successfully!'.format(
                        list_status[status_cache], list_type[type_cache], provision.domain)
            else:
                result['msg'] = 'Can not find cache infomation'
    except KeyError:
        result['msg'] = 'Can not find cache infomation'
    except ObjectDoesNotExist:
        result['msg'] = "Provision is not exist!"
    except BaseException as e:
        result['msg'] = str(e)
    return JsonResponse(result)

def sslManager(request):
    """
    list website action ssl
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        provisions = Provision.objects.filter(account_id=userId,deactive_flg=0)
        count = provisions.count()
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/list_website_ssl.html',{'provisions': provisions, 'count': count, 'page_title': 'SSL Manager'})

def checkSsl(request,pro_id=None):
    """
    check SSL status
    :param request:
    :param pro_id:
    :return:
    """
    result = {'status': 0,'msg': ''}
    try:
        userId = request.session['userID']
        provision = Provision.objects.get(pk=pro_id,account_id=userId,deactive_flg=0)
        ssl = sslSetting.SslMng(provision.provision_name)
        status = ssl.ssl_status()
        msg = {}
        if status:
            result['status'] = 1
            result['install'] = 1
            msg['duration'] = status['expiration_date']
            output = status['general_info'].split('\n')
            if 'subject=CN' in str(output[0]):
                msg['subject'] = str(output[0]).replace('subject=CN = ', '')
            else:
                msg['subject'] = 'Unknown'
            if 'CN =' in str(output[1]):
                msg['issuer'] = str(output[1]).split('CN = ')[1]
            else:
                msg['issuer'] = 'Unknown'
            if 'notBefore' in str(output[2]):
                msg['from'] = str(output[2]).replace('notBefore=', '')
            else:
                msg['from'] = 'Unknown'
            if 'notAfter' in str(output[3]):
                msg['to'] = str(output[3]).replace('notAfter=', '')
            else:
                msg['to'] = 'Unknown'

            result['msg'] = msg
        else:
            result['msg'] = "Not installed SSL"
    except KeyError:
        return HttpResponseRedirect('/login')
    except ObjectDoesNotExist:
        result['msg'] = 'Provision is not exist!'

    return JsonResponse(result)

def showSsl(request,pro_id=None):
    """
    show info SSL
    :param request:
    :param pro_id:
    :return:
    """
    result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        provision = Provision.objects.get(pk=pro_id, account_id=userId, deactive_flg=0)
        result['status'] = True
        ssl = sslSetting.SslMng(provision.provision_name)
        if ssl.k_view_cert():
            if os.path.isfile(settings.URL_CRT+provision.provision_name+'.crt'):
                f = open(settings.URL_CRT+provision.provision_name+'.crt', "r")
                result['crt'] = f.read()
                f.close()
            if os.path.isfile(settings.URL_KEY+provision.provision_name+'.key'):
                f = open(settings.URL_KEY + provision.provision_name + '.key', "r")
                result['key'] = f.read()
                f.close()

    except KeyError:
        return HttpResponseRedirect('/login')
    except ObjectDoesNotExist:
        result['msg'] = 'Provision is not exist!'

    return JsonResponse(result)

def removeSsl(request,pro_id=None):
    """
    remove SSL
    :param request:
    :param pro_id:
    :return:
    """
    result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        provision = Provision.objects.get(pk=pro_id, account_id=userId, deactive_flg=0)
        ssl = sslSetting.SslMng(provision.provision_name)
        if ssl.remove_ssl():
            result['status'] = True
            result['msg'] = 'Remove SSL {} success!'.format(provision.domain)
        else:
            result['msg'] = 'Remove SSL {} failed!'.format(provision.domain)
    except KeyError:
        return HttpResponseRedirect('/login')
    except ObjectDoesNotExist:
        result['msg'] = 'Provision is not exist!'

    return JsonResponse(result)

def installManual(request,pro_id=None):
    """
    install Manual SSL
    :param request:
    :param pro_id:
    :return:
    """
    result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        provision = Provision.objects.get(pk=pro_id, account_id=userId, deactive_flg=0)
        if request.POST:
            data = request.POST.copy()
            try:
                # write file ssl
                content_crt = data['ssl_crt']
                content_key = data['ssl_key']
                name_crt = settings.URL_CRT+provision.provision_name+'.crt'
                name_key = settings.URL_KEY + provision.provision_name + '.key'
                f = open(name_crt,'w')
                f.write(content_crt)
                f.close()
                f = open(name_key, 'w')
                f.write(content_key)
                f.close()
                # call Lib install SSL
                ssl = sslSetting.SslMng(provision.provision_name)
                if ssl.k_cert_change(cert_file_path=name_crt,key_file_path=name_key):
                    result['status'] = True
                    result['msg'] = 'Install SSL Manual {} success!'.format(provision.domain);
                else:
                    result['msg'] = 'Install SSL Manual {} failed!'.format(provision.domain)

            except KeyError:
                result['msg'] = "Params is incorrect!"

    except KeyError:
        return HttpResponseRedirect('/login')
    except ObjectDoesNotExist:
        result['msg'] = 'Provision is not exist!'

    return JsonResponse(result)

def installLet(request,pro_id=None):
    """
    install Let's SSL
    :param request:
    :param pro_id:
    :return:
    """
    result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        provision = Provision.objects.get(pk=pro_id, account_id=userId, deactive_flg=0)
        ssl = sslSetting.SslMng(provision.provision_name)
        if ssl.k_ssl(provision.email, 'redirect'):
            result['status'] = True
            result['msg'] = "Installing SSL Certificate {} is completed successfully.".format(provision.domain)
        else:
            result['msg'] = "Installing SSL Certificate {} is failed.".format(provision.domain)
    except KeyError:
        return HttpResponseRedirect('/login')
    except ObjectDoesNotExist:
        result['msg'] = 'Provision is not exist!'

    return JsonResponse(result)

def listTheme(request,pro_id=None):
    """
        list website action ssl
        :param request:
        :return:
        """
    try:
        userId = request.session['userID']
        pro = Provision.objects.get(account_id=userId, deactive_flg=0, app_id__in=[1,2], pk=pro_id)
        data = urllib.request.urlopen(settings.BASE_URL_WB+'theme.json').read()
        data = json.loads(data)
    except KeyError:
        return HttpResponseRedirect('/login')
    except BaseException:
        return HttpResponseRedirect('/websites/')

    return render(request, 'websiteManager/list_theme.html',
                  {'pro': pro,'data': data.values(),'base_theme_url': settings.BASE_URL_WB,'page_title': 'Website Builder'})

def modal(request):
    """
    ajax load modal
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        provisions = Provision.objects.filter(account_id=userId,deactive_flg=0,app_id__in=[1,2])
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/modal.html',{'provisions': provisions})

def activeTheme(request):
    data_result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        account = Account.objects.get(pk=userId)
        if request.POST:
            try:
                pro = Provision.objects.get(id=request.POST['id'], app_id__in=[1, 2], account_id=account.id, deactive_flg=0)
                ws = website.Website(pro.provision_name)
                result = ws.activeTheme({'domain': pro.domain,'theme_id': request.POST['theme_id'],'email': pro.email})
                if result['status']:
                    data_result['status'] = 1
                    data_result['msg'] = '<p>Your website has been created successfully.</p><p><strong><span><i class="fa fa-link"></i> Login url: <a href="'+result['data']['url']+'" target="_blank">'+result['data']['url']+'</a></span></strong></p><p><span><i class="fa fa-user"></i> Account: <strong>'+result['data']['user']+'</strong></span></p><p><span><i class="fa fa-lock"></i> Password: <strong>'+result['data']['password']+'</strong></span></p><p><span><i class="fa fa-lightbulb-o"></i> Please save this information and change current password for more sercurity.</span></p>'
                else:
                    raise ValueError(result['msg'])
            except BaseException as e:
                data_result['msg'] = str(e)
                return HttpResponse(json.dumps(data_result))
        else:
            return HttpResponseRedirect('/websites/')
    except KeyError:
        return HttpResponseRedirect('/login')

    return HttpResponse(json.dumps(data_result))


def fileManager(request):
    """
    ajax create link filemanager
    :param request:
    :return:
    """
    data_result = {'status': 0, 'msg': ''}
    try:
        userId = request.session['userID']
        account = Account.objects.get(pk=userId)
        password = hashPassword.generate_pass(16)
        pass_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode('utf-8').replace('$2b','$2y')
        db = MySQLdb.connect(host=define.DB_HOST_RUN, user=define.DB_USERNAME_RUN, passwd=define.DB_PASS_RUN, database=define.DB_NAME_RUN)
        cursor = db.cursor()
        cursor.execute("UPDATE df_users SET password='{}', username='kusanagi', require_password_change = 0 WHERE id = 1".format(pass_hash))
        cursor.execute("UPDATE df_users_permissions SET homefolder='/home/kusanagi' WHERE uid = 1")
        db.commit()
        db.close()
        ip = socket.gethostbyname(socket.gethostname())
        return HttpResponseRedirect("http://{}/FileManager/?page=login&action=login&nonajax=1&username=kusanagi&password={}".format(ip, password))
    except KeyError:
        return HttpResponseRedirect('/login')
    except ConnectionError:
        data_result['msg'] = 'Can not connect MYSQL'

    return HttpResponse(json.dumps(data_result))

def generateProvision(domain=None):
    """
    generate random provision name
    :param domain:
    :return:
    """
    if len(domain) > 24:
        pass
        pro = hashPassword.generate_pass(4)+domain[:20]
        cnt = Provision.objects.filter(provision_name=pro,deactive_flg=0).count()
        while cnt:
            pro = hashPassword.generate_pass(4) + domain[:20]
            cnt = Provision.objects.filter(provision_name=pro, deactive_flg=0).count()

        return pro.lower()
    else:
        return domain.lower()

def listMysql(request):
    """
    list info mysql manager
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        provisions = Provision.objects.filter(account_id=userId, deactive_flg=0)
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/list_mysql.html', {'data': provisions,'count': len(provisions),'page_title': 'Mysql Manager','ipServer': settings.GOOGLEAUTH})

def emailServer(request):
    """
    EmailServer
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        provisions = Provision.objects.filter(account_id=userId, deactive_flg=0)
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'websiteManager/email_server.html', {'data': provisions,'count': len(provisions),'page_title': 'Mysql Manager','ipServer': settings.GOOGLEAUTH})
