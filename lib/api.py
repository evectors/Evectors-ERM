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

import csv
import StringIO
import zipfile
import urllib

from erm.lib.misc_utils import microtime_slug, to_unicode
from django.utils.encoding import smart_str, smart_unicode, force_unicode

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
                value=ERROR_CODES["100"]
#                 code="100"
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
            
        elif isinstance(obj, datetime.date):
            return obj.isoformat()

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

def get_item_value_by_key(item, keys):
    if len(keys)>0:
        key=keys[0]
        if "[" not in key:
            if len(keys)==1:
                item=item[key]
            else:
                item = get_item_value_by_key(item[key], keys[1:])
        else:
            condition=None
            key,pos=key.split('[')
            res_list=list()
            if "{" in pos:
                conditions_list=list()
                pos, conditions= pos.split("{")
                for condition in conditions[:-1].split('&'):
                    condition=condition.split('>')
                    condition[1]=str(urllib.unquote_plus(condition[1])).replace('*','.')
                    conditions_list.append(condition)
            pos=pos[:-1]
            pos_list=list()
            for pos_item in pos.split("|"):
                if pos_item!='*':
                    pos_item=int(pos_item)
                pos_list.append(pos_item)
                
            item_pos=0
            for sub_item in item[key]:
                if pos_list==['*'] or item_pos in pos_list:
                    get_it=True
                    for condition in conditions_list:
                        get_it=get_it and (str(sub_item[condition[0]])==condition[1])
                    
                    if get_it:
                        res_list.append(to_unicode(get_item_value_by_key(sub_item, keys[1:]), False))
                item_pos+=1 
                        
            item=','.join(res_list)
    return item
        
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
        
        if len(request.GET)>0:
            self.params = dict((str(a), b) for a, b in request.GET.items())
        elif params and params['params'] and params['params']!=None and ("=" in params['params']):
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
                elif format=='csv':
                    csv_text=""
                    if len(self.response)>0:
                        row_cells=list()
                        first_row=list()
                        if _params.has_key('row_format'):
                            row_format=_params.get('row_format')
                            for row_cell in _params.get('row_format').split(','):
                                if ':' in row_cell:
                                    cell_path, cell_head=row_cell.split(':')
                                else:
                                    cell_path=row_cell
                                    cell_head=row_cell
                                    
                                cell_path=cell_path.strip()
                                cell_head=cell_head.strip()
                                
                                first_row.append(smart_str(cell_head))
                                row_cells.append(cell_path.split('.'))
                        else:
                            if isinstance(self.response['data'], list) and isinstance(self.response['data'][0], dict):
                                for key in self.response['data'][0]:
                                    if isinstance(self.response['data'][0][key], dict):
                                        for inner_key in self.response['data'][0][key]:
                                            row_cells.append([key, inner_key])
                                            first_row.append("%s.%s" % (smart_str(key), 
                                                smart_str(inner_key)))
                                    else:
                                        row_cells.append([key])
                                        first_row.append(smart_str(key))
                            row_cells.sort()
                            first_row.sort()
                        
                        if len(row_cells)>0:
                            string_file=StringIO.StringIO()
                            writer=csv.writer(string_file, 
                                              delimiter=',', 
                                              quotechar='"', 
                                              quoting=csv.QUOTE_ALL, 
                                              )
                            if bool(int(_params.get('first_row',1))):
                                writer.writerow(first_row)
                            for row in self.response['data']:
                                row_list=list()
                                for cell in row_cells:
                                    
                                    nomad = get_item_value_by_key(row, cell)

                                    if isinstance(nomad, (str, unicode)):
                                        row_list.append(nomad.encode('utf-8'))
                                    elif isinstance(nomad, (int, float)):
                                        row_list.append(nomad)
                                    else:
                                        try:
                                            row_list.append(json_encode(nomad).encode('utf-8'))
                                        except Exception, err:
                                            try:
                                                row_list.append("%s" % (nomad))
                                            except Exception, err:
                                                row_list.append("%s-%s" % (Exception, err))
                                writer.writerow(row_list)
                            
                            csv_text=string_file.getvalue()
                            if bool(int(_params.get('compress',0))):
                                mimetype='application/zip'
                                zip_file=StringIO.StringIO()
                                zipper=zipfile.ZipFile(zip_file, 'w')
                                zipper.writestr("%s.csv" % _params.get('file_name',microtime_slug()), csv_text )
                                zipper.close()
                                response=zip_file.getvalue()
                                Content_Disposition = 'attachment; filename=%s.zip' % microtime_slug()
                            else:
                                mimetype='text/csv'
                                response=csv_text
                                Content_Disposition = 'attachment; filename=%s.csv' % microtime_slug()
                    if csv_text=="":
                        response="No data to convert"
                        HttpResponseServerError(response)
                    else:
                        http_response=HttpResponse(response, mimetype=mimetype)
                        http_response['Content-Disposition'] = Content_Disposition
                        return http_response
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
                    fl_is_entity=self.request.META['PATH_INFO'].find("/entity/")>=0 or \
                                 self.request.META['PATH_INFO'].find("/search/")>=0 or \
                                 self.request.META['PATH_INFO'].find("/entity_export/")>=0
                    try:
                        compact=bool(int(self.params.get('compact', self.request.method=="GET")))
                        attributes=self.params.get('return_attrs', self.request.method!="GET" and "*" or "")
                        tags=self.params.get('return_tags', self.request.method!="GET" and "*" or "")
                        fl_mask_attributes_err=self.params.get('attrs_err')!="1"
                        cache_life=int(self.params.get('cache_life',0))
                        rels=self.params.get('return_rels', self.params.get('rels', ""))
                            
                    except:
                        pass
                        
                    if self.request.META['PATH_INFO'].find("/entity_export/")>=0 and self.request.method=='POST':
                        compact=False
                        attributes=self.raw_data.get('return_attrs', "")
                        tags=self.raw_data.get('return_tags', self.request.method!="GET" and "*" or "")
                        fl_mask_attributes_err=self.raw_data.get('attrs_err')!="1"
                        rels=self.raw_data.get('return_rels', self.raw_data.get('rels', ""))

                    if isinstance(result, list):
                        try:
                            if fl_is_entity:
                                self.data=list(item.to_dict(bool(int(self.params.get('compact', 0))), 
                                                            attributes, 
                                                            tags, 
                                                            rels, 
                                                            fl_mask_attributes_err=fl_mask_attributes_err, 
                                                            cache_life=cache_life, 
                                                            fl_set_cache_date=fl_set_cache_date) for item in result)
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
        
        for key in ('count', 'page', 'page_size'):
            value = getattr(self, key, None)
            if value is not None:
                self.response[key]=value

        if DEBUG_API:
            self.response['method']=self.method
            self.response['raw_data']=self.raw_data
            self.response['params']=self.params
                    
        return self.build_response()
    
