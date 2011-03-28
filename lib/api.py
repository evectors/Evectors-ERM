import cjson
import inspect
import os

from types import FunctionType
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, \
                        HttpResponseServerError, HttpResponseBadRequest, HttpResponseRedirect
from django.conf import settings

from erm.settings import *
from django.db import transaction

import datetime
import time

from erm.lib.logger import Logger

#from erm.datamanager.models import DataManagerError
#from erm.datamanager.connectors.simple import SimpleDbError


PREFIX_METHOD_MAP=dict()
PREFIX_METHOD_MAP['get']='GET'
PREFIX_METHOD_MAP['add']='POST'
PREFIX_METHOD_MAP['set']='PUT'
PREFIX_METHOD_MAP['del']='DELETE'

ERROR_CODES=dict()
#=====================generic or common errors=====================#
ERROR_CODES["100"]="Error management error"
ERROR_CODES["101"]="Generic error"
ERROR_CODES["102"]="Missing or empty parameter"
ERROR_CODES["103"]="Bad request format"
#=====================get errors=====================#
ERROR_CODES["200"]="No object found" 
#=====================add errors=====================#
ERROR_CODES["300"]="Object already existent"
ERROR_CODES["311"]="No entity type found"
ERROR_CODES["312"]="More entity types found"
#=====================set errors=====================#
ERROR_CODES["400"]="Object missing" #200 can also be returned
ERROR_CODES["401"]="More objects found"
ERROR_CODES["410"]="Can't change"
#=====================delete errors=====================#
ERROR_CODES["500"]="Object missing" #200 can also be returned
ERROR_CODES["501"]="More objects found"


class ApiError(Exception):
    def __init__(self, value=None, code=None, extra_info=""):
        if not value and not code:
            code="100"
        if not value and code:
            try:
                value=ERROR_CODES[str(code)]
            except:
                code="100"
                value=ERROR_CODES[str(code)]
        if extra_info!="":
            value+=" [%s]" % extra_info
        if DEBUG_ERM:
            daddy=inspect.stack()[1]
#            value="%s >> %s (%s: line %s)" % (daddy[3], value, os.path.basename(daddy[1]), daddy[2])
            value="%s >> %s (%s: line %s) - %s" % (daddy[3], value, os.path.basename(daddy[1]), daddy[2], inspect.trace())
        self.value = value
        self.code = code
    def __str__(self):
        return repr(self.value)
    def error_code(self):
        return self.code
    def error_str(self):
        return self.value

def json_decode(s):
    h,d,u=cjson.__version__.split(".")
    if (int(h)*100+int(d)*10+int(u))<=105:
        s=s.replace('\/', '/')
    return cjson.decode(s)

def json_indent(s):
    # slow and ugly, but we use it only in debug mode
    buffer = list()
    inside = False
    escape = False
    indent = 0
    indent_str='  '
    for c in s:
        if c == '\\':
            escape = not escape
        elif c != '"' and escape:
             escape=False
       
        if c == '"':
            if escape:
                escape = False
            else:
                inside = not inside
                
        if not inside:
            if c == ',':
                buffer.append(",\n%s" % (indent_str * indent))
                continue
            elif c == ' ':
                continue
            elif c in '[{':
                buffer.append(c)
                indent += 1
                buffer.append("\n%s" % (indent_str * indent))
                continue
            elif c in ']}':
                buffer.append("\n%s" % (indent_str * indent))
                indent -=1
                buffer.append(c)
                continue
        
        buffer.append(c)
    return ''.join(buffer)

def json_encode(obj, flIndent=False, flMaskErrs=True, flRecursion=False):
    s=""
    try:
        s=cjson.encode(obj)
        if flIndent:
            s=json_indent(s)
        return s
            
    except cjson.EncodeError, err:
        if isinstance(obj, list):
            new_list=list()
            for item in obj:
                try:
                    cjson.encode(item)
                    new_list.append(item)
                except Exception, err:
                    new_list.append(json_encode(item, flIndent, True, True))
            if not flRecursion:
                s=cjson.encode(new_list)
                if flIndent:
                    s=json_indent(s)
                return s
            else:
                return new_list
        elif isinstance(obj, dict):
            new_dict=dict()
            for key,value in obj.items():
                try:
                    cjson.encode(value)
                    new_dict[key]=value
                except Exception, err:
                    new_dict[key]=json_encode(value, flIndent, True, True)
            if not flRecursion:
                return json_encode(new_dict, flIndent, True, True)
            else:
                return new_dict
        elif isinstance(obj, datetime.datetime):
            return cjson.encode(time.mktime(obj.timetuple()))
        else:
#            if flMaskErrs:
#                return ("Encode error: %s (%s)" % (obj, type(obj)))
#            else:
#                raise
            try:
                #maybe the object is iterable anyway ;)
                new_dict=dict()
                for key,value in obj.items():
                    try:
                        cjson.encode(value)
                        new_dict[key]=value
                    except Exception, err:
                        new_dict[key]=json_encode(value, flIndent, True, True)
                if not flRecursion:
                    return json_encode(new_dict, flIndent, True, True)
                else:
                    return new_dict
            except Exception, err:
                try:
                    return json_encode(obj.__dict__, flIndent, True, True)
                except Exception, err:
                    if flMaskErrs:
                        return ("Encode error: %s (%s) - %s" % (obj, type(obj), err))
                    else:
                        raise

class API(object):
        
    def __init__(self, request, api_key, params):
        self.request=request
        self.api_key=api_key
        self.params=dict()
        self.validators={'GET':None, 'POST':None, 'PUT':None, 'DEL':None}    
        self.success=True
        self.msg=""
        self.data=None
        self.response=dict()
        self.method=request.method
        self.raw_data=request.raw_post_data
        
        transaction.enter_transaction_management()
        transaction.managed(True)
        
        if params and params['params'] and params['params']!=None and ("=" in params['params']):
            try:
                self.params = dict((str(a), b) for a, b in [p.split('=') for p in params['params'].split(';') if p!=""])
            except:
                try:
                    self.params={"id":params['params']}
                except:
                    self.params={"id":params}
        else:
            try:
                self.params={"id":params['params']}
            except:
                self.params={"id":params}

        #====DEBUG: allows to mimic different methods and http data====#
        if DEBUG_API:       
            if self.params.has_key('method'):
                self.method=self.params.get('method')
            if self.params.has_key('raw_data'):
                self.raw_data=self.params.get('raw_data')
        #==================END: DEBUG=================#
        
        if self.method=="POST" or self.method=="PUT":
            try:
                self.raw_data = json_decode(self.raw_data)
            except cjson.DecodeError, err:
                self.success=False
                self.msg = "Error decoding json data: %s (%s)" % (err , self.raw_data)

        if api_key!=SECRET_KEY:
                self.success=False
                self.msg = "You are not allowed to access this resource."

    def get(self):
        return list()
    
    def add(self):
        return None
    
    def set(self):
        return None
    
    def delete(self):
        return None
            
    def validate(self, required, passed_values, missing_list):
        if isinstance(required, list):
            for field in required:
                if not passed_values.has_key(field):
                    missing_list.append(field)
        elif isinstance(required, FunctionType):
            required(passed_values, missing_list)
    
    def build_response(self):
        if isinstance(self.response, dict):
            response=""
            if self.response.has_key('success') and \
                self.response.has_key('msg') and \
                self.response.has_key('data'):
                
                if self.response['success']:
                    transaction.commit()
                else:
                    transaction.rollback()
                transaction.leave_transaction_management()
                
                format='json'
                fl_jindent=False
                mimetype='text/plain'
                
                _params=None
                if self.method in ('POST', 'PUT'):
                    _params=self.raw_data
                elif self.method in ('GET', 'DELETE'):
                    _params=self.params
                if _params:
                    format=_params.get('format', 'json')
                    fl_jindent=bool(_params.get('jindent', False))
                if format=='json':
                    fl_jindent=settings.DEBUG_JSON or fl_jindent
                    if not fl_jindent:
                        mimetype='application/json'
                    _result=json_encode(self.response, fl_jindent)
                    response=_result                        
                elif format=='xml':
                    mimetype='text/xml'
                    response='<?xml version="1.0" encoding="UTF-8" ?><answer>Sorry, xml format not yet implemented</answer>'
                else:
                    response="Answer format not supported: %s" % (format,)
                    HttpResponseServerError(response)
                return HttpResponse(response, mimetype=mimetype)
            else:
                HttpResponseServerError("Malformed response, expected success, msg, data, params fields, got %s (%s)" % (self.response.keys(), self.response))
        else:
            HttpResponseServerError("Bad response, expected dict, got %s (%s)" % (type(self.response), self.response))

    def respond(self):
        if self.success:    
            if self.validators.has_key(self.method):
                missing_args=list()
                missing_params=list()
                required=self.validators[self.method]
                if required and isinstance(required, dict):
                    self.validate(required.get('args', list()), self.raw_data, missing_args)
                    self.validate(required.get('params', list()), self.params, missing_params)
                if len(missing_args)>0 or len(missing_params)>0:
                    self.success=False
                    self.msg="Incomplete request. "
                    self.data="102"
                    if len(missing_args) > 0:
                        self.msg=self.msg+("data: %s " % ",".join(missing_args))
                        if len(missing_params) > 0:
                            self.msg=self.msg+"and "
                        else:
                            self.msg=self.msg+"required"
                    if len(missing_params) > 0:
                        self.msg=self.msg+("params: %s required" % ",".join(missing_params))
                    self.msg=self.msg+"%s" % ([missing_args, missing_params])
            if self.success:
                result=None
                try:
                    if self.method=="GET":
                        result=self.get()
                    elif self.method=="POST":
                        result=self.add()
                    elif self.method=="PUT":
                        result=self.set()
                    elif self.method=="DELETE":
                        result=self.delete()
                    else:
                        self.msg="Unsupported method: %s" % self.method
                        self.success=False
#                except (ApiError,SimpleDbError,DataManagerError), err:
                except ApiError, err:
                    self.success=False
                    try:
                        self.msg=err.value
                        self.data=err.code
                    except Exception, e:
                        self.msg="Undefined error [%s]" % e
                except Exception,err:#, err:
                    self.success=False
                    self.msg="Error: %s (%s)" % (Exception, err)
                if self.success:
                    compact=False
                    attributes="*"
                    tags="*"
                    cache_life=0
                    fl_set_cache_date=False
                    fl_mask_attributes_err=True
                    fl_is_entity=self.request.META['PATH_INFO'].find("/entity/")>=0 or self.request.META['PATH_INFO'].find("/search/")>=0
                    try:
                        compact=bool(int(self.params.get('compact', self.request.method=="GET")))
                        attributes=self.params.get('return_attrs', self.request.method!="GET" and "*" or "")
                        tags=self.params.get('return_tags', self.request.method!="GET" and "*" or "")
                        fl_mask_attributes_err=self.params.get('attrs_err')!="1"
                        cache_life=int(self.params.get('cache_life',0))
                        rels=self.params.get('rels', "")
                    except:
                        pass
                    if isinstance(result, list):
                        try:
                            if fl_is_entity:
                                self.data=list(item.to_dict(compact, attributes, tags, rels, fl_mask_attributes_err=fl_mask_attributes_err, cache_life=cache_life, fl_set_cache_date=fl_set_cache_date) for item in result)
                            else:
                                self.data=list(item.to_dict(compact) for item in result)
                        except Exception, err:
                            if fl_is_entity and not fl_mask_attributes_err:
                                self.success=False
                                try:
                                    self.msg=err.value
                                    self.data=err.code
                                except Exception, e:
                                    self.msg="Undefined error [%s]" % e
                            else:
                                self.data=result
                    else:
                        try:
                            if fl_is_entity:
                                self.data=result.to_dict(compact, attributes, tags)
                            else:
                                self.data=result.to_dict(compact)
                        except:
                            self.data = result
        self.response={"success":self.success, 
                       "msg":self.msg, 
                       "data":self.data}
        if DEBUG_API:
            self.response['method']=self.method
            self.response['raw_data']=self.raw_data
            self.response['params']=self.params
#            self.response['request']=self.request
                    
        return self.build_response()
    