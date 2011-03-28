# Create your views here.
import erm.core.activity_manager as am
#import erm.lib.api as api

from erm.core.models import *
from erm.lib.api import *

from erm.settings import *

#===============ACTIVITY ENTRY=============#

class ActivityApi(API):

    def __init__(self,request, api_key, params):
        super(ActivityApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':None}, 
                         'PUT':{'args':None}, 
                         'DEL':{'params':None}}    

    def get(self):
        return am.get_activity(self.params)

    def add(self):
        return am.add_activity(self.raw_data)
 
    def set(self):
        return am.set_activity(self.raw_data)
    
    def delete(self):
        return am.del_activity(self.params)

def activity(request, api_key, **params):
    responder=ActivityApi(request, api_key, params)
    return responder.respond()

