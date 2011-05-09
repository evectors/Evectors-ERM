import MySQLdb
#import atexit
import datetime
import time
import unicodedata        
import hashlib

import urllib, urllib2
import httplib
import uuid

import cjson
import settings

from django.db import IntegrityError
from erm.datamanager.connectors.simple import *
from erm.settings import *
from erm.lib.api import ApiError, ERROR_CODES
from django.utils.encoding import smart_str, smart_unicode

from erm.core.models import Entity

from erm.core.entity_manager import get_entity, set_entity, add_entity

from erm.lib.logger import Logger

from erm.datamanager.connectors.lib.oauth import Oauth2WebFlow

from urlparse import urlparse
from erm.lib.misc_utils import string_to_slug, microtime_slug

INIT_STATEMENTS = ("SET NAMES UTF8", 
                   "SET AUTOCOMMIT = 0", 
                   "SET @innodb_lock_wait_timeout = 50")

#=====================generic or common errors=====================#
ERROR_CODES["3100"]="facebook connector: Missing database"
ERROR_CODES["3101"]="facebook connector: Generic error"
ERROR_CODES["3102"]="facebook connector: Database error"

#=====================create_table=====================#
ERROR_CODES["3200"]="facebook connector: Table exists" 
ERROR_CODES["3201"]="facebook connector: Table wasn't created" 
#=====================add_field=====================#
ERROR_CODES["3300"]="facebook connector: Field exists" 
ERROR_CODES["3301"]="facebook connector: Field wasn't created" 
#=====================set_field=====================#
ERROR_CODES["3400"]="facebook connector: Field missing" 
ERROR_CODES["3401"]="facebook connector: Field wasn't updated" 
#=====================delete_field=====================#
ERROR_CODES["3500"]="facebook connector: Field missing" 
ERROR_CODES["3501"]="facebook connector: Field wasn't deleted" 
#=====================init=====================#
ERROR_CODES["3600"]="facebook connector: Table exists" 

#=====================delete_table=====================#
ERROR_CODES["3700"]="facebook connector: Table missing" 
ERROR_CODES["3701"]="facebook connector: Table not deleted" 

#=====================add_record=====================#
ERROR_CODES["3800"]="facebook connector: Not null entity id is required" 
ERROR_CODES["3801"]="facebook connector: Entity record is already present" 
ERROR_CODES["3802"]="facebook connector: Entity record not created" 
ERROR_CODES["3803"]="facebook connector: Entity record add issue" 

#=====================update_record=====================#
ERROR_CODES["3900"]="facebook connector: Not null entity id is required" 
ERROR_CODES["3901"]="facebook connector: Entity record not found" 
ERROR_CODES["3902"]="facebook connector: Entity record update issue" 

#=====================delete_record=====================#
ERROR_CODES["3910"]="facebook connector: Not null entity id is required" 
ERROR_CODES["3911"]="facebook connector: Entity record not deleted" 

#=====================get_record=====================#
ERROR_CODES["3920"]="facebook connector: Not null entity id is required" 
ERROR_CODES["3921"]="facebook connector: Entity record missing" 
ERROR_CODES["3922"]="facebook connector: an Entity with the same facebook id already exist" 
ERROR_CODES["3923"]="facebook connector: database error" 
ERROR_CODES["3925"]="facebook connector error" 

#=====================virtual attribute fields definition
USER_ATTRIBUTES=dict()
USER_ATTRIBUTES["id"] = "raw_text"
USER_ATTRIBUTES["first_name"] = "raw_text"
USER_ATTRIBUTES["last_name"] = "raw_text"
USER_ATTRIBUTES["name"] = "raw_text"
USER_ATTRIBUTES["link"] = "raw_text"
USER_ATTRIBUTES["about"] = "raw_text"
USER_ATTRIBUTES["birthday"] = "raw_text"
USER_ATTRIBUTES["work"] = "raw_text"
USER_ATTRIBUTES["education"] = "raw_text"
USER_ATTRIBUTES["email"] = "raw_text"
USER_ATTRIBUTES["website"] = "raw_text"
USER_ATTRIBUTES["hometown"] = "raw_text"
USER_ATTRIBUTES["location"] = "raw_text"
USER_ATTRIBUTES["bio"] = "raw_text"
USER_ATTRIBUTES["quotes"] = "raw_text"
USER_ATTRIBUTES["gender"] = "raw_text"
USER_ATTRIBUTES["interested_in"] = "raw_text"
USER_ATTRIBUTES["meeting_for"] = "raw_text"
USER_ATTRIBUTES["relationship_status"] = "raw_text"
USER_ATTRIBUTES["religion"] = "raw_text"
USER_ATTRIBUTES["political"] = "raw_text"
USER_ATTRIBUTES["verified"] = "raw_text"
USER_ATTRIBUTES["significant_other"] = "raw_text"
USER_ATTRIBUTES["timezone"] = "raw_text"
USER_ATTRIBUTES["third_party_id"] = "raw_text"
USER_ATTRIBUTES["last_updated"] = "raw_text"
USER_ATTRIBUTES["locale"] = "raw_text"

USER_ATTRIBUTES_KEYS=USER_ATTRIBUTES.keys()
#=====================private attribute fields definition
CONNECTOR_LOCAL_FIELDS_MAP=dict()

CONNECTOR_INNER_RECORDS=[{'slug':'access_token', 'kind':'raw_text'}]

CONNECTOR_INNER_FIELDS=[item['slug'] for item in CONNECTOR_INNER_RECORDS]

USER_CONNECTIONS=dict()
USER_CONNECTIONS['home'] = "raw_text"
USER_CONNECTIONS['feed'] = "raw_text"
USER_CONNECTIONS['tagged'] = "raw_text"
USER_CONNECTIONS['posts'] = "raw_text"
USER_CONNECTIONS['picture'] = "raw_text"
USER_CONNECTIONS['friends'] = "raw_text"
USER_CONNECTIONS['activities'] = "raw_text"
USER_CONNECTIONS['interests'] = "raw_text"
USER_CONNECTIONS['music'] = "raw_text"
USER_CONNECTIONS['books'] = "raw_text"
USER_CONNECTIONS['movies'] = "raw_text"
USER_CONNECTIONS['television'] = "raw_text"
USER_CONNECTIONS['likes'] = "raw_text"
USER_CONNECTIONS['photos'] = "raw_text"
USER_CONNECTIONS['albums'] = "raw_text"
USER_CONNECTIONS['videos'] = "raw_text"
USER_CONNECTIONS['groups'] = "raw_text"
USER_CONNECTIONS['statuses'] = "raw_text"
USER_CONNECTIONS['links'] = "raw_text"
USER_CONNECTIONS['notes'] = "raw_text"
USER_CONNECTIONS['events'] = "raw_text"
USER_CONNECTIONS['inbox'] = "raw_text"
USER_CONNECTIONS['outbox'] = "raw_text"
USER_CONNECTIONS['updates'] = "raw_text"
USER_CONNECTIONS['accounts'] = "raw_text"
USER_CONNECTIONS['checkins'] = "raw_text"
USER_CONNECTIONS['platformrequests'] = "raw_text"

USER_CONNECTIONS_KEYS=USER_CONNECTIONS.keys()

CONNECTOR_REMOTE_FIELDS=CONNECTOR_LOCAL_FIELDS_MAP.keys() + USER_CONNECTIONS.keys()

#=====================connector

class CustomConnector(SimpleDbConnector):
    
    def __init__(self, object_name, fl_create_table=False, fields_desc=None):
        self.cache_life=0
        super(CustomConnector, self).__init__(object_name, fl_create_table=False, fields_desc=None)
        threshold=getattr(settings, "FB_CONNECTOR_LOG_THRESHOLD", getattr(settings, "LOG_THRESHOLD","NOTSET"))
        logfile=getattr(settings, "FB_CONNECTOR_LOG_FILENAME", getattr(settings, "LOG_FILE_NAME", "generic_log"))
        #self.logger=Logger(threshold, logfile, logger_name='facebookconnector')
        self.empty_field_descriptor={'status': u'A', 
                'kind': u'', 
                'unique': False, 
                'name': u'', 
                'searchable': False, 
                'default': u'', 
                'editable': False, 
                'is_key': False, 
                'slug': u'test', 
                'blank': True, 
                'null': True}

    def do_query(self, query):
        try:
            self.cursor.execute(query)
            #self.connection.commit ()
        except Exception, err:
            if DEBUG_SQL:
                err = "%s (%s)" % (err, query)
            raise Exception(err)
    
    def get_default_attributes(self):
        return [{"slug":key, "kind":value} for key,value in CONNECTOR_LOCAL_FIELDS_MAP.items()]

    def get_remote_attributes(self):
        _attributes=[{"slug":"dummy", "kind":"raw_text"}]
        for _map in (USER_ATTRIBUTES, USER_CONNECTIONS):
            for key,value in _map.items():
                _attributes.append({"slug":key, "kind":value})
        return _attributes

    def merge_fields(self, fields):
        for _field in CONNECTOR_INNER_RECORDS:
            if not fields.has_key(_field['slug']):
                _complete_field=self.empty_field_descriptor
                _complete_field.update(_field)
                fields[_field['slug']]=_complete_field
        return fields
    
    def create_table(self, fields):
        super(CustomConnector, self).create_table(self.merge_fields(fields))
        
    def update_fields(self, fields):
        super(CustomConnector, self).update_fields(self.merge_fields(fields))
                            
    def get_record(self, entity_id, fields_list, cache_life=0, fl_set_cache_date=False):
        try:
            if entity_id!="":
                user_attrs=list()
                connection_attrs=dict()
                result = dict()
                get_connections="dummy" not in fields_list
                for field in fields_list:
                    if field in USER_ATTRIBUTES_KEYS:
                        user_attrs.append(field)
                    elif field in USER_CONNECTIONS_KEYS and get_connections:
                        try:
                            connection_attrs[field]=self.graph(entity_id, {"object":field})
                        except Exception, err:
                            connection_attrs[field]=err

                debug_dict=dict()
                
#                 debug_dict["user_attrs"]=user_attrs
#                 debug_dict["fields_list"]=fields_list
#                 debug_dict["connection_attrs"]=connection_attrs
# 
                if len(user_attrs)>0 or len(fields_list)==0:
                    try:
                        result = self.graph(entity_id, {})
                    except Exception, err:
                        result[err]=err

                if len(user_attrs):
                    result=dict((field, result.get(field)) for field in fields_list)
                
                result.update(connection_attrs)
                result.update(debug_dict)
                
                return result
                
            else:
               raise ApiError(None, 3920)
        except Exception, err:
           raise ApiError(None, 3101, err)

    def graph(self, entity_id, params, access_token=None):
        if entity_id is not None or access_token is not None:
            result=dict()
            if access_token is None:
                access_token=super(CustomConnector, self).get_record(entity_id, ["access_token"])["access_token"]
            graph_api=params.get('object', 'me')
            endpoint='graph.facebook.com'
            if graph_api!='me':
                graph_api="me/%s" % graph_api
            
            _method = params.get('method', 'GET')
            if _method == 'GET':
                url = '/%s?access_token=%s' % (graph_api, access_token)
                connection = httplib.HTTPSConnection(endpoint)
                connection.request('GET', url)
                response = connection.getresponse()
                
                if response is None:
                    self.error = "No HTTP response received."
                    connection.close()
                    return None
            
                if graph_api=='me/picture' and response.status in (301,302,):
                    result = response.getheader('location', '')
                else:
                    response = response.read()
                    result=cjson.decode(response)

                connection.close()

            elif _method == 'POST':
                url = 'https://%s/%s' % (endpoint, graph_api)
                api_params = params.get('api_params',dict())
                api_params['access_token']=access_token
                data = urllib.urlencode(api_params)
                req = urllib2.Request(url, data)
                response = urllib2.urlopen(req)
                response = response.read()
                result=cjson.decode(response)

            return result
        else:
            raise ApiError(None, 3900)        

    def update_record(self, entity_id, attributes, query=QUERY_UPDATE_RECORD):
        try:
            if entity_id!="":
                uid=Entity.objects.get(id=entity_id).slug
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    set_list=list()
                    db_attributes=dict()
                    for key, value in attributes.items():
                        if key in ("status", "message", "post"):
                            if isinstance(value, dict):
                                args = value
                            else:
                                args={"message":value}
                            self.graph(entity_id, {"object":"feed", 
                                                   "method":"POST", 
                                                   "api_params":args})
                        elif key in USER_ATTRIBUTES_KEYS:
                            pass
                        else:
                            if not USER_ATTRIBUTES.has_key(key):
                                db_attributes[key]=value
                    if len(db_attributes):
                        super(CustomConnector, self).update_record(entity_id, db_attributes, query)
                else:
                   self.add_record(entity_id, attributes)
                    #raise ApiError(None, 3901, entity_id)
            else:
               raise ApiError(None, 3900)
        except Exception, err:
            raise ApiError(None, 3101, err)

#=============================OAuth authentication

    def get_oauth_url(self, entity_id=None, params={}):
        next_url=params.get('next_url', settings.FACEBOOK_CONNECTOR_REDIRECT_URI)
        decode = params.get('decode', False)
        if decode:
            next_url=urllib.unquote(next_url)
        client=Oauth2WebFlow('graph.facebook.com', 
                                        settings.FACEBOOK_CONNECTOR_API_KEY,
                                        settings.FACEBOOK_CONNECTOR_SECRET_KEY, 
                                        next_url)
        return client.getAuthorizeURL(params.get('scope', ','.join(FACEBOOK_PERMISSIONS)))
 
    def oauth_validate_token(self, entity_id=None, params={}):
        next_url=params.get('next_url', settings.FACEBOOK_CONNECTOR_REDIRECT_URI)
        decode = params.get('decode', False)
        if decode:
            next_url=urllib.unquote(next_url)
        client=Oauth2WebFlow('graph.facebook.com', 
                                        settings.FACEBOOK_CONNECTOR_API_KEY,
                                        settings.FACEBOOK_CONNECTOR_SECRET_KEY, 
                                        next_url)
        try:
            tokenized_url = params.get('tokenized_url')
            if tokenized_url and tokenized_url!="":
                decode = params.get('decode', False)
        
                if decode:
                    tokenized_url=urllib.unquote(tokenized_url)
                parsed=urlparse(tokenized_url)
                parsed_params=dict([item.split('=')[0], item.split('=')[1]] for item in parsed.query.split('&'))   
                code = urllib.unquote(parsed_params.get('code'))
                access_token = client.getAccessToken(code)
                
                facebook_params=None
                if access_token:
                    entity_type=self.object_name.split("_")[-1]
                    if entity_id is None:
                        facebook_params=self.graph(None, {}, access_token)
                        remote_id = "%s" % facebook_params['id']
                        entity_name="%s %s" % (facebook_params.get('first_name'), facebook_params.get('last_name'))
                        entity_slug=microtime_slug()
                        try:
                            my_entity=add_entity({"slug":entity_slug, 
                                                  "name":entity_name, 
                                                  "type":entity_type,
                                                  "remote_id":remote_id,
                                                  "attributes":{"access_token": access_token}
                                                  })
                            entity_id=my_entity.id
                        except Exception, err:
                            try:
                                my_entity=get_entity({"remote_id":remote_id, "type":entity_type})[0]
                                entity_id=my_entity.id
                                super(CustomConnector, self).update_record(entity_id, {"access_token": access_token})
                            except Exception, err:
                                raise ApiError(None, 3923, "----->%s - %s" % (Exception, err))
                    else:
                        my_entity=get_entity({"id":str(entity_id), "type":entity_type})[0]
                        super(CustomConnector, self).update_record(entity_id, {"access_token": access_token})
                else:
                    raise ApiError(None, 3925)
                
                if facebook_params is None:
                    facebook_params=self.graph(None, {}, access_token)
                
                result=my_entity.to_dict(False, "", "")
                result['attributes']=facebook_params
                result['attributes']['email']=facebook_params.get('email', None)
                return result
            else:
                raise ApiError(None, 3925)
        except Exception, err:
            reauthenticate=self.get_oauth_url()
            raise ApiError(None, "%s" % reauthenticate, err)
        else:
            raise ApiError(None, 3900)