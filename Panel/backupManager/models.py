from django.db import models
from websiteManager.models import Provision
from django.utils import timezone

class BackupLog(models.Model):
    provision = models.ForeignKey(Provision, on_delete=models.CASCADE)
    status = models.SmallIntegerField(default=0)
    backup_type = models.SmallIntegerField(default=0)
    message = models.TextField(default='None', null=True)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table='logs'


class CronJob(models.Model):
    backup_schedu = models.CharField(max_length=255,default=None)
    backup_day = models.CharField(max_length=255,default=None, null=True)
    backup_week = models.SmallIntegerField(default=0, null=True)
    backup_type = models.SmallIntegerField(default=0)
    host = models.CharField(max_length=255,default=None, null=True)
    port = models.IntegerField(default=0, null=True)
    user = models.CharField(max_length=255,default=None, null=True)
    password = models.CharField(max_length=255, default=None, null=True)
    path = models.TextField(default=None, null=True)
    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table='cron_job'

