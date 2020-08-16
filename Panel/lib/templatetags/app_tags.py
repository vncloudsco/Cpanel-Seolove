from django import template
import os
from django.conf import settings
import uuid
from pathlib import Path

from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter
def render_html(int):
    if (int < 50):
        color = "#00a65a"
    elif(int >= 50 and int < 75):
        color = "#f39c12"
    else:
        color = "#dd4b39"
    inputChart = '<input class="knob" data-angleOffset=-125 data-angleArc=250 data-fgColor="{}" value="{}" data-readOnly=true>'.format(color,int)

    return inputChart

@register.filter
@stringfilter
def show_usage(provision_name):
    root_directory = Path('/home/kusanagi/{}'.format(provision_name))
    used = sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())
    format = 'GB'
    usage = round(used/(1024**3))
    if usage == 0:
        usage = round(used/(1024**2),2)
        format = 'MB'
    else:
        usage = round(used/(1024 ** 3),2)
    return str(usage)+' '+format

@register.simple_tag(name='cache_bust')
def cache_bust():

    if settings.DEBUG:
        version = uuid.uuid1()
    else:
        version = os.environ.get('PROJECT_VERSION')
        if version is None:
            version = '1'

    return '__v__={version}'.format(version=version)

@register.filter
def show_name(request):
    try:
        return request.session['name']
    except:
        return None

@register.simple_tag(name = 'show_pass_mail')
def show_pass_mail():
    try:
        file = open('/usr/lib/.irm_admin', 'r')
        password = file.read()
        file.close()
        return password
    except:
        return ""