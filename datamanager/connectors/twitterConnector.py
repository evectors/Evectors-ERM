import MySQLdb
#import atexit
import datetime
import time
import unicodedata        
import hashlib

import urllib, urllib2
import urlparse
import uuid

import cjson

import settings

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "lib"))
import tweepy

from erm.datamanager.connectors.simple import *
from erm.settings import *
from erm.lib.api import ApiError, ERROR_CODES
from django.utils.encoding import smart_str, smart_unicode

from erm.core.models import Entity
from erm.core.entity_manager import get_entity, set_entity, add_entity

from erm.lib.logger import Logger

import inspect

INIT_STATEMENTS = ("SET NAMES UTF8", 
                   "SET AUTOCOMMIT = 0", 
                   "SET @innodb_lock_wait_timeout = 50")

#=====================generic or common errors=====================#
ERROR_CODES["3100"]="twitter connector: Missing database"
ERROR_CODES["3101"]="twitter connector: Generic error"
ERROR_CODES["3102"]="twitter connector: Database error"

#=====================create_table=====================#
ERROR_CODES["3200"]="twitter connector: Table exists" 
ERROR_CODES["3201"]="twitter connector: Table wasn't created" 
#=====================add_field=====================#
ERROR_CODES["3300"]="twitter connector: Field exists" 
ERROR_CODES["3301"]="twitter connector: Field wasn't created" 
#=====================set_field=====================#
ERROR_CODES["3400"]="twitter connector: Field missing" 
ERROR_CODES["3401"]="twitter connector: Field wasn't updated" 
#=====================delete_field=====================#
ERROR_CODES["3500"]="twitter connector: Field missing" 
ERROR_CODES["3501"]="twitter connector: Field wasn't deleted" 
#=====================init=====================#
ERROR_CODES["3600"]="twitter connector: Table exists" 

#=====================delete_table=====================#
ERROR_CODES["3700"]="twitter connector: Table missing" 
ERROR_CODES["3701"]="twitter connector: Table not deleted" 

#=====================add_record=====================#
ERROR_CODES["3800"]="twitter connector: Not null entity id is required" 
ERROR_CODES["3801"]="twitter connector: Entity record is already present" 
ERROR_CODES["3802"]="twitter connector: Entity record not created" 
ERROR_CODES["3803"]="twitter connector: Entity record add issue" 

#=====================update_record=====================#
ERROR_CODES["3900"]="twitter connector: Not null entity id is required" 
ERROR_CODES["3901"]="twitter connector: Entity record not found" 
ERROR_CODES["3902"]="twitter connector: Entity record update issue" 

#=====================delete_record=====================#
ERROR_CODES["3910"]="twitter connector: Not null entity id is required" 
ERROR_CODES["3911"]="twitter connector: Entity record not deleted" 

#=====================get_record=====================#
ERROR_CODES["3920"]="twitter connector: Not null entity id is required" 
ERROR_CODES["3921"]="twitter connector: Entity record missing" 
#=====================execute=====================#
ERROR_CODES["3930"]="twitter connector: execute error" 
#=====================oauth=====================#
ERROR_CODES["3940"]="twitter connector: callback_url is required" 


TW_FIELDS_MAP=dict()
TW_FIELDS_MAP['created_at']='datetime'
TW_FIELDS_MAP['description']='raw_text'
TW_FIELDS_MAP['favourites_count']='integer'
TW_FIELDS_MAP['followers_count']='integer'
TW_FIELDS_MAP['following']='boolean'
TW_FIELDS_MAP['friends_count']='integer'
TW_FIELDS_MAP['geo_enabled']='boolean'
TW_FIELDS_MAP['id']='integer'
TW_FIELDS_MAP['location']='string'
TW_FIELDS_MAP['name']='string'
TW_FIELDS_MAP['notifications']='boolean'
TW_FIELDS_MAP['profile_background_color']='string'
TW_FIELDS_MAP['profile_background_image_url']='image'
TW_FIELDS_MAP['profile_background_tile']='boolean'
TW_FIELDS_MAP['profile_image_url']='image'
TW_FIELDS_MAP['profile_link_color']='string'
TW_FIELDS_MAP['profile_sidebar_border_color']='string'
TW_FIELDS_MAP['profile_sidebar_fill_color']='string'
TW_FIELDS_MAP['profile_text_color']='string'
TW_FIELDS_MAP['protected']='boolean'
TW_FIELDS_MAP['screen_name']='string'
TW_FIELDS_MAP['statuses_count']='integer'
TW_FIELDS_MAP['status']='string'
TW_FIELDS_MAP['time_zone']='string'
TW_FIELDS_MAP['url']='string'
TW_FIELDS_MAP['utc_offset']='integer'
TW_FIELDS_MAP['verified']='boolean'

TW_INNER_RECORDS=[{'slug':'cache_refresh_time', 'kind':'datetime'}, {'slug':'token_key', 'kind':'string'}, {'slug':'token_secret', 'kind':'string'}]
TW_INNER_FIELDS=[item['slug'] for item in TW_INNER_RECORDS]

CONNECTOR_REMOTE_FIELDS=TW_FIELDS_MAP.keys()

def json_decode(s):
    h,d,u=cjson.__version__.split(".")
    if (int(h)*100+int(d)*10+int(u))<=105:
        s=s.replace('\/', '/')
    return cjson.decode(s)

class CustomConnector(SimpleDbConnector):
    
    def __init__(self, object_name, fl_create_table=False, fields_desc=None):
        self.cache_life=0
        super(CustomConnector, self).__init__(object_name, fl_create_table=False, fields_desc=None)
#        threshold=getattr(settings, "TW_CONNECTOR_LOG_THRESHOLD", getattr(settings, "LOG_THRESHOLD","NOTSET"))
#        logfile=getattr(settings, "TW_CONNECTOR_LOG_FILENAME", getattr(settings, "LOG_FILE_NAME", "generic_log"))
##        self.logger=Logger(threshold, logfile, logger_name='twitterconnector')
#        self.logger.warning("%s - %s" % (threshold,logfile))
        self.oauth_tokens_db_name='twitter_oauth_temp_tokens'
        self.oauth_pending_tokens_table_name='pending_tokens'
        self.TEMP_TOKENS_FIELDS={"token":"varchar(255)",
                            "key":"varchar(255)",
                            "secret":"varchar(255)"}

    def get_default_attributes(self):
        return [{"slug":key, "kind":value} for key,value in TW_FIELDS_MAP.items()]

    def create_table(self, fields):
        for _field in TW_INNER_RECORDS:
            if not fields.has_key(_field['slug']):
                fields[_field['slug']]=_field
        super(CustomConnector, self).create_table(fields)
        
    def update_fields(self, fields):
        for _field in TW_INNER_RECORDS:
            if not fields.has_key(_field['slug']):
                fields[_field['slug']]=_field
        super(CustomConnector, self).update_fields(fields)
        
    def add_record(self, entity_id, attributes):
        '''Adding a record in this context means IMO:
            -add the record to the db table
            -connect to FaceBook
            -Fetch user info
            -Populate the record
            -update the cache_refresh_time field'''
        inner_attributes={"cache_refresh_time":datetime.datetime.now()}
        super(CustomConnector, self).add_record(entity_id, inner_attributes)
        #attributes=self.get_record(entity_id, [item['slug'] for item in self.get_default_attributes()])
                    
    def get_api(self, entity_obj=None, entity_id=None):
        _api=None
        credentials = super(CustomConnector, self).get_record(entity_id, TW_INNER_FIELDS)
        if credentials["token_key"] and credentials["token_secret"]:
            auth = self.get_auth()
            auth.set_access_token(credentials["token_key"], credentials["token_secret"])
            _api = tweepy.API(auth)
        if not _api:
            if not entity_obj:
                entity_obj=Entity.objects.get(id=entity_id)
            auth=tweepy.BasicAuthHandler(entity_obj.slug, entity_obj.password)
            _api = tweepy.API(auth)
        return _api

    def get_auth(self, callback_url=None):
        consumer_token=TWITTER_APP_CONSUMER_KEY
        consumer_secret=TWITTER_APP_CONSUMER_SECRET
        if callback_url:
            self.auth = tweepy.OAuthHandler(consumer_token, consumer_secret, callback_url)
        else:
            self.auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
        return self.auth
            
    def get_record(self, entity_id, fields_list, cache_life=0, fl_set_cache_date=False):
        try:
            if entity_id!="":
                if len(fields_list):
                    fl_cache=False
                    if cache_life>0:
                        self.cursor.execute(QUERY_GET_RECORD % ('cache_refresh_time', DM_DATABASE_NAME, self.object_name, "entity_id=%s" % entity_id))
                        fl_cache = self.cursor.fetchall()[0][0]+datetime.timedelta(seconds=cache_life)>datetime.datetime.now()
                    if not fl_cache:
                        attributes=dict()
                        remote_attrs=list()
                        local_attrs=list()
                        
                        for key in fields_list:
                            if (key in CONNECTOR_REMOTE_FIELDS):
                                remote_attrs.append(key)
                            else:
                                local_attrs.append(key)
                        
                        if len(remote_attrs):
                            api=self.get_api(entity_id=entity_id)
                            me=api.me()
                            for key in remote_attrs:
                                if key!="status":
                                    attributes[key]=getattr(me,key)
                                else:
                                    attributes[key]=getattr(me,key).text
                            local_db_attrs=attributes
                            if len(remote_attrs)==len(CONNECTOR_REMOTE_FIELDS) or fl_set_cache_date:
                                local_db_attrs['cache_refresh_time']=datetime.datetime.now()
                            super(CustomConnector, self).update_record(entity_id, local_db_attrs)
                        if len(local_attrs):
                            for key, value in super(CustomConnector, self).get_record(entity_id, local_attrs):
                                attributes[key]=value

                        return attributes    
                    else:
                        return super(CustomConnector, self).get_record(entity_id, fields_list)
#                        if self.record_exists({"entity_id":entity_id}):
#                            self.cursor.execute(QUERY_GET_RECORD % ("`,`".join(fields_list), DM_DATABASE_NAME, self.object_name, "entity_id=%s" % entity_id))
#                            record=[dict(zip(fields_list, row)) for row in self.cursor.fetchall()]
#                            #record=dict(zip(fields_list, row) for row in self.cursor.fetchall())
#                            return record[0]
#                        else:
#                           raise ApiError(None, 3921, entity_id)
                else:
                    return dict()
            else:
               raise ApiError(None, 3920)
        except Exception, err:
           raise ApiError(None, 3101, err)

    def get_oauth_url(self, entity_id=None, params={'callback_url':None}):
        QUERY_TABLE_EXISTS='SHOW TABLES LIKE `%s`;'
        QUERY_CREATE_TABLE="CREATE TABLE `%s`.`%s` (`creation_date` datetime NOT NULL); "        
        QUERY_ADD_FIELD="ALTER TABLE `%s`.`%s` ADD `%s` %s NOT NULL;"
        QUERY_CREATE_DB="CREATE DATABASE IF NOT EXISTS %s"
        QUERY_COUNT_DB="""SELECT count(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='%s';"""
        
        QUERY_ADD_RECORD="INSERT INTO `%s`.`%s` (`%s`) VALUES (%s);"
        callback_url=params.get('callback_url')
        if not callback_url or callback_url=="":
            raise ApiError(None, 3940)
        else:
            creation_date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            auth = self.get_auth(callback_url)
            redirect_url = auth.get_authorization_url()
            self.token=redirect_url.split('?oauth_token=')[1]
            self.key= auth.request_token.key
            self.secret=auth.request_token.secret
            
            self.cursor.execute(QUERY_COUNT_DB % self.oauth_tokens_db_name)
            _count=self.cursor.fetchone()[0]
            if not _count==1:
                self.do_query(QUERY_CREATE_DB % self.oauth_tokens_db_name)
                self.do_query(QUERY_CREATE_TABLE % (self.oauth_tokens_db_name, self.oauth_pending_tokens_table_name))
                for field_key, field_type in self.TEMP_TOKENS_FIELDS.items():
                    self.do_query(QUERY_ADD_FIELD % (self.oauth_tokens_db_name, self.oauth_pending_tokens_table_name, field_key, field_type))
            keys=list()
            values=list()
            for field_key, field_type in self.TEMP_TOKENS_FIELDS.items():
                keys.append(field_key)
                values.append(getattr(self, field_key))
            keys.append('creation_date')
            values.append(creation_date)
            _query = QUERY_ADD_RECORD % (self.oauth_tokens_db_name, 
                                        self.oauth_pending_tokens_table_name, 
                                        "`,`".join(keys),
                                        "'%s'" % ("','".join(values)))
            self.transaction_start()
            self.do_query(_query)
            self.transaction_commit()
            
            return redirect_url
 
    def oauth_validate_token(self, entity_id=None, params={}):
        pos=0
        try:
            QUERY_GET_RECORD="SELECT `%s` FROM `%s`.`%s` WHERE %s;"
            QUERY_DELETE_RECORD="DELETE FROM `%s`.`%s` WHERE %s"
            QUERY_UPDATE_RECORD=u'UPDATE `%s`.`%s` SET %s WHERE `entity_id`=%s'
            
            oauth_token = params.get('oauth_token')
            oauth_verifier = params.get('oauth_verifier')
            _query=QUERY_GET_RECORD % ("`,`".join(self.TEMP_TOKENS_FIELDS.keys()),
                                       self.oauth_tokens_db_name, 
                                        self.oauth_pending_tokens_table_name, 
                                        "token='%s'" % oauth_token)
            self.cursor.execute(_query)
            record=[dict(zip(self.TEMP_TOKENS_FIELDS.keys(), row)) for row in self.cursor.fetchall()][0]
            auth = self.get_auth()
            auth.set_request_token(record['key'],record['secret'])
            pos+=1
            auth.get_access_token(oauth_verifier)
            pos+=1
            self.key= auth.access_token.key
            pos+=1
            self.secret=auth.access_token.secret
            pos+=1
            auth.set_access_token(self.key, self.secret)
            pos+=1
            api = tweepy.API(auth)
            pos+=1
            _query=QUERY_DELETE_RECORD % (self.oauth_tokens_db_name, 
                                          self.oauth_pending_tokens_table_name, 
                                          "token='%s'" % oauth_token)
            self.transaction_start()
            self.cursor.execute(_query)
            self.transaction_commit()
            pos+=1
            me =api.me()
            pos+=1
            my_id=getattr(me,'id')
            pos+=1
            entity_type=self.object_name.split("_")[-1]
            pos+=1
            attributes={"token_key":self.key, "token_secret":self.secret}
            my_entity=get_entity({"slug":str(my_id), "type":entity_type})
            if len(my_entity)==0:
                my_entity=add_entity({"slug":str(my_id), 
                                      "type":entity_type,
                                      "attributes":attributes})
            else:
                my_entity=set_entity({"slug":str(my_id), 
                                      "type":entity_type,
                                      "attributes":attributes})

            set_list=list()
            for key, value in attributes.items():
                set_list.append("`%s`='%s'" % (key, value))

            pos+=1
            _query = QUERY_UPDATE_RECORD % (DM_DATABASE_NAME, 
                                            self.object_name, 
                                            smart_unicode(",".join(set_list)),
                                            my_entity.id)
            pos+=1
            self.transaction_start()
            self.do_query(_query)
            self.transaction_commit()
            
            return my_entity
        except Exception, err:
            err="%s - %s" % (pos, err)
            raise ApiError(None, 3100, err)
        
    def execute(self, entity_id, params):
        result=None
        method=params["method"]
        args=params["args"]
        api=self.get_api(entity_id=entity_id)
        if hasattr(api, method):
            method_funct=getattr(api, method)
            if len(args)>0:
                if "null" in args.keys():
                    if len(args)==1:
                        result=method_funct(args.values()[0])
                    else:
                        named_args=dict()
                        unnamed_arg=""
                        for _key, _value in args.items():
                            if _key != "null":
                                named_args[str(_key)]=_value 
                            else:   
                                unnamed_arg=_value
                        result=method_funct(unnamed_arg, *named_args)
                else:
                    result=method_funct(*args)
            else:
                result=method_funct()
            
            return self.normalize(result)
            
        else:
            raise ApiError(None, 3930, "method %s doesn't exist" % method)
        return result
    
    def obj_to_dict(self, obj):
        _dict=dict()
        for _key in dir(obj):
            if not inspect.ismethod(getattr(obj, _key)) and _key!="_api" and _key[0]!="_" and not ("__" in _key):
                _dict[_key]=self.normalize(getattr(obj, _key))
        return _dict
    
    def is_tweepy_obj(self, obj):
        for _key, _value in inspect.getmembers(tweepy.models, inspect.isclass):
            if isinstance(obj, _value):
                return True
        return False
    
    def normalize(self, obj):
        _normalized=None
        try:
            if isinstance(obj, list):
                _list=list()
                for _item in obj:
                    _list.append(self.normalize(_item))
                _normalized=_list
            elif isinstance(obj, dict):
                _dict=dict()
                for _key, _value in obj.items():
                    if _key!="_api":
                        _dict[_key]=self.normalize(_value)
                _normalized=_dict
            elif self.is_tweepy_obj(obj):
                _normalized=self.obj_to_dict(obj)
            else:
                _normalized=obj
        except Exception, err:
            return "%s: %s" % (Exception, err)

        return _normalized
        
    def update_status(self, entity_id, params):
        _status=list()
        try:
            if entity_id!="":
                api=self.get_api(entity_id=entity_id)
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    _params_list=dict()
                    for _key in ("status", "in_reply_to_status_id","lat", "long", "source"):
                        _params_list[_key]=params.get(_key)
                    if _params_list.get('status'):
                        if _params_list.get('in_reply_to_status_id'):
                            if _params_list.get('lat') and _params_list.get('long'):
                                _status=api.update_status(_params_list.get('status')[:140], _params_list.get('in_reply_to_status_id'), _params_list.get('lat'), _params_list.get('long'))
                        else:
                            if _params_list.get('lat') and _params_list.get('long'):
                                _status=api.update_status(_params_list.get('status')[:140], _params_list.get('lat'), _params_list.get('long'))
                            else:
                                _status=api.update_status(_params_list.get('status')[:140])
                    else:
                        raise ApiError(None, 3900, "status is required (%s)" % params)
                else:
                   self.add_record(entity_id, attributes)
                    #raise ApiError(None, 3901, entity_id)
            else:
               raise ApiError(None, 3900)
        except Exception, err:
            raise ApiError(None, 3101, err)
        
                
        return self.normalize(_status)
        
    def update_record(self, entity_id, attributes, query=QUERY_UPDATE_RECORD):
        try:
            if entity_id!="":
                api=self.get_api(entity_id=entity_id)
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    set_list=list()
                    db_attributes=dict()
                    for key, value in attributes.items():
                        if key in CONNECTOR_REMOTE_FIELDS:
                            if key=="status":
                                api.update_status(value[:140])
                        else:
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
