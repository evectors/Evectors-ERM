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

from erm.datamanager.connectors.simple import *
from erm.settings import *
from erm.lib.api import ApiError, ERROR_CODES
from django.utils.encoding import smart_str, smart_unicode

from erm.core.models import Entity
from erm.core.entity_manager import get_entity, set_entity, add_entity

from erm.lib.logger import Logger

import inspect

import base64

from urlparse import urlparse

import pickle

from erm.datamanager.connectors.lib.linkedin import LinkedIn 
from erm.lib.misc_utils import string_to_slug, microtime_slug

INIT_STATEMENTS = ("SET NAMES UTF8", 
                   "SET AUTOCOMMIT = 0", 
                   "SET @innodb_lock_wait_timeout = 50")

#=====================generic or common errors=====================#
ERROR_CODES["3100"]="linkedin connector: Missing database"
ERROR_CODES["3101"]="linkedin connector: Generic error"
ERROR_CODES["3102"]="linkedin connector: Database error"

#=====================create_table=====================#
ERROR_CODES["3200"]="linkedin connector: Table exists" 
ERROR_CODES["3201"]="linkedin connector: Table wasn't created" 
#=====================add_field=====================#
ERROR_CODES["3300"]="linkedin connector: Field exists" 
ERROR_CODES["3301"]="linkedin connector: Field wasn't created" 
#=====================set_field=====================#
ERROR_CODES["3400"]="linkedin connector: Field missing" 
ERROR_CODES["3401"]="linkedin connector: Field wasn't updated" 
#=====================delete_field=====================#
ERROR_CODES["3500"]="linkedin connector: Field missing" 
ERROR_CODES["3501"]="linkedin connector: Field wasn't deleted" 
#=====================init=====================#
ERROR_CODES["3600"]="linkedin connector: Table exists" 

#=====================delete_table=====================#
ERROR_CODES["3700"]="linkedin connector: Table missing" 
ERROR_CODES["3701"]="linkedin connector: Table not deleted" 

#=====================add_record=====================#
ERROR_CODES["3800"]="linkedin connector: Not null entity id is required" 
ERROR_CODES["3801"]="linkedin connector: Entity record is already present" 
ERROR_CODES["3802"]="linkedin connector: Entity record not created" 
ERROR_CODES["3803"]="linkedin connector: Entity record add issue" 

#=====================update_record=====================#
ERROR_CODES["3900"]="linkedin connector: Not null entity id is required" 
ERROR_CODES["3901"]="linkedin connector: Entity record not found" 
ERROR_CODES["3902"]="linkedin connector: Entity record update issue" 

#=====================delete_record=====================#
ERROR_CODES["3910"]="linkedin connector: Not null entity id is required" 
ERROR_CODES["3911"]="linkedin connector: Entity record not deleted" 

#=====================get_record=====================#
ERROR_CODES["3920"]="linkedin connector: Not null entity id is required" 
ERROR_CODES["3921"]="linkedin connector: Entity record missing" 
#=====================execute=====================#
ERROR_CODES["3930"]="linkedin connector: execute error" 
#=====================oauth=====================#
ERROR_CODES["3940"]="linkedin connector: callback_url is required" 
ERROR_CODES["3941"]="linkedin connector: service not (yet) supported" 
ERROR_CODES["3942"]="linkedin connector: the tokenized url is required" 
ERROR_CODES["3943"]="linkedin connector: authorization error" 
#=====================get file=====================#
ERROR_CODES["3950"]="linkedin connector: unable to get a client" 
ERROR_CODES["3951"]="linkedin connector: a resource_id is required" 
ERROR_CODES["3923"]="linkedin connector: database error" 
ERROR_CODES["3924"]="linkedin connector: unknown mode" 


CONNECTOR_LOCAL_FIELDS_MAP=dict()

CONNECTOR_REMOTE_FIELDS_MAP = dict()
CONNECTOR_REMOTE_FIELDS_MAP[u'id']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'first-name']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'last-name']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'headline']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'location']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'industry']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'distance']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'relation-to-viewer']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'current-status']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'current-status-timestamp']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'current-share']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'connections']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'num-connections']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'num-connections-capped']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'summary']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'specialties']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'proposal-comments']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'associations']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'honors']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'interests']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'positions']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'educations']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'three-current-positions']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'three-past-positions']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'num-recommenders']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'recommendations-received']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'phone-numbers']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'im-accounts']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'twitter-accounts']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'date-of-birth']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'main-address']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'picture-url']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'site-standard-profile-request']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'api-standard-profile-request']='raw_text'
CONNECTOR_REMOTE_FIELDS_MAP[u'public-profile-url']='raw_text'

#=====================private attribute fields definition
CONNECTOR_INNER_RECORDS=[{'slug':'access_token', 'kind':'raw_text'}, {'slug':'access_token_secret', 'kind':'raw_text'}]

CONNECTOR_INNER_FIELDS=[item['slug'] for item in CONNECTOR_INNER_RECORDS]

CONNECTOR_REMOTE_FIELDS=CONNECTOR_LOCAL_FIELDS_MAP.keys()

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

#=====================connector

class CustomConnector(SimpleDbConnector):
    
    def __init__(self, object_name, fl_create_table=False, fields_desc=None):
        self.cache_life=0
        self.api=None
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


        super(CustomConnector, self).__init__(object_name, fl_create_table=False, fields_desc=None)

    def get_default_attributes(self):
        return [{"slug":key, "kind":value} for key,value in CONNECTOR_LOCAL_FIELDS_MAP.items()]

    def get_remote_attributes(self):
        return [{"slug":key, "kind":value} for key,value in CONNECTOR_REMOTE_FIELDS_MAP.items()]

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
                            
    def get_api(self, entity_obj=None, entity_id=None, access_token = None, access_token_secret=None):
        if self.api is None:
            
            _api = LinkedIn(settings.LINKEDIN_OAUTH_CONSUMER_KEY, 
                                    settings.LINKEDIN_OAUTH_CONSUMER_SECRET, 
                                    settings.LINKEDIN_OAUTH_RETURN_URL)
            if access_token is None or access_token_secret is None:
                _token=super(CustomConnector, self).get_record(entity_id, ["access_token_secret",
                                                                    "access_token"])
                _api.access_token=_token['access_token']
                _api.access_token_secret=_token['access_token_secret']
            else:
                _api.access_token=access_token
                _api.access_token_secret=access_token_secret
            self.api = _api
        return self.api
        
    def get_record(self, entity_id, fields_list, cache_life=0, fl_set_cache_date=False):
        try:
            if entity_id!="":
                attributes=dict()
                api=self.get_api(entity_id=entity_id)
                profile = api.GetProfile(fields=fields_list)
                attributes=profile.to_dict(fields_list)
                return attributes
                
            else:
               raise ApiError(None, 3920)
        except Exception, err:
           raise ApiError(None, 3101, err)

    def update_record(self, entity_id, attributes):
        try:
            if entity_id!="":
                api=self.get_api(entity_id=entity_id)
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    for key, value in attributes.items():
                        if key == "current-status":
                            api.ShareUpdate(value[:700])
                        elif key == "current-share":
                            if isinstance(value, dict):
                                api.ShareUpdate(**value)
                            elif isinstance(value, (str, unicode)):
                                api.ShareUpdate(value[:700])
            else:
               raise ApiError(None, 3900)
        except Exception, err:
            raise ApiError(None, 3101, err)
#=============================OAuth authentication

    def get_oauth_url(self, entity_id=None, params={}):
        next_url=params.get('next_url', settings.LINKEDIN_OAUTH_RETURN_URL)
        decode = params.get('decode', False)

        if decode:
            next_url=urllib.unquote(next_url)
        api = LinkedIn(settings.LINKEDIN_OAUTH_CONSUMER_KEY, 
                                settings.LINKEDIN_OAUTH_CONSUMER_SECRET, 
                                next_url)
        result = api.requestToken() # result can be True or False
        # if True, you can open your browser and copy the authorization url of LinkedIn.
        if result:
            try:
                query=None
                pickled = base64.encodestring(pickle.dumps(api))
                token = api.request_token
                self.transaction_start()
                try:
                    query=QUERY_CREATE_OAUTH_TABLE % (DM_DATABASE_NAME)
                    self.do_query(query)
                except Exception, err:
                    if not ("already exists" in ("%s" % err)):
                        Logger().error("Error: %s (%s) - %s" % (err, query, Exception))
                        raise Exception, err
                
                try:
                    query=QUERY_DELETE_OAUTH_RECORD % (DM_DATABASE_NAME,token, "linkedinConnector")
                    self.do_query(query)
                except Exception, err:
                    Logger().error("Error: %s (%s)" % (err, query))
                    raise Exception, err

                
                query=QUERY_ADD_OAUTH_RECORD % (DM_DATABASE_NAME,
                                          token,
                                          pickled, 
                                          str(datetime.datetime.now()), 
                                          "linkedinConnector")
                self.do_query(query)

                self.transaction_commit()
            except Exception, err:
                self.transaction_rollback()
                raise ApiError(None, 3102, "%s (%s): %s - [%s]" % (entity_id, err, query, Exception))
            
            _mode=params.get('mode', settings.LINKEDIN_OAUTH_MODE)
            if _mode=="authorize":
                return  api.getAuthorizeURL()# send the user to this url on his browser
            elif _mode=="authenticate":
                return  api.getAuthenticateURL()# send the user to this url on his browser
            else:
                raise ApiError(None, 3924, "%s" % _mode)
        else:
            raise ApiError(None, 3940, "%s" % api.getRequestTokenError())
 
    def oauth_validate_token(self, entity_id=None, params={}):
        api = LinkedIn(settings.LINKEDIN_OAUTH_CONSUMER_KEY, 
                                settings.LINKEDIN_OAUTH_CONSUMER_SECRET, 
                                params.get('next_url', settings.LINKEDIN_OAUTH_RETURN_URL))
        try:
            tokenized_url = params.get('tokenized_url')
            if tokenized_url and tokenized_url!="":
                decode = params.get('decode', False)
        
                if decode:
                    tokenized_url=urllib.unquote(tokenized_url)
                parsed=urlparse(tokenized_url)
                parsed_params=dict([item.split('=')[0], item.split('=')[1]] for item in parsed.query.split('&'))                
                oauth_token = urllib.unquote(parsed_params.get('oauth_token'))
                self.cursor.execute(QUERY_GET_OAUTH_RECORD % (DM_DATABASE_NAME, oauth_token, "linkedinConnector"))
    
                record=[dict(zip(['pickled'], row)) for row in self.cursor.fetchall()]
    
                api = pickle.loads(base64.decodestring(record[0].get('pickled')))
                                    
                oauth_verifier = str(parsed_params.get('oauth_verifier'))
                # After you get the verifier, you call the accessToken() method to get the access token.
                result = api.accessToken(verifier=oauth_verifier) # result can be True or False
                
                if result:
                    entity_type=self.object_name.split("_")[-1]
                    if entity_id is None:
                        profile_fields=["id", 
                           "first-name",
                           "last-name",
                           ]
                        profile = api.GetProfile(None, None, profile_fields)
                        attributes=profile.to_dict()
                        remote_id = "%s" % attributes['id']
                        entity_name="%s %s" % (attributes.get('first-name'), attributes.get('last-name'))
                        entity_slug=microtime_slug()
                        try:
                            my_entity=add_entity({"slug":entity_slug, 
                                                  "name":entity_name, 
                                                  "type":entity_type,
                                                  "remote_id":remote_id,
                                                  "attributes":{
                                                        "access_token_secret":api.access_token_secret,
                                                        "access_token": api.access_token
                                                        }
                                                  })
                            entity_id=my_entity.id
                        except Exception, err:
                            try:
                                my_entity=get_entity({"remote_id":remote_id, "type":entity_type})[0]
                                entity_id=my_entity.id
                                super(CustomConnector, self).update_record(entity_id, {
                                                        "access_token_secret":api.access_token_secret,
                                                        "access_token": api.access_token
                                                        })
                            except Exception, err:
                                raise ApiError(None, 3923, "%s - %s" % (Exception, err))
                    else:
                        my_entity=get_entity({"id":str(entity_id), "type":entity_type})[0]
                        super(CustomConnector, self).update_record(entity_id, 
                                                                    {"access_token_secret":api.access_token_secret,
                                                                     "access_token": api.access_token})
                    try:
                        query=QUERY_DELETE_OAUTH_RECORD % (DM_DATABASE_NAME,oauth_token, "linkedinConnector")
                        self.do_query(query)
                    except Exception, err:
                        Logger().error("Error: %s (%s)" % (err, query))
                        #raise Exception, err
                    
                else:
                    raise ApiError(api.getAccessTokenError(), 3943,  "%s" %  api.getAccessTokenError())
                
                return my_entity
            else:
                raise ApiError(None, 3942)
        except ApiError, err:
            raise Exception(err)
        except Exception, err:
            reauthenticate=self.get_oauth_url()
            raise ApiError(None, "%s" % reauthenticate, err)
