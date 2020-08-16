from django.shortcuts import render

from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import Account
from .forms import ChangePassForm,AuthenForm
from plogical import hashPassword
import psutil
import math
import subprocess
from django.contrib import messages
import pyotp
from django.conf import settings

def index(request):
    try:
        userId = request.session['userID']
        context = {
            'userId': userId,
            'ipServer': settings.GOOGLEAUTH,
            'CpuPer': psutil.cpu_percent(),
            'CpuCore': psutil.cpu_count(),
            'MemToltal': math.ceil(float(psutil.virtual_memory()[0])/float(1024**3)),
            'MemPer': psutil.virtual_memory()[2],
            'SwapTotal': math.ceil(float(psutil.swap_memory()[0])/float(1024**3)),
            'SwapPer': psutil.swap_memory()[3],
            'DiskTotal': math.ceil(float(psutil.disk_usage('/')[0])/float(1024*1024*1000)),
            'DiskPer': math.ceil(psutil.disk_usage('/')[3]),
        }
    except KeyError:
        return HttpResponseRedirect('/login')
    return render(request, 'index.html',context)

def login(request):
    """
    login account
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        return HttpResponseRedirect('/')
    except KeyError:
        try:
            if request.method == 'POST':
                username = request.POST.get('login_id')
                password = request.POST.get('login_password')
                account = Account.objects.get(login_id=username)
                if account.is_active == False:
                    raise ValueError("Account is suppend!")
                if hashPassword.check_password(account.password, password):
                    if account.security_status:
                        request.session['tempID'] = account.pk
                        return HttpResponseRedirect('/authi')
                    else:
                        request.session['userID'] = account.pk
                        request.session['name'] = account.get_full_name()
                        return HttpResponseRedirect('/')
                else:
                    raise ValueError("Username or password is invalid.")
            else:
                try:
                    del request.session['tempID']
                except KeyError:
                    pass
        except BaseException as msg:
            messages.error(request, str(msg))

    return render(request,'loginSys/login.html')

def logout(request):
    """
    logout account
    :param request:
    :return:
    """
    try:
        del request.session['userID']
        return HttpResponseRedirect('/login')
    except:
        return HttpResponseRedirect('/login')

def load_chart(request):
    """
    load chart ajax
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        context = {
            'userId': userId,
            'ipServer': request.META.get('REMOTE_ADDR'),
            'CpuPer': psutil.cpu_percent(),
            'CpuCore': psutil.cpu_count(),
            'MemToltal': math.ceil(float(psutil.virtual_memory()[0])/float(1024*1024)),
            'MemPer': psutil.virtual_memory()[2],
            'SwapTotal': math.ceil(float(psutil.swap_memory()[0])/float(1024*1024)),
            'SwapPer': psutil.swap_memory()[3],
            'DiskTotal': math.ceil(float(psutil.disk_usage('/')[0])/float(1024*1024*1024)),
            'DiskPer': math.ceil(psutil.disk_usage('/')[3]),
        }
    except KeyError:
        return HttpResponseRedirect('/login')

    return render(request, 'chart.html',context)

def changePassword(request):
    """
    change password
    :param request:
    :return:
    """
    try:
        userId = request.session['userID']
        account = Account.objects.get(pk=userId)

        if request.POST:
            data = request.POST.copy()
            data['user_id'] = userId
            form = ChangePassForm(data)
            if form.is_valid():
                account = Account.objects.get(pk=userId)
                account.password = hashPassword.hash_password(data['password'])
                account.save()
                messages.success(request, "Your password changed successfully!")
        else:
            form = ChangePassForm()
    except KeyError:
        return HttpResponseRedirect('/login')
    return render(request, 'loginSys/change_password.html',{'page_title': 'Change Password','form': form})

def authi(request):
    """
    2FA authen google
    :param request:
    :return:
    """
    try:
        userId = request.session['tempID']
        account = Account.objects.get(pk=userId)
        if request.POST:
            form = AuthenForm(request.POST)
            if form.is_valid():
                totp = pyotp.TOTP(account.security_code)
                if totp.verify(request.POST['code']):
                    request.session['userID'] = account.pk
                    return HttpResponseRedirect('/')
                else:
                    del request.session['tempID']
                    return HttpResponseRedirect('/login')
            else:
                return HttpResponseRedirect('/login')
        else:
            form = AuthenForm()
    except KeyError:
        return HttpResponseRedirect('/login')
    return render(request, 'loginSys/authi.html', {'page_title': 'Change Password','form': form})

def handler404(request,exception):
    return render(request, '404.html', status=404)
def handler500(request):
    return render(request, '500.html', status=500)
