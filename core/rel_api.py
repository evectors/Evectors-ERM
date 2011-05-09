import erm.core.rel_manager as rel

from erm.core.models import *
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

###===============RELATIONSHIP TYPE ATTRIBUTE=============#
class RelationshipTypeApi(API):

    def __init__(self,request, api_key, params):
        super(RelationshipTypeApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['slug']}, 
                         'PUT':{'args':['slug']}, 
                         'DEL':{'params':['slug']}}    

    def get(self):
        return rel.get_rel_type(self.params)

    def add(self):
        return rel.add_rel_type(self.raw_data)
 
    def set(self):
        return rel.set_rel_type(self.raw_data)
    
    def delete(self):
        return rel.del_rel_type(self.params)

def rel_type(request, api_key, **params):
    responder=RelationshipTypeApi(request, api_key, params)
    return responder.respond()

#===============RELATIONSHIP TYPE ALLOWED=============#
class RelationshipTypeAllowedApi(API):

    def __init__(self,request, api_key, params):
        super(RelationshipTypeAllowedApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['rel_type', 'entity_type_from', 'entity_type_to']}, 
                         'PUT':{'args':['id', 'entity_type_from_id', 'entity_type_to_id']}, 
                         'DEL':{'params':['id']}}    

    def get(self):
        return rel.get_rel_type_allowed(self.params)

    def add(self):
        return rel.add_rel_type_allowed(self.raw_data)
 
    def set(self):
        return rel.set_rel_type_allowed(self.raw_data)
    
    def delete(self):
        return rel.del_rel_type_allowed(self.params.get('id'), self.params.get('slug'))

def rel_type_allowed(request, api_key, **params):
    responder=RelationshipTypeAllowedApi(request, api_key, params)
    return responder.respond()


#===============RELATIONSHIP TAG SCHEMA=============#
class RelationshipTagSchemaApi(API):

    def check_params(self, params, missing_list):
        if not params.has_key('id') and not(params.has_key('name')):
            missing_list.append('id or name')

    def __init__(self,request, api_key, params):
        super(RelationshipTagSchemaApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['name']}, 
                         'PUT':{'args':self.check_params}, 
                         'DEL':{'params':self.check_params}}    

    def get(self):
        return rel.get_rel_tag_schema(self.params)

    def add(self):
        return rel.add_rel_tag_schema(self.raw_data)
 
    def set(self):
        return rel.set_rel_tag_schema(self.raw_data)
    
    def delete(self):
        return rel.del_rel_tag_schema(self.params)

def rel_tag_schema(request, api_key, **params):
    responder=RelationshipTagSchemaApi(request, api_key, params)
    return responder.respond()

#===============RELATIONSHIP TAG=============#
class RelationshipTagApi(API):

    def check_params(self, params, missing_list):
        if not params.has_key('id') and not(params.has_key('slug')):
            missing_list.append('id or slug')

    def __init__(self,request, api_key, params):
        super(RelationshipTagApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['name']}, 
                         'PUT':{'args':self.check_params}, 
                         'DEL':{'params':self.check_params}}    

    def get(self):
        return rel.get_rel_tag(self.params)

    def add(self):
        return rel.add_rel_tag(self.raw_data)
 
    def set(self):
        return rel.set_rel_tag(self.raw_data)
    
    def delete(self):
        return rel.del_rel_tag(self.params.get('id'), self.params.get('slug'))

def rel_tag(request, api_key, **params):
    responder=RelationshipTagApi(request, api_key, params)
    return responder.respond()

##===============RELATIONSHIP=============#
#
class RelationshipApi(API):

    def check_params(self, params, missing_list):
        if not (params.has_key('entity_from_type') or params.has_key('entity_to_type')):
            missing_list.append('entity_from_type or entity_to_type')

    def __init__(self,request, api_key, params):
        super(RelationshipApi, self).__init__(request, api_key, params)
        self.validators={'GET':{'params':self.check_params}   , 
                         'POST':{'args':None},#['rel_type_id', 'entity_from_id', 'entity_to_id']}, 
                         'PUT':{'args':['rel_type', 'entity_from', 'entity_from_type', 'entity_to', 'entity_to_type']},
                         'DEL':{'params':['id']}   ,
                         } 

    def get(self):
        return rel.get_rel(self.params)

    def add(self):
        return rel.add_rel(self.raw_data)
 
    def set(self):
        return rel.set_rel(self.raw_data)
    
    def delete(self):
        return rel.del_rel(self.params)#.get('id'), self.params.get('slug'), self.params.get('type'), self.params.get('type_name'))

def relationship(request, api_key, **params):
    responder=RelationshipApi(request, api_key, params)
    return responder.respond()