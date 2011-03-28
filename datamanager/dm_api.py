# Create your views here.
#import erm.dm.core_manager as mm
#import erm.lib.api as api

from erm.datamanager.models import *
from erm.lib.api import *
from erm.settings import *

#===============BOUNCE (dev)=============#

def bounce(request, api_key, **params):
    
    #return HttpResponse("%s" % args, mimetype="text/plain")
    class Bounce_Responder(API):

        def __init__(self, request, api_key, params):
            super(Bounce_Responder, self).__init__(request, api_key, params)
            self.validators={'GET':None, 
                             'POST':None, 
                             'PUT':None, 
                             'DEL':None}    

        def get(self):
            return "get: %s" % self.params
        
        def add(self):
            return  "add: %s" % self.raw_data

        def set(self):
            return  "set: %s" % self.data
        
        def delete(self):
            return  "delete: %s" % self.params
    
    responder=Bounce_Responder(request, api_key, params)
    return responder.respond()

#===============ENTITY TYPE ATTRIBUTE=============#
class EntityTypeAttributeApi(API):

    def __init__(self,request, api_key, params):
        super(EntityTypeAttributeApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['name']}, 
                         'PUT':{'args':['name']}, 
                         'DEL':{'params':['name']}}    

    def get(self):
        return em.get_entity_type_attribute(self.params)

    def add(self):
        return em.add_entity_type_attribute(self.raw_data.get('name'))
 
    def set(self):
        return em.set_entity_type_attribute(self.raw_data.get('name'))
    
    def delete(self):
        return em.del_entity_type_attribute(self.params.get('name'))

def entity_type_attribute(request, api_key, **params):
    responder=EntityTypeAttributeApi(request, api_key, params)
    return responder.respond()