import MySQLdb
#import atexit
import datetime
import time
import unicodedata        
import hashlib

import urllib, urllib2

import uuid

import cjson

import settings

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "lib"))
import tweepy

from erm.datamanager.connectors.simple import *

import settings

from erm.settings import *

from erm.lib.api import ApiError, ERROR_CODES
from django.utils.encoding import smart_str, smart_unicode

from erm.core.models import Entity
from erm.core.entity_manager import get_entity, set_entity, add_entity

from erm.lib.logger import Logger

import inspect

from urlparse import urlparse

from erm.lib.misc_utils import string_to_slug, microtime_slug

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
TW_FIELDS_MAP['dummy']='boolean'

TW_FIELDS_MAP['user_timeline']='raw_text'
TW_FIELDS_MAP['friends_timeline']='raw_text'
TW_FIELDS_MAP['followers']='raw_text'
TW_FIELDS_MAP['friends_ids']='raw_text'
TW_FIELDS_MAP['friends']='raw_text'

TW_EXTRA_METHODS_ATTRS=['user_timeline', 'friends_timeline', 'followers', 'friends_ids', 'friends']

TW_INNER_RECORDS=[{'slug':'token_key', 'kind':'string'}, 
                  {'slug':'token_secret', 'kind':'string'}]
TW_INNER_FIELDS=[item['slug'] for item in TW_INNER_RECORDS]

CONNECTOR_REMOTE_FIELDS=TW_FIELDS_MAP.keys()
CONNECTOR_REMOTE_FIELDS_MAP=TW_FIELDS_MAP

#=====================ancillar table sql queries for oauth
QUERY_CREATE_OAUTH_TABLE="""CREATE TABLE IF NOT EXISTS `%s`.`oauth_tokens` 
                     (`token` varchar(255) NOT NULL PRIMARY KEY, 
                      `pickled` blob,
                      `connector` varchar(255),
                      `created` datetime); """        
QUERY_ADD_OAUTH_RECORD="INSERT INTO `%s`.`oauth_tokens` (`token`,`pickled`, `created`, `connector`) VALUES ('%s', '%s', '%s', '%s')"
QUERY_GET_OAUTH_RECORD="SELECT `pickled` FROM `%s`.`oauth_tokens` WHERE `token`='%s' AND `connector`='%s'"
QUERY_DELETE_OAUTH_RECORD="DELETE FROM `%s`.`oauth_tokens` WHERE `token`='%s' AND `connector`='%s'"

#=====================
def json_decode(s):
    h,d,u=cjson.__version__.split(".")
    if (int(h)*100+int(d)*10+int(u))<=105:
        s=s.replace('\/', '/')
    return cjson.decode(s)

STATUS_FIELDS=['favorited', 
                'geo', 
                'id', 
                'id_str', 
                'in_reply_to_screen_name', 
                'in_reply_to_status_id', 
                'in_reply_to_status_id_str', 
                'in_reply_to_user_id', 
                'in_reply_to_user_id_str', 
                'place', 
                'retweet_count', 
                'retweeted', 
                'source', 
                'source_url', 
                'text', 
                'truncated']
                
USER_FIELDS = ['id', 
                'verified', 
                'profile_sidebar_fill_color', 
                'profile_text_color', 
                'followers_count', 
                'protected', 
                'location', 
                'profile_background_color', 
                'utc_offset', 
                'statuses_count', 
                'description', 
                'friends_count', 
                'profile_link_color', 
                'profile_image_url', 
                'notifications', 
                'geo_enabled', 
                'profile_background_image_url', 
                'name', 
                'profile_background_tile', 
                'favourites_count', 
                'screen_name', 
                'url', 
                'time_zone', 
                'profile_sidebar_border_color', 
                'following']


def obj_to_dict(object, fields_list):
    result=dict()
    for key in fields_list:
        try:
            result[key]=getattr(object, key)
        except Exception, err:
            result[key]="%s" % err
    return result

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
        self.entity_obj = None
        
    def get_default_attributes(self):
        return []#{"slug":key, "kind":value} for key,value in TW_INNER_RECORDS.items()]

    def get_remote_attributes(self):
        return [{"slug":key, "kind":value} for key,value in CONNECTOR_REMOTE_FIELDS_MAP.items()]

    def merge_fields(self, fields):
        for _field in TW_INNER_RECORDS:
            if not fields.has_key(_field['slug']):
                _complete_field=self.empty_field_descriptor
                _complete_field.update(_field)
                fields[_field['slug']]=_complete_field
        return fields
    
    def create_table(self, fields):
        super(CustomConnector, self).create_table(self.merge_fields(fields))
        
    def update_fields(self, fields):
        super(CustomConnector, self).update_fields(self.merge_fields(fields))
                                                
    def get_api(self, entity_obj=None, entity_id=None):
        _api=None
        if not entity_obj:
            if self.entity_obj is None:
                self.entity_obj=Entity.objects.get(id=entity_id)
            entity_obj=self.entity_obj
        credentials = super(CustomConnector, self).get_record(entity_id, TW_INNER_FIELDS)
        if credentials["token_key"] and credentials["token_secret"]:
            auth = self.get_auth()
            auth.set_access_token(credentials["token_key"], credentials["token_secret"])
            _api = tweepy.API(auth)
        if not _api:
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
            
    def get_record(self, entity_id, fields_list):
        try:
            if entity_id!="":
                if len(fields_list):
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
                            if key in TW_EXTRA_METHODS_ATTRS:
                                if not 'dummy' in remote_attrs:
                                    if key in ['user_timeline', 'friends_timeline'] :
                                        _timeline=getattr(api, key)()
                                        attributes[key]=cjson.encode(list(obj_to_dict(status, STATUS_FIELDS) for status in _timeline) )
                                    elif key in ['followers'] :
                                        _users=getattr(api, key)()
                                        attributes[key]=cjson.encode(list(obj_to_dict(user, USER_FIELDS) for user in _users) )
                                    elif key in ['friends_ids']:
                                        attributes[key]=cjson.encode(getattr(api, key)())
                                    elif key in ['friends']:
                                        friends_ids=api.friends_ids()
                                        friends_array=list()
                                        for _id in friends_ids:
                                            try:
                                                friends_array.append(obj_to_dict(api.get_user(_id), USER_FIELDS))
                                            except Exception, err:
                                                friends_array.append("%s" % err )
                                        attributes[key]=cjson.encode(friends_array)
                            elif key!="status":
                                if key!="dummy":
                                    attributes[key]=getattr(me,key)
                            else:
                                attributes[key]=""
                                try:
                                    attributes[key]=getattr(me,key).text
                                except Exception, err:
                                    pass
#                         local_db_attrs=attributes
#                         if len(remote_attrs)==len(CONNECTOR_REMOTE_FIELDS) or fl_set_cache_date:
#                             local_db_attrs['cache_refresh_time']=datetime.datetime.now()
#                         super(CustomConnector, self).update_record(entity_id, local_db_attrs)
                    if len(local_attrs):
                        for key, value in super(CustomConnector, self).get_record(entity_id, local_attrs):
                            attributes[key]=value

                    return attributes    
                else:
                    return dict()
            else:
               raise ApiError(None, 3920)
        except Exception, err:
           raise ApiError(None, 3101, err)

    def get_oauth_url(self, entity_id=None, params={}):
        callback_url=params.get('next_url', settings.TWITTER_APP_CALLBACK_URL)
        decode = params.get('decode', False)

        if decode:
            callback_url=urllib.unquote(callback_url)

        creation_date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        auth = self.get_auth(callback_url)
        redirect_url = auth.get_authorization_url(signin_with_twitter=params.get('mode', settings.TWITTER_APP_OAUTH_MODE)=='authenticate')
        self.token=redirect_url.split('?oauth_token=')[1]
        self.key= auth.request_token.key
        self.secret=auth.request_token.secret
        
        token_dict=dict()
        for field_key, field_type in self.TEMP_TOKENS_FIELDS.items():
            token_dict[field_key]=getattr(self, field_key)
        token_dict['creation_date']=creation_date

        try:
            query=None
            _value = cjson.encode(token_dict)
            self.transaction_start()
            try:
                query=QUERY_CREATE_OAUTH_TABLE % (DM_DATABASE_NAME)
                self.do_query(query)
            except Exception, err:
                if not ("already exists" in ("%s" % err)):
                    Logger().error("Error: %s (%s) - %s" % (err, query, Exception))
                    raise Exception, err
            
            try:
                query=QUERY_DELETE_OAUTH_RECORD % (DM_DATABASE_NAME,redirect_url, "twitterConnector")
                self.do_query(query)
            except Exception, err:
                Logger().error("Error: %s (%s)" % (err, query))
                raise Exception, err

            query=QUERY_ADD_OAUTH_RECORD % (DM_DATABASE_NAME,
                                      self.token,
                                      _value, 
                                      creation_date, 
                                      "twitterConnector")
            self.do_query(query)

            self.transaction_commit()
        except Exception, err:
            self.transaction_rollback()
            raise ApiError(None, 3102, "%s (%s): %s - [%s]" % (entity_id, err, query, Exception))
            
        return redirect_url
 
    def trace(self, pos):
        self.logger.debug("%s" % pos)
        pos+=1

    def oauth_validate_token(self, entity_id=None, params={}):
        pos=1
        self.trace(pos)
        try:
    
            tokenized_url = params.get('tokenized_url')
            decode = params.get('decode', False)

            if decode:
                tokenized_url=urllib.unquote(tokenized_url)
            parsed=urlparse(tokenized_url)
        
            self.trace(pos)
            
            parsed_params=dict([item.split('=')[0], item.split('=')[1]] for item in parsed.query.split('&'))                

            oauth_token = urllib.unquote(parsed_params.get('oauth_token'))

            oauth_verifier = urllib.unquote(parsed_params.get('oauth_verifier'))

            self.trace(pos)
            
            self.cursor.execute(QUERY_GET_OAUTH_RECORD % (DM_DATABASE_NAME, oauth_token, "twitterConnector"))
    
            record=[dict(zip(['pickled'], row)) for row in self.cursor.fetchall()]
            record = cjson.decode(record[0].get('pickled'))

            self.trace(pos)
            
            auth = self.get_auth()
            auth.set_request_token(record['key'],record['secret'])

            auth.get_access_token(oauth_verifier)

            self.trace(pos)
            
            self.key= auth.access_token.key
            self.secret=auth.access_token.secret

            auth.set_access_token(self.key, self.secret)

            api = tweepy.API(auth)

            self.trace(pos)
            
            try:
                query=QUERY_DELETE_OAUTH_RECORD % (DM_DATABASE_NAME,oauth_token, "twitterConnector")
                self.do_query(query)
            except Exception, err:
                Logger().error("Error: %s (%s)" % (err, query))
                #raise Exception, err

            me =api.me()
            my_id=getattr(me,'id')
            my_name=getattr(me,'name')
            if my_name is None or my_name =="":
                my_name=getattr(me,'screen_name')
            entity_type=self.object_name.split("_")[-1]
            attributes={"token_key":self.key, "token_secret":self.secret}

            self.trace(pos)
            
            entity_type=self.object_name.split("_")[-1]
            if entity_id is None:
                remote_id = "%s" % getattr(me,'id')
                entity_name=my_name
                entity_slug=microtime_slug()
                try:
                    my_entity=add_entity({"slug":entity_slug, 
                                          "name":entity_name, 
                                          "type":entity_type,
                                          "remote_id":remote_id,
                                          "attributes":attributes
                                          })
                    entity_id=my_entity.id
                except Exception, err:
                    try:
                        my_entity=get_entity({"remote_id":remote_id, "type":entity_type})[0]
                        entity_id=my_entity.id
                        super(CustomConnector, self).update_record(entity_id, attributes)
                    except Exception, err:
                        raise ApiError(None, 3923, "%s - %s" % (Exception, err))
            else:
                my_entity=get_entity({"id":str(entity_id), "type":entity_type})[0]
                super(CustomConnector, self).update_record(entity_id, attributes)
            
            self.trace(pos)
            
            try:
                query=QUERY_DELETE_OAUTH_RECORD % (DM_DATABASE_NAME,oauth_token, "twitterConnector")
                self.do_query(query)
            except Exception, err:
                Logger().error("Error: %s (%s)" % (err, query))

            return my_entity
        except Exception, err:
            self.logger.error("%s" % err)
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
        
    def update_status(self, entity_id, value):
        params=dict()
        if isinstance(value, dict):
            params=value
        else:
            params["status"]=value

        _status=list()
        try:
            if entity_id!="":
                api=self.get_api(entity_id=entity_id)
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    if params.get('status') is not None:
                        _status=api.update_status(**params)
                    else:
                        raise ApiError(None, 3900, "status is required (%s)" % params)
                else:
                    #self.add_record(entity_id, attributes)
                    raise ApiError(None, 3901, entity_id)
            else:
               raise ApiError(None, 3900)
        except Exception, err:
            raise ApiError(None, 3101, err)
        
                
        return self.normalize(_status)
        
    def update_record(self, entity_id, attributes, query=QUERY_UPDATE_RECORD):
        try:
            if entity_id!="":
#                 api=self.get_api(entity_id=entity_id)
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    set_list=list()
                    db_attributes=dict()
                    for key, value in attributes.items():
                        if key in CONNECTOR_REMOTE_FIELDS:
                            if key=="status":
                                self.update_status(entity_id, value)
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
