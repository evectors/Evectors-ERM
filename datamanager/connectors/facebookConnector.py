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

from erm.datamanager.connectors.simple import *
from erm.settings import *
from erm.lib.api import ApiError, ERROR_CODES
from django.utils.encoding import smart_str, smart_unicode

from erm.core.models import Entity

from erm.lib.logger import Logger

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

FB_FIELDS_MAP=dict()
FB_FIELDS_MAP["uid"] = "integer"
FB_FIELDS_MAP["first_name"] = "string"
FB_FIELDS_MAP["last_name"] = "string"
FB_FIELDS_MAP["name"] = "string"
FB_FIELDS_MAP["pic_small"] = "image"
FB_FIELDS_MAP["pic_big"] = "image"
FB_FIELDS_MAP["pic_square"] = "image"
FB_FIELDS_MAP["pic"] = "image"
FB_FIELDS_MAP["affiliations"] = "raw_text"
FB_FIELDS_MAP["profile_update_time"] = "datetime"
FB_FIELDS_MAP["timezone"] = "short_string"
FB_FIELDS_MAP["religion"] = "string"
FB_FIELDS_MAP["birthday"] = "string"
FB_FIELDS_MAP["birthday_date"] = "datetime"
FB_FIELDS_MAP["sex"] = "short_string"
FB_FIELDS_MAP["hometown_location"] = "raw_text"
FB_FIELDS_MAP["meeting_sex"] = "raw_text"
FB_FIELDS_MAP["meeting_for"] = "raw_text"
FB_FIELDS_MAP["relationship_status"] = "string"
FB_FIELDS_MAP["significant_other_id"] = "integer"
FB_FIELDS_MAP["political"] = "string"
FB_FIELDS_MAP["current_location"] = "raw_text"
FB_FIELDS_MAP["activities"] = "string"
FB_FIELDS_MAP["interests"] = "string"
FB_FIELDS_MAP["is_app_user"] = "boolean"
FB_FIELDS_MAP["music"] = "long_text"
FB_FIELDS_MAP["tv"] = "long_text"
FB_FIELDS_MAP["movies"] = "long_text"
FB_FIELDS_MAP["books"] = "long_text"
FB_FIELDS_MAP["quotes"] = "long_text"
FB_FIELDS_MAP["about_me"] = "long_text"
FB_FIELDS_MAP["hs_info"] = "raw_text"
FB_FIELDS_MAP["education_history"] = "raw_text"
FB_FIELDS_MAP["work_history"] = "raw_text"
FB_FIELDS_MAP["notes_count"] = "integer"
FB_FIELDS_MAP["wall_count"] = "integer"
FB_FIELDS_MAP["status"] = "string"
FB_FIELDS_MAP["online_presence"] = "string"
FB_FIELDS_MAP["locale"] = "string"
FB_FIELDS_MAP["proxied_email"] = "string"
FB_FIELDS_MAP["profile_url"] = "string"
FB_FIELDS_MAP["email_hashes"] = "raw_text"
FB_FIELDS_MAP["pic_small_with_logo"] = "image"
FB_FIELDS_MAP["pic_big_with_logo"] = "image"
FB_FIELDS_MAP["pic_square_with_logo"] = "image"
FB_FIELDS_MAP["pic_with_logo"] = "image"
FB_FIELDS_MAP["allowed_restrictions"] = "string"
FB_FIELDS_MAP["verified"] = "string"
FB_FIELDS_MAP["profile_blurb"] = "string"
FB_FIELDS_MAP["family"] = "raw_text"
FB_FIELDS_MAP["username"] = "string"
FB_FIELDS_MAP["website"] = "string"
FB_FIELDS_MAP["is_blocked"] = "boolean"

#FQL_GET_FRIENDS_DETAILS="SELECT first_name,last_name,uid,pic,is_app_user FROM user WHERE uid IN (SELECT uid2 FROM friend WHERE uid1=%s)"
#
#FB_SPECIAL_FIELDS=("friends", "friends_details", "permissions")

FB_MINIMAL_FIELDS=["affiliations", "first_name", "last_name", "name", "uid", "is_app_user"]

FB_NO_SESSION_FIELDS=["uid","first_name","last_name","name","locale","affiliations","pic_square","profile_url", "is_app_user"]

FB_PIC_FIELDS=["pic_big","pic_square","pic","pic_big_with_logo","pic_square_with_logo","pic_small_with_logo","pic_small"]

FB_RETURNED_FIELDS=FB_NO_SESSION_FIELDS

for item in FB_PIC_FIELDS:
    if not (item in FB_RETURNED_FIELDS):
        FB_RETURNED_FIELDS.append(item)
    
EXTENDED_PERMISSONS=("email","read_stream","publish_stream","offline_access","status_update","photo_upload","create_event","rsvp_event","sms","video_upload","create_note","share_item")
def json_decode(s):
    h,d,u=cjson.__version__.split(".")
    if (int(h)*100+int(d)*10+int(u))<=105:
        s=s.replace('\/', '/')
    return cjson.decode(s)

class CustomConnector(SimpleDbConnector):
    
    def __init__(self, object_name, fl_create_table=False, fields_desc=None):
        self.cache_life=0
        super(CustomConnector, self).__init__(object_name, fl_create_table=False, fields_desc=None)
        threshold=getattr(settings, "FB_CONNECTOR_LOG_THRESHOLD", getattr(settings, "LOG_THRESHOLD","NOTSET"))
        logfile=getattr(settings, "FB_CONNECTOR_LOG_FILENAME", getattr(settings, "LOG_FILE_NAME", "generic_log"))
        #self.logger.warning("%s - %s" % (threshold,logfile))
        self.logger=Logger(threshold, logfile, logger_name='facebookconnector')
        
    def do_query(self, query):
        try:
            self.cursor.execute(query)
            #self.connection.commit ()
        except Exception, err:
            if DEBUG_SQL:
                err = "%s (%s)" % (err, query)
            raise Exception(err)
    
    def get_default_attributes(self):
        return [{"slug":key, "kind":FB_FIELDS_MAP[key]} for key in FB_RETURNED_FIELDS]

    def session_key(self, entity=None, entity_id=None):
        key=None
        if not entity and entity_id:
            try:
                entity=Entity.objects.get(id=entity_id)
            except Exception, err:
                pass
        self.logger.warning("%s, %s, %s" % (entity.slug, entity.password, entity.custom_date))
        if entity and \
            entity.password and \
            ((not entity.custom_date) or time.mktime(entity.custom_date.timetuple())==0 or entity.custom_date>datetime.datetime.now()):
            key=entity.password
        return key
           
    def signature(self, args):
        parts = ["%s=%s" % (n, args[n]) for n in sorted(args.keys())]
        body = "".join(parts) + FACEBOOK_CONNECTOR_SECRET_KEY
        if isinstance(body, unicode): 
            body = body.encode("utf-8")
        return hashlib.md5(body).hexdigest()

    def create_table(self, fields):
        if not fields.has_key('cache_refresh_time'):
            fields['cache_refresh_time']={'slug':'cache_refresh_time', 'kind':'datetime'}
        super(CustomConnector, self).create_table(fields)
        
    def update_fields(self, fields):
        if not fields.has_key('cache_refresh_time'):
            fields['cache_refresh_time']={'slug':'cache_refresh_time', 'kind':'datetime'}
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
                    
    def fb_get(self, args, method, fl_decode=True):
        if not method.startswith("facebook."):
            method = "facebook." + method
        args["api_key"] = FACEBOOK_CONNECTOR_API_KEY
        args["v"] = "1.0"
        args["method"] = method
        args["call_id"] = str(long(time.time() * 1e6))
        args["format"] = "json"
        args["sig"] = self.signature(args)
        url = "http://api.facebook.com/restserver.php?" + \
            urllib.urlencode(args)
        self.logger.warning("url: %s" % url)
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        response_text=response.read()
        self.logger.warning("response: %s" % response_text)
        json_response=json_decode(response_text)

        fl_error=isinstance(json_response, dict) and json_response.has_key('error_code') and json_response.get('error_code')
        
        if not fl_error:
            if fl_decode:
                return json_response
            else:
                return response_text
        else:
            raise ApiError(json_response.get('error_msg'), 3101, json_response.get('error_code')) 
            
    def get_record(self, entity_id, fields_list, cache_life=0, fl_set_cache_date=False):
        try:
            if entity_id!="":
                if len(fields_list):
                    fl_cache=False
                    if cache_life>0:
                        self.cursor.execute(QUERY_GET_RECORD % ('cache_refresh_time', DM_DATABASE_NAME, self.object_name, "entity_id=%s" % entity_id))
                        fl_cache = self.cursor.fetchall()[0][0]+datetime.timedelta(seconds=cache_life)>datetime.datetime.now()
                    if not fl_cache:
                        _entity=Entity.objects.get(id=entity_id)
                        uid=_entity.slug
                        _session_key=self.session_key(_entity)
                        attributes=dict()
                        friends_att="friends" in fields_list
                        friends_details_att="friends_details" in fields_list
                        fb_attrs=list()
                        local_attrs=list()
                        
                        if _session_key:
                            accessible_fields=FB_FIELDS_MAP.keys()
                        else:
                            accessible_fields=FB_RETURNED_FIELDS
                        for key in fields_list:
                            if (key in accessible_fields):
                                fb_attrs.append(key)
                            else:
                                if (not FB_FIELDS_MAP.has_key(key)) and key!="cache_refresh_time":
                                    local_attrs.append(key)
                        
                        if len(fb_attrs):
                            args={"uids": uid, 'fields':",".join(fb_attrs)}
                            if _session_key:
                                args['session_key']=_session_key
                            response=self.fb_get(args, "users.getInfo")
                            for key, value in response[0].items():
                                attributes[key]=value
                            local_db_attrs=attributes
                            if len(fb_attrs)==len(FB_RETURNED_FIELDS) or fl_set_cache_date:
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

    def get_permissions(self, entity_id, params={"permissions_list":EXTENDED_PERMISSONS}):
        uid=Entity.objects.get(id=entity_id).slug
        permissions_list=params.get('permissions_list',EXTENDED_PERMISSONS)
        permissions=dict()
        for permission_key in permissions_list:
            args={"uid": uid, "ext_perm": permission_key}
            permissions[permission_key]=self.fb_get(args, "users.hasAppPermission")
        return permissions
    
    def get_friends(self, entity_id, params={"details":False, "fields":[]}):
        uid=Entity.objects.get(id=entity_id).slug
        args={"uid": uid}
        details=params.get('details',0)
        friends=self.fb_get(args, "friends.get", not details)
                        
        if details:
            fields=params.get('fields', FB_MINIMAL_FIELDS)
            if fields==[]:
                fields=FB_MINIMAL_FIELDS
            args={"uids": friends, "fields":",".join(fields)}
            friends=self.fb_get(args, "users.getInfo")
        return friends
        
    def execute(self, entity_id, params):
        method=params["method"]
        args=params.get("args", dict())
        if ((not args.has_key("uid")) or args["uid"]=="") or ((not args.has_key("session_key")) or args["session_key"]==""):
            _entity=Entity.objects.get(id=entity_id)
            if (not args.has_key("uid")) or args["uid"]=="":
                args["uid"]=_entity.slug
            if (not args.has_key("session_key")) or args["session_key"]=="":
                _session_key=self.session_key(_entity)
                if _session_key:
                    args["session_key"]=_session_key
                else:
                    if args.has_key("session_key"):
                        del args["session_key"]
        result= self.fb_get(args, method)
        return result
    
    def update_record(self, entity_id, attributes, query=QUERY_UPDATE_RECORD):
        try:
            if entity_id!="":
                uid=Entity.objects.get(id=entity_id).slug
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    set_list=list()
                    db_attributes=dict()
                    for key, value in attributes.items():
                        if key in FB_FIELDS_MAP.keys():
                            if key=="status":
                                if type(value) is dict:
                                    args={"uid": uid}
                                    for key,key_value in value.items():
                                        if type(key_value) is dict or type(key_value) is list:
                                            key_value=cjson.encode(key_value)
                                        args[key]=key_value
                                else:
                                    args={"uid": uid, "message":value}
                                result=self.fb_get(args, "stream.publish")
                        else:
                            if not FB_FIELDS_MAP.has_key(key):
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
