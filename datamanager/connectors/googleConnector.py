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

import gdata.gauth
import gdata.docs
import gdata.service
import gdata.docs.client
import gdata.docs.service
import gdata.youtube.service

import base64

from urlparse import urlparse

import pickle

INIT_STATEMENTS = ("SET NAMES UTF8", 
                   "SET AUTOCOMMIT = 0", 
                   "SET @innodb_lock_wait_timeout = 50")

#=====================generic or common errors=====================#
ERROR_CODES["3100"]="google connector: Missing database"
ERROR_CODES["3101"]="google connector: Generic error"
ERROR_CODES["3102"]="google connector: Database error"

#=====================create_table=====================#
ERROR_CODES["3200"]="google connector: Table exists" 
ERROR_CODES["3201"]="google connector: Table wasn't created" 
#=====================add_field=====================#
ERROR_CODES["3300"]="google connector: Field exists" 
ERROR_CODES["3301"]="google connector: Field wasn't created" 
#=====================set_field=====================#
ERROR_CODES["3400"]="google connector: Field missing" 
ERROR_CODES["3401"]="google connector: Field wasn't updated" 
#=====================delete_field=====================#
ERROR_CODES["3500"]="google connector: Field missing" 
ERROR_CODES["3501"]="google connector: Field wasn't deleted" 
#=====================init=====================#
ERROR_CODES["3600"]="google connector: Table exists" 

#=====================delete_table=====================#
ERROR_CODES["3700"]="google connector: Table missing" 
ERROR_CODES["3701"]="google connector: Table not deleted" 

#=====================add_record=====================#
ERROR_CODES["3800"]="google connector: Not null entity id is required" 
ERROR_CODES["3801"]="google connector: Entity record is already present" 
ERROR_CODES["3802"]="google connector: Entity record not created" 
ERROR_CODES["3803"]="google connector: Entity record add issue" 

#=====================update_record=====================#
ERROR_CODES["3900"]="google connector: Not null entity id is required" 
ERROR_CODES["3901"]="google connector: Entity record not found" 
ERROR_CODES["3902"]="google connector: Entity record update issue" 

#=====================delete_record=====================#
ERROR_CODES["3910"]="google connector: Not null entity id is required" 
ERROR_CODES["3911"]="google connector: Entity record not deleted" 

#=====================get_record=====================#
ERROR_CODES["3920"]="google connector: Not null entity id is required" 
ERROR_CODES["3921"]="google connector: Entity record missing" 
#=====================execute=====================#
ERROR_CODES["3930"]="google connector: execute error" 
#=====================oauth=====================#
ERROR_CODES["3940"]="google connector: callback_url is required" 
ERROR_CODES["3941"]="google connector: service not (yet) supported" 
ERROR_CODES["3942"]="google connector: the tokenized url is required" 
#=====================get file=====================#
ERROR_CODES["3950"]="google connector: unable to get a client" 
ERROR_CODES["3951"]="google connector: a resource_id is required" 


G_FIELDS_MAP=dict()

G_REMOTE_FIELDS_MAP=dict()
G_REMOTE_FIELDS_MAP['docs_list']='raw_text'
G_REMOTE_FIELDS_MAP['videos_list']='raw_text'

G_INNER_RECORDS=[{'slug':'services', 'kind':'raw_text'}]

G_INNER_FIELDS=[item['slug'] for item in G_INNER_RECORDS]

CONNECTOR_REMOTE_FIELDS=G_FIELDS_MAP.keys()

#=====================ancillar table sql queries for oauth
QUERY_CREATE_OAUTH_TABLE="""CREATE TABLE IF NOT EXISTS `%s`.`oauth_tokens` 
                     (`token` varchar(255) NOT NULL PRIMARY KEY, 
                      `pickled` blob,
                      `connector` varchar(255),
                      `created` datetime); """        
QUERY_ADD_OAUTH_RECORD="INSERT INTO `%s`.`oauth_tokens` (`token`,`pickled`, `created`, `connector`) VALUES ('%s', '%s', '%s', '%s')"
QUERY_GET_OAUTH_RECORD="SELECT `pickled` FROM `%s`.`oauth_tokens` WHERE `token`='%s' AND `connector`='%s'"
QUERY_DELETE_OAUTH_RECORD="DELETE FROM `%s`.`oauth_tokens` WHERE `token`='%s' AND `connector`='%s'"

services_data={
    'docs':{
        'scopes':['https://docs.google.com/feeds/', 
                  'http://docs.google.com/feeds/', 
                  'http://spreadsheets.google.com/feeds/', 
                  'https://spreadsheets.google.com/feeds']

        },
    'youtube':{
        'scopes':['http://gdata.youtube.com']

        },

    }
    

def json_decode(s):
    h,d,u=cjson.__version__.split(".")
    if (int(h)*100+int(d)*10+int(u))<=105:
        s=s.replace('\/', '/')
    return cjson.decode(s)

class CustomConnector(SimpleDbConnector):
    
    def __init__(self, object_name, fl_create_table=False, fields_desc=None):
        self.cache_life=0
        self.apis=dict()
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
        return [{"slug":key, "kind":value} for key,value in G_FIELDS_MAP.items()]

    def get_remote_attributes(self):
        return [{"slug":key, "kind":value} for key,value in G_REMOTE_FIELDS_MAP.items()]

    def merge_fields(self, fields):
        for _field in G_INNER_RECORDS:
            if not fields.has_key(_field['slug']):
                _complete_field=self.empty_field_descriptor
                _complete_field.update(_field)
                fields[_field['slug']]=_complete_field
        return fields
    
    def create_table(self, fields):
        super(CustomConnector, self).create_table(self.merge_fields(fields))
        
    def update_fields(self, fields):
        super(CustomConnector, self).update_fields(self.merge_fields(fields))
                            
#     @property
# refer to :
#  http://code.google.com/intl/it-IT/apis/documents/docs/3.0/developers_guide_protocol.html#ListFolderContents
#  http://code.google.com/intl/it-IT/apis/documents/docs/3.0/developers_guide_protocol.html#DownloadingDocsAndPresentations
    def docs_list(self, entity_id):
        client=self.get_api(entity_id=entity_id, service='docs')
        if client is not None:
            documents_feed = client.GetDocumentListFeed()
            documents_data=list()
            for entry in documents_feed.entry:
                is_author=True
                for author in entry.author:
                    is_author |= (author.email.text == self.entity_obj.name)
                if is_author:
                    documents_data.append({
                                        "title": entry.title.text,
                                        "published": entry.published.text,
                                        "updated": entry.updated.text,
                                        "authors": "%s" % list({"email":author.email.text, "name":author.name.text} for author in entry.author),
                                        "resourceId": entry.resourceId.text,
                                        "docType": entry.resourceId.text.split(":")[0],
                                        "content": entry.content.src,
                                        "links":list({"href":getattr(link,'href'), 
                                                      "rel":getattr(link,'rel'),
                                                      "type":getattr(link,'type')}
                                                      for link in entry.link)
                                        })
            return cjson.encode(documents_data)
            #return cjson.encode(list(item.title.text for item in documents_feed.entry))
        else:
            return "[]"
        
    def videos_list(self, entity_id):
        client=self.get_api(entity_id=entity_id, service='youtube')
        if client is not None:
            uri = 'http://gdata.youtube.com/feeds/api/users/default/uploads'
            videos_feed = client.GetYouTubeVideoFeed(uri)
            videos_data=list()
            for entry in videos_feed.entry:
                videos_data.append({
                                    "title": entry.title.text,
                                    "published": entry.published.text,
                                    'description': entry.media.description.text,
                                    'watch': entry.media.player.url,
                                    'seconds': entry.media.duration.seconds,
                                    'view_count': getattr(entry.statistics, 'view_count', 0),
                                    'thumbnails':list(thumbnail.url for thumbnail in entry.media.thumbnail),
                                    })
            return cjson.encode(videos_data)
        else:
            return "[]"
        
    def get_api(self, entity_obj=None, entity_id=None, service='docs'):
        if not entity_obj:
            entity_obj=Entity.objects.get(id=entity_id)
        self.entity_obj=entity_obj
        
        if not self.apis.has_key(service) or self.apis[service] is None:
            
            _api=None
            try:
                attributes = super(CustomConnector, self).get_record(entity_id, ["services"])
                credentials=attributes.get("services", "{}")
    
                if credentials is None or credentials=="":
                    credentials={}
                else:
                    credentials=json_decode(credentials)
    
                if credentials.has_key(service):
                    if credentials[service].has_key('oauth') and credentials[service]['oauth']!="":
                        if service == 'docs': 
                            _api=gdata.docs.service.DocsService(source='evectors-mirmex-v1')
                        elif service == 'youtube':
                            _api=gdata.youtube.service.YouTubeService()
                            _api.ssl = False
     
                        if _api is not None:
    
                            SIG_METHOD=gdata.auth.OAuthSignatureMethod.HMAC_SHA1
                            CONSUMER_KEY=credentials[service]['oauth']['consumer_key']
                            CONSUMER_SECRET= credentials[service]['oauth']['consumer_secret']
                            _api.SetOAuthInputParameters(SIG_METHOD, CONSUMER_KEY, consumer_secret=CONSUMER_SECRET)
                            
                            TOKEN=credentials[service]['oauth']['token_key']
                            TOKEN_SECRET=credentials[service]['oauth']['token_secret']
    
                            _api.SetOAuthInputParameters(SIG_METHOD, CONSUMER_KEY,consumer_secret=CONSUMER_SECRET) 
                            oauth_input_params = gdata.auth.OAuthInputParams(SIG_METHOD, CONSUMER_KEY, consumer_secret=CONSUMER_SECRET) 
                            oauth_token = gdata.auth.OAuthToken(key=TOKEN, secret=TOKEN_SECRET, oauth_input_params=oauth_input_params) 
                            _api.SetOAuthToken(oauth_token) 
    
                    elif credentials[service].has_key('authsub') and credentials[service]['authsub']!="":
                        if service == 'docs':
                            _api=gdata.docs.service.DocsService(source='evectors-mirmex-v1')
                        elif service == 'youtube':
                            _api=gdata.youtube.service.YouTubeService()
                            _api.ssl = False
                        if _api is not None:
                            _api.SetAuthSubToken(credentials[service]['authsub'])                
                
                if not _api:
                    if entity_obj.password is not None and entity_obj.password!="":
                        if service=='docs':
                            _api = gdata.docs.service.DocsService()
                            _api.ClientLogin(entity_obj.name, entity_obj.password)
                        elif service=='youtube':
                            _api = gdata.youtube.service.YouTubeService()
                            _api.email = entity_obj.name
                            _api.password = entity_obj.password
                            _api.source = 'evectors-mirmex-v1'
                            _api.ssl = False
                            _api.ProgrammaticLogin()
            except Exception, err:
                self.logger.error("Error getting API access to %s service (%s-%s)" % (service, Exception, err))
                _api=None
                
            self.apis[service]=_api
        return self.apis[service]

    def get_auth(self, callback_url=None):        
        client = gdata.docs.client.DocsClient(source='erm_connector')
        
        self.request_token = client.GetOAuthToken(
                                                GOOGLE_OAUTH_SCOPES, 
                                                callback_url, 
                                                GOOGLE_OAUTH_CONSUMER_KEY, 
                                                consumer_secret=GOOGLE_OAUTH_CONSUMER_SECRET)

        # gdata.gauth.AeSave(request_token, 'myKey')
        return self.request_token
        
    def get_record(self, entity_id, fields_list, cache_life=0, fl_set_cache_date=False):
        try:
            if entity_id!="":
                if len(fields_list):
                    attributes=dict()
                    hasAttrsDict=dict()
                    remote_attrs=list()
                    local_attrs=list()
                    
                    for key in fields_list:
                        hasAttrsDict[key]=hasattr(self, key)
                        if (key in CONNECTOR_REMOTE_FIELDS):
                            remote_attrs.append(key)
                        elif hasattr(self, key):
                            _attr=getattr(self, key)
                            if callable(_attr):
                                attributes[key]=_attr(entity_id)
                            else:
                                attributes[key]=_attr
                        elif key not in G_REMOTE_FIELDS_MAP.keys():
                            local_attrs.append(key)
                    
                    #attributes['check']=hasAttrsDict
                    
                    if len(remote_attrs):
                        api=self.get_api(entity_id=entity_id)
                        me=None
                        if api is not None:
                            me=api.me()
                        for key in remote_attrs:
                            if me:
                                if key!="status":
                                    attributes[key]=getattr(me,key)
                                else:
                                    attributes[key]=getattr(me,key).text
                            else:
                                attributes[key]=None
                                
                    if len(local_attrs):
                        for key, value in super(CustomConnector, self).get_record(entity_id, local_attrs).items():
                            attributes[key]=value

                    return attributes    
                else:
                    return {"fields":fields_list}
            else:
               raise ApiError(None, 3920)
        except Exception, err:
           raise ApiError(None, 3101, err)

#================================= AuthSub implementation

    def get_authsub_url(self, entity_id=None, params={'next_url':None, 'service':'docs'}):
        next_url = params.get('next_url')
        service = params.get('service', 'docs')
        source = params.get('source', 'evectors-ermconnector-v1')
        redirect_url=""
        decode = params.get('decode', False)
        if next_url and next_url!="":
            if service !="": #in ('docs', 'youtube'):
                gd_client = gdata.docs.service.DocsService(source=source)
                
                if decode:
                    next=urllib.unquote(next_url)
                else:
                    next=next_url
                
                scopes=list()
                for single_service in service.split(','):
                    scopes=scopes+services_data[single_service]['scopes']
                scopes = list(set(scopes))#services_data[service]['scopes']
                secure = False
                session = True
                redirect_url=gdata.service.GenerateAuthSubRequestUrl(next, scopes, secure=secure, session=session)
            else:
                raise ApiError(None, 3941)            
            return redirect_url
        else:
            raise ApiError(None, 3940)
    
    def upgrade_authsub_token(self, entity_id=None, params={'tokenized_url':None, 'service':'docs'}):
        tokenized_url = params.get('tokenized_url')
        service = params.get('service', 'docs')
        source = params.get('source', 'evectors-ermconnector-v1')
        store = (entity_id is not None) and params.get('store', True)
        decode = params.get('decode', False)

        if decode:
            tokenized_url=urllib.unquote(tokenized_url)
        parsed=urlparse(tokenized_url)
        parsed_params=dict([item.split('=')[0], item.split('=')[1]] for item in parsed.query.split('&'))                

        scopes=list(urllib.unquote(item) for item in parsed_params.get('authsub_token_scope',"+".join(services_data[service]['scopes'])).split('+'))
        
        services=list()
        for service_key, service_val in services_data.items():
            intersect=list(set(service_val["scopes"]).intersection(set(scopes)))
            intersect.sort()
            service_scopes=service_val["scopes"]
            service_scopes.sort()
            if intersect == service_scopes:
                services.append(service_key)

        if tokenized_url and tokenized_url!="":
            results=list()
            session_token=None
            for service in services:
                if service in ('docs', 'youtube'):
                    if session_token is None:
                        gd_client = gdata.docs.service.DocsService(source=source)
                        single_use_token = gdata.auth.extract_auth_sub_token_from_url(urllib.unquote(tokenized_url))
                        gd_client.UpgradeToSessionToken(single_use_token)
                        session_token=gd_client.GetAuthSubToken()
                    if store:
                        attributes = super(CustomConnector, self).get_record(entity_id, ["services"])
                        credentials=attributes.get("services", "{}")
                        if credentials is None or credentials=="":
                            credentials={}
                        else:
                            credentials=json_decode(credentials)
                            
                        if not credentials.has_key(service):
                            credentials[service]={}
                        credentials[service]['authsub']=session_token
                        super(CustomConnector, self).update_record(entity_id, {"services":cjson.encode(credentials)})
                        results.append(True)
                    else:
                        results.append(gd_client.GetAuthSubToken())
                else:
                    raise ApiError(None, 3941)            

        else:
            raise ApiError(None, 3942)
        return results
        
#=============================OAuth implementetation

    def get_oauth_url(self, entity_id=None, params={'service':'docs'}):
        next_url=params.get('next_url', None)
        decode = params.get('decode', False)
        domain =  params.get('domain', 'default')
        service = params.get('service', 'docs')
        consumer_key = params.get('consumer_key', GOOGLE_OAUTH_CONSUMER_KEY)
        consumer_secret = params.get('consumer_secret', GOOGLE_OAUTH_CONSUMER_SECRET)
        source = params.get('source', 'evectors-ermconnector-v1')

        if next_url and next_url!="":
            if service !="": #in ('docs', 'youtube'):
                if decode:
                    next=urllib.unquote(next_url)
                else:
                    next=next_url
                scopes=list()
                for single_service in service.split(','):
                    scopes=scopes+services_data[single_service]['scopes']
                scopes = list(set(scopes))#services_data[service]['scopes']
                
                client = gdata.docs.client.DocsClient(source=source)
                request_token = client.GetOAuthToken(scopes, 
                                                     next, 
                                                     consumer_key, 
                                                     consumer_secret=consumer_secret)

                redirect_url=request_token.generate_authorization_url(google_apps_domain=domain)
                
                try:
                    query=None
                    pickled=base64.encodestring(pickle.dumps({"token":request_token,
                                                              "next_url":next_url,
                                                              "consumer_key":consumer_key,
                                                              "consumer_secret":consumer_secret,
                                                              "service":service,
                                                              "source":source,
                                                              "scopes":scopes
                                                              }))
                    token=request_token.token
                    
                    self.transaction_start()
                    try:
                        query=QUERY_CREATE_OAUTH_TABLE % (DM_DATABASE_NAME)
                        self.do_query(query)
                    except Exception, err:
                        if not ("already exists" in ("%s" % err)):
                            Logger().error("Error: %s (%s) - %s" % (err, query, Exception))
                            raise Exception, err
                    
                    try:
                        query=QUERY_DELETE_OAUTH_RECORD % (DM_DATABASE_NAME,token, "googleConnector")
                        self.do_query(query)
                    except Exception, err:
                        Logger().error("Error: %s (%s)" % (err, query))
                        raise Exception, err
    
                    
                    query=QUERY_ADD_OAUTH_RECORD % (DM_DATABASE_NAME,
                                              token,
                                              pickled, 
                                              str(datetime.datetime.now()), 
                                              "googleConnector")
                    self.do_query(query)

                    self.transaction_commit()
                except Exception, err:
                    self.transaction_rollback()
                    raise ApiError(None, 3102, "%s (%s): %s - [%s]" % (entity_id, err, query, Exception))

                return str(redirect_url)
            else:
                raise ApiError(None, 3941)            
            
        else:
            raise ApiError(None, 3940)
 
    def oauth_validate_token(self, entity_id=None, params={}):
        pos=0
        try:
            tokenized_url = params.get('tokenized_url')
            if tokenized_url and tokenized_url!="":
                decode = params.get('decode', False)
        
                if decode:
                    tokenized_url=urllib.unquote(tokenized_url)
                parsed=urlparse(tokenized_url)
                parsed_params=dict([item.split('=')[0], item.split('=')[1]] for item in parsed.query.split('&'))                
                oauth_token = urllib.unquote(parsed_params.get('oauth_token'))
                self.cursor.execute(QUERY_GET_OAUTH_RECORD % (DM_DATABASE_NAME, oauth_token, "googleConnector"))
    
                record=[dict(zip(['pickled'], row)) for row in self.cursor.fetchall()]
    
                _pickled = pickle.loads(base64.decodestring(record[0].get('pickled')))
    
                next_url=_pickled['next_url']
                service = _pickled['service']
                consumer_key = _pickled['consumer_key']
                consumer_secret = _pickled['consumer_secret']
                source = _pickled['source']
                scopes = _pickled['scopes']
                saved_request_token = _pickled['token']
                
                self.logger.error(_pickled)
                
                self.request_token = gdata.gauth.AuthorizeRequestToken(saved_request_token, tokenized_url)
                
                client = gdata.docs.client.DocsClient(source=source)
                self.access_token = client.GetAccessToken(self.request_token)
                
    
                credentials_attributes={"token_key":self.access_token.token, 
                            "token_secret":self.access_token.token_secret,
                            "consumer_key":consumer_key,
                            'consumer_secret':consumer_secret,
                            'service':service
                            }
    
                services=list()
                for service_key, service_val in services_data.items():
                    intersect=list(set(service_val["scopes"]).intersection(set(scopes)))
                    intersect.sort()
                    service_scopes=service_val["scopes"]
                    service_scopes.sort()
                    if intersect == service_scopes:
                        services.append(service_key)
        
                for service in services:
                    if service in ('docs', 'youtube'):
                        attributes = super(CustomConnector, self).get_record(entity_id, ["services"])
                        credentials=attributes.get("services", "{}")
                        if credentials is None or credentials=="":
                            credentials={}
                        else:
                            credentials=json_decode(credentials)
                            
                        if not credentials.has_key(service):
                            credentials[service]={}
                        credentials[service]['oauth']=credentials_attributes
                        super(CustomConnector, self).update_record(entity_id, {"services":cjson.encode(credentials)})
                    else:
                        raise ApiError(None, 3941)            
    
    
    
    
                entity_type=self.object_name.split("_")[-1]
                my_entity=get_entity({"slug":str(entity_id), "type":entity_type})
                return my_entity
            else:
                raise ApiError(None, 3942)
        except Exception, err:
            err="%s - %s" % (pos, err)
            raise ApiError(None, 3100, err)
    
    def get_file(self, entity_id, params):
        try:
            resource_id = params.get('resource_id', None)
            if resource_id is not None:
                doc_services_map={"spreadsheet":"wise",
                                  "document": None}
                client = gdata.docs.service.DocsService()
                entity_obj=Entity.objects.get(id=entity_id)
                doc_type, doc_key = resource_id.split(':')
            
                client.ClientLogin(entity_obj.name, entity_obj.password, service=doc_services_map[doc_type])
                if client is not None:
                
                    file_name = params.get('file', 'file_%s.pdf' % int(time.time()))
                    fl_return_data = bool(int(params.get('get_data', 0)))
                    return_data_limit = int(params.get('get_data_limit', 1024*1024*10))
                    file_path=os.path.join(PICKLER_DIR, file_name)
                    client.Export(resource_id, os.path.join(PICKLER_DIR, file_path))
                    file_size=os.path.getsize(file_path)
                    file_data=""
                    file_encoding=""
                    file_storage=""
                    if fl_return_data and file_size<return_data_limit:
                        file_data = base64.encodestring( open(file_path).read() )
                        file_encoding="base64"
                        os.unlink(file_path)
                        file_path=""
                    documents_data = {"file_name": file_name,
                                      "file_path":file_path,
                                      "file_size": file_size,
                                      "file_encoding": file_encoding,
                                      "file_storage":file_storage,
                                      "file_data": file_data,
                                     }
                    return cjson.encode(documents_data)
                else:
                   raise ApiError(None, 3950)
            else:
                raise ApiError(None, 3951)
        except Exception, err:
            raise ApiError(None, 3101, "\n\nerr: %s \n\nentity_id: %s \n\n" % (err, entity_id))
#     def execute(self, entity_id, params):
#         result=None
#         method=params["method"]
#         args=params["args"]
#         api=self.get_api(entity_id=entity_id)
#         if hasattr(api, method):
#             method_funct=getattr(api, method)
#             if len(args)>0:
#                 if "null" in args.keys():
#                     if len(args)==1:
#                         result=method_funct(args.values()[0])
#                     else:
#                         named_args=dict()
#                         unnamed_arg=""
#                         for _key, _value in args.items():
#                             if _key != "null":
#                                 named_args[str(_key)]=_value 
#                             else:   
#                                 unnamed_arg=_value
#                         result=method_funct(unnamed_arg, *named_args)
#                 else:
#                     result=method_funct(*args)
#             else:
#                 result=method_funct()
#             
#             return self.normalize(result)
#             
#         else:
#             raise ApiError(None, 3930, "method %s doesn't exist" % method)
#         return result
#     
#     def obj_to_dict(self, obj):
#         _dict=dict()
#         for _key in dir(obj):
#             if not inspect.ismethod(getattr(obj, _key)) and _key!="_api" and _key[0]!="_" and not ("__" in _key):
#                 _dict[_key]=self.normalize(getattr(obj, _key))
#         return _dict
#     
#     def is_tweepy_obj(self, obj):
#         for _key, _value in inspect.getmembers(tweepy.models, inspect.isclass):
#             if isinstance(obj, _value):
#                 return True
#         return False
#     
#     def normalize(self, obj):
#         _normalized=None
#         try:
#             if isinstance(obj, list):
#                 _list=list()
#                 for _item in obj:
#                     _list.append(self.normalize(_item))
#                 _normalized=_list
#             elif isinstance(obj, dict):
#                 _dict=dict()
#                 for _key, _value in obj.items():
#                     if _key!="_api":
#                         _dict[_key]=self.normalize(_value)
#                 _normalized=_dict
#             elif self.is_tweepy_obj(obj):
#                 _normalized=self.obj_to_dict(obj)
#             else:
#                 _normalized=obj
#         except Exception, err:
#             return "%s: %s" % (Exception, err)
# 
#         return _normalized
#         
#     def update_status(self, entity_id, params):
#         _status=list()
#         try:
#             if entity_id!="":
#                 api=self.get_api(entity_id=entity_id)
#                 if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_OAUTH_RECORD:
#                     _params_list=dict()
#                     for _key in ("status", "in_reply_to_status_id","lat", "long", "source"):
#                         _params_list[_key]=params.get(_key)
#                     if _params_list.get('status'):
#                         if _params_list.get('in_reply_to_status_id'):
#                             if _params_list.get('lat') and _params_list.get('long'):
#                                 _status=api.update_status(_params_list.get('status')[:140], _params_list.get('in_reply_to_status_id'), _params_list.get('lat'), _params_list.get('long'))
#                         else:
#                             if _params_list.get('lat') and _params_list.get('long'):
#                                 _status=api.update_status(_params_list.get('status')[:140], _params_list.get('lat'), _params_list.get('long'))
#                             else:
#                                 _status=api.update_status(_params_list.get('status')[:140])
#                     else:
#                         raise ApiError(None, 3900, "status is required (%s)" % params)
#                 else:
#                    self.add_record(entity_id, attributes)
#                     #raise ApiError(None, 3901, entity_id)
#             else:
#                raise ApiError(None, 3900)
#         except Exception, err:
#             raise ApiError(None, 3101, err)
#         
#                 
#         return self.normalize(_status)
#         
#     def update_record(self, entity_id, attributes, query=QUERY_UPDATE_RECORD):
#         try:
#             if entity_id!="":
#                 api=None
#                 if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_OAUTH_RECORD:
#                     set_list=list()
#                     db_attributes=dict()
#                     for key, value in attributes.items():
#                         if key in CONNECTOR_REMOTE_FIELDS:
#                             if api is None:
#                                 api=self.get_api(entity_id=entity_id)
#                             if key=="status":
#                                 api.update_status(value[:140])
#                         else:
#                             db_attributes[key]=value
#                     if len(db_attributes):
#                         super(CustomConnector, self).update_record(entity_id, db_attributes, query)
#                 else:
#                    self.add_record(entity_id, attributes)
#                     #raise ApiError(None, 3901, entity_id)
#             else:
#                raise ApiError(None, 3900)
#         except Exception, err:
#             raise ApiError(None, 3101, err)
