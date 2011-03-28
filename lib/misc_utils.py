import re
import unicodedata        
from erm.settings import *
import datetime
import os
import sys
import time
import pickle
import stat

from django.utils.encoding import smart_str, smart_unicode, force_unicode

def string_to_slug(s):    
    raw_data = s
    # normalze string as proposed on http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/251871
    # by Aaron Bentley, 2006/01/02
    try:
        raw_data = unicodedata.normalize('NFKD', smart_str(raw_data).decode('utf-8', 'replace')).encode('ascii', 'ignore')
    except:
        pass
    return re.sub(r'[^a-z0-9-\.]+', SANITIZE_CHAR, raw_data.lower())#.strip(SANITIZE_CHAR)

def to_unicode(s):
    return force_unicode(s, strings_only=True)

def build_text_search(objects, param_name, params_dict, wildchar="*"):
    if params_dict.has_key(param_name) and params_dict.get(param_name):
        kwargs={}
        arg_name=param_name
        param_value=params_dict.get(param_name)
        if param_value.find(",") >= 0:
            param_values_list=param_value.split(",")
            kwargs["%s__in" % param_name]=param_values_list
        elif param_value.find(wildchar) >= 0:
            if param_value[:1]==wildchar and param_value[-1:]=='*':
                kwargs["%s__icontains" % param_name]=param_value[1:-1]
            elif param_value[:1]==wildchar :
                kwargs["%s__iendswith" % param_name]=param_value[1:]
            elif param_value[-1:]==wildchar :
                kwargs["%s__istartswith" % param_name]=param_value[:-1]
            else:
                kwargs[param_name]=param_value
        else:
            kwargs[param_name]=param_value
        return objects.filter(**kwargs)
    return objects

def build_date_search(objects, param_name, params_dict, dateformat='timestamp'): 
    if params_dict.has_key(param_name) and params_dict.get(param_name):
        kwargs={}
        search_day=params_dict.get(param_name)
        if dateformat=='timestamp':
            search_day=float(search_day)
            search_day=datetime.datetime.fromtimestamp(search_day)
        start = datetime.datetime(search_day.year, search_day.month, search_day.day)
        end = start + datetime.timedelta(hours=23, minutes=59, seconds=59)
        kwargs["%s__range" % param_name]=(start, end)
        return objects.filter(**kwargs)

    elif params_dict.has_key(param_name + "_in") and params_dict.get(param_name + "_in"):
        kwargs={}
        start=None
        end=None
        dates=params_dict.get(param_name + "_in").split(",")
        if len(dates)>0:
            try:
                start=datetime.datetime.fromtimestamp(float(dates[0]))
            except:
                pass
            if len(dates)>1:
                try:
                    end=datetime.datetime.fromtimestamp(float(dates[1]))
                except:
                    pass
            if start and end:
                kwargs["%s__range" % param_name]=(start, end)
            elif start:
                kwargs["%s__gt" % param_name]=start
            elif end:
                kwargs["%s__lt" % param_name]=end
        if len(kwargs)>0:
            return objects.filter(**kwargs)
    return objects

def pickleToFile(fileName, data, dest_dir=PICKLER_DIR):
    if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)
            try:
                os.chmod(dest_dir, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
            except:
                pass
    pickleFilePath=os.path.join(dest_dir, fileName)
    pickleFile=open(pickleFilePath, 'w')
    pickle.dump(data, pickleFile)
    pickleFile.close()
    try:
        os.chmod(pickleFilePath, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
    except:
        pass

def pickleFromFile(fileName, default=None, dest_dir=PICKLER_DIR):
    try:
        pickleFile=open(dest_dir + 'daemon_' + fileName, 'r')
        my_data=pickle.load(pickleFile)
        pickleFile.close()
        return my_data
    except:
        return default

def isProcessRunning (PID):
    try:
        os.kill(PID,0)
        return True
    except:
        return False

def isAnotherMeRunning(myname):
    try:
        pickleFile=open(settings.PICKLER_DIR + myname, 'r')
        otherMeData=pickle.load(pickleFile)
        pickleFile.close()
        if otherMeData and isProcessRunning(otherMeData[0]):
            return (True, otherMeData)
        else:
            pickleToFile(myname, [os.getpid(), datetime.datetime.now()])
        return (False,)
    except:
        pickleToFile(myname, [os.getpid(), datetime.datetime.now()])
        return (False,)

def getServerLoad():
    uptime=os.popen( "uptime" )
    load=uptime.read().split('average:')
    loadFloat = [float(avg) for avg in load[1].split(',')]
    uptime.close()
    return loadFloat

def killProcess(processname, sudopass=None):
    try:
        if sudopass:
            os.popen("sudo kill -9 `ps aux |grep %s |grep -v grep |awk '{print $2}'`" % processname).write(sudopass)
        else:
            os.popen("kill -9 `ps aux |grep %s |grep -v grep |awk '{print $2}'`" % processname)
        return True
    except:
        return False

