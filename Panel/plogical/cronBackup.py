#!/usr/bin/env python3

import argparse
import django
import sys
import os

dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(dir_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GmoPanel.settings")
django.setup()
from django.core.exceptions import ObjectDoesNotExist
from plogical.backupSetting import BackupAllProvision
from backupManager.models import CronJob


def retention(freq=None, number=None):
    chdir = '/home/kusanagi/backup/%s/' % freq
    job = BackupAllProvision()
    job.delete_old_local_backup_all_provision(chdir, int(number))


def back_up(freq=None, number=None):
    try:
        tasks = CronJob.objects.get(id="%s" % int(number))
    except ObjectDoesNotExist as error:
        return error
    job = BackupAllProvision()
    bktype = tasks.backup_type
    if bktype == 0:
        job.local_backup('/home/kusanagi/backup/%s/' % freq)
    if bktype == 1:
        job.remote_backup(tasks.user, tasks.host, tasks.port, tasks.password, tasks.path)
    if bktype == 2:
        job.drive_backup(tasks.path)


def get_options(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', type=str, choices=['create', 'del'])
    parser.add_argument('options', nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main():
    args = get_options(sys.argv[1:])
    if args.mode == 'create':
        back_up(*args.options)
    if args.mode == 'del':
        retention(*args.options)
    

if __name__ == '__main__':
    main()
