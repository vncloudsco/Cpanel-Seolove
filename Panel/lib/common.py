import os
from django.conf import settings
from datetime import datetime

def write_log(name_file=None,message = None):
    """
    write log custom file
    :param name_file:
    :param message:
    :return:
    """
    name_file = os.path.join(settings.BASE_DIR, name_file)
    f = open(name_file, "a+")
    today = datetime.now()
    f.write("%s %s \n" % (today.strftime("%Y-%m-%d %H:%M:%S"), message))
    f.close()
