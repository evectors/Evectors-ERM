from django.db import models
from django.core.management.base import BaseCommand
import settings
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Dumps the data as a customised python script.'
    args = '[appname ...]'

    def handle(self, *app_labels, **options):
        
        if len(app_labels)==2:
            user = User.objects.get(username=app_labels[0])
            user.set_password(app_labels[1]);
            user.save()
            print ("password for user %s changed to %s" % (app_labels[0], app_labels[1]))
        else:
            print ("usage: python manage.py changepwd username newpassword")
