import erm.core.entity_manager as em
#import erm.lib.api as api

from erm.core.models import *
from erm.lib.api import *

from erm.settings import *

#===============UNION=============#

class EntityUnionApi(API):

    def __init__(self,request, api_key, params):
        super(EntityUnionApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':None, 
                         'PUT':None, 
                         'DEL':None}    

    def get(self):
        return em.get_entity_union(self.params, self)

    def add(self):
        return em.add_entity_union(self.raw_data)
 
    def set(self):
        return em.set_entity_union(self.raw_data)
    
    def delete(self):
        return em.del_entity_union(self.params)

def entity_union(request, api_key, **params):
    responder=EntityUnionApi(request, api_key, params)
    return responder.respond()

##===============ENTITY TYPE ATTRIBUTE=============#
class EntityTypeApi(API):

    def __init__(self,request, api_key, params):
        super(EntityTypeApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['slug']}, 
                         'PUT':{'args':['slug']}, 
                         'DEL':{'params':['slug']}}    

    def get(self):
        return em.get_entity_type(self.params, self)

    def add(self):
        return em.add_entity_type(self.raw_data)
 
    def set(self):
        return em.set_entity_type(self.raw_data)
    
    def delete(self):
        return em.del_entity_type(self.params)

def entity_type(request, api_key, **params):
    responder=EntityTypeApi(request, api_key, params)
    return responder.respond()

#===============ENTITY TAG SCHEMA=============#
class EntityTagSchemaApi(API):

    def check_params(self, params, missing_list):
        if not params.has_key('id') and not(params.has_key('slug')):
            missing_list.append('id or slug')

    def __init__(self,request, api_key, params):
        super(EntityTagSchemaApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['slug']}, 
                         'PUT':{'args':self.check_params}, 
                         'DEL':{'params':self.check_params}}    

    def get(self):
        return em.get_entity_tag_schema(self.params, self)

    def add(self):
        return em.add_entity_tag_schema(self.raw_data)
 
    def set(self):
        return em.set_entity_tag_schema(self.raw_data)
    
    def delete(self):
        return em.del_entity_tag_schema(self.params)

def entity_tag_schema(request, api_key, **params):
    responder=EntityTagSchemaApi(request, api_key, params)
    return responder.respond()

#===============ENTITY TAG=============#
class EntityTagApi(API):

    def check_params(self, params, missing_list):
        if not params.has_key('id') and not(params.has_key('slug')):
            missing_list.append('id or slug')

    def __init__(self,request, api_key, params):
        super(EntityTagApi, self).__init__(request, api_key, params)
        self.validators={'GET':None, 
                         'POST':{'args':['name']}, 
                         'PUT':{'args':self.check_params}, 
                         'DEL':{'params':self.check_params}}    

    def get(self):
        return em.get_entity_tag(self.params, self)

    def add(self):
        return em.add_entity_tag(self.raw_data)
 
    def set(self):
        return em.set_entity_tag(self.raw_data)
    
    def delete(self):
        return em.del_entity_tag(self.params.get('id'), self.params.get('slug'))

def entity_tag(request, api_key, **params):
    responder=EntityTagApi(request, api_key, params)
    return responder.respond()

#===============ENTITY=============#

class EntityApi(API):

    def check_params(self, params, missing_list):
        if not params.has_key('id') and not(params.has_key('slug') and (params.has_key('type') or params.has_key('type_name'))):
            missing_list.append('id or (slug AND (type OR type_name))')

    def check_post_params(self, params, missing_list):
        if not params.has_key('slug') or not(params.has_key('type') or params.has_key('type_name')):
            missing_list.append('slug AND (type OR type_name)')

    def check_get_params(self, params, missing_list):
        if not params.has_key('type') and not(params.has_key('type_id')):
            missing_list.append('type OR type_id')

    def __init__(self,request, api_key, params):
        super(EntityApi, self).__init__(request, api_key, params)
        self.validators={'GET':{'params':self.check_get_params}, 
                         'POST':{'args':self.check_post_params}, 
                         'PUT':{'args':self.check_params}, 
                         'DEL':{'params':self.check_params}}    

    def get(self):
        return em.get_entity(self.params, self)

    def add(self):
        return em.add_entity(self.raw_data)
 
    def set(self):
        return em.set_entity(self.raw_data)
    
    def delete(self):
        return em.del_entity(self.params)

def entity(request, api_key, **params):
    responder=EntityApi(request, api_key, params)
    return responder.respond()

