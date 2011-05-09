import erm.core.series_manager as sm
#import erm.lib.api as api

from erm.core.models import *
from erm.lib.api import *

from erm.settings import *

#===============SERIES TODAY=============#

class SeriesTodayApi(API):

    def __init__(self,request, api_key, params):
        super(SeriesTodayApi, self).__init__(request, api_key, params)
        self.validators={'GET': None, 
                         'POST': None, 
                         'PUT': None, 
                         'DEL': {'params':['name']}}    

    def get(self):
        return sm.get_series_today(self.params)

    def add(self):
        return sm.add_series_today(self.raw_data)
 
    def set(self):
        return sm.add_series_today(self.raw_data)
    
    def delete(self):
        return sm.del_series_today(self.params)

def series_today(request, api_key, **params):
    responder=SeriesTodayApi(request, api_key, params)
    return responder.respond()

#===============SERIES CURRENT=============#

class SeriesHistoryApi(API):

    def __init__(self,request, api_key, params):
        super(SeriesHistoryApi, self).__init__(request, api_key, params)
        self.validators={'GET': {'params':['name']}, 
                         'POST': {'args':['name', 'day', 'values']}, 
                         'PUT': {'args':['name', 'day', 'values']}, 
                         'DEL': {'params':['name', 'day']}}    

    def get(self):
        return sm.get_series_history(self.params)

    def add(self):
        return sm.add_series_history(self.raw_data)
 
    def set(self):
        return sm.add_series_history(self.raw_data)
    
    def delete(self):
        return sm.del_series_history(self.params)

def series_history(request, api_key, **params):
    responder=SeriesHistoryApi(request, api_key, params)
    return responder.respond()

#===============SERIES CURRENT=============#

class SeriesCurrentApi(API):

    def __init__(self,request, api_key, params):
        super(SeriesCurrentApi, self).__init__(request, api_key, params)
        self.validators={'GET': {'params':['name', 'length']}, 
                         'POST': {'args':['name', 'values']}, 
                         'PUT': {'args':['name', 'values']}, 
                         'DEL': {'params':['name', 'length']}}    

    def get(self):
        return sm.get_series_current(self.params)

    def add(self):
        return sm.add_series_current(self.raw_data)
 
    def set(self):
        return sm.add_series_current(self.raw_data)
    
    def delete(self):
        return sm.del_series_current(self.params)

def series_current(request, api_key, **params):
    responder=SeriesCurrentApi(request, api_key, params)
    return responder.respond()

#===============SERIES RULES=============#

class SeriesRuleApi(API):

    def __init__(self,request, api_key, params):
        super(SeriesRuleApi, self).__init__(request, api_key, params)
        self.validators={'GET': None, 
                         'POST': {'args':['name', 'length']}, 
                         'PUT': {'args':['name', 'length']}, 
                         'DEL': {'params':['name', 'length']}}    

    def get(self):
        return sm.get_series_rule(self.params)

    def add(self):
        return sm.add_series_rule(self.raw_data)
 
    def set(self):
        return sm.add_series_rule(self.raw_data)
    
    def delete(self):
        return sm.del_series_rule(self.params)

def series_rule(request, api_key, **params):
    responder=SeriesRuleApi(request, api_key, params)
    return responder.respond()

#===============SERIES KEYS=============#

class SeriesKeysApi(API):

    def __init__(self,request, api_key, params):
        super(SeriesKeysApi, self).__init__(request, api_key, params)
        self.validators={'GET': None, 
                         'POST': None, 
                         'PUT': None, 
                         'DEL': None}    

    def get(self):
        return sm.get_series_keys(self.params)

    def add(self):
        return "Not supported"
 
    def set(self):
        return "Not supported"
    
    def delete(self):
        return "Not supported"

def series_keys(request, api_key, **params):
    responder=SeriesKeysApi(request, api_key, params)
    return responder.respond()

