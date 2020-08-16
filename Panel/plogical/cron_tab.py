from cronManager import CronManager


test = '0,1,2,3,4,5,6'

cron = CronManager(command='ahihi', comment='ahehe')

cron.daily(test.split(','))



