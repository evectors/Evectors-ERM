import os
import sys
import time
import datetime
import pickle
import settings

def pickleToFile(fileName, data):
    if not os.path.exists(settings.PICKLER_DIR):
            os.mkdir(settings.PICKLER_DIR)
    picklePath=os.path.join(settings.PICKLER_DIR, fileName)
    pickleFile=open(picklePath, 'w')
    pickle.dump(data, pickleFile)
    pickleFile.close()
    return picklePath

def pickleFromFile(fileName, default=None):
    try:
        picklePath=os.path.join(settings.PICKLER_DIR, fileName)
        pickleFile=open(picklePath, 'r')
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
    	otherMeData=pickleFromFile(myname)
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
