import httplib
import urllib

import cjson

import os
import sys

_erm_path=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_lib_path=os.path.join(_erm_path, "lib")
sys.path.insert(0, _lib_path)
sys.path.insert(0, "/var/www")

from erm.datamanager.connectors.simple import *
from erm.settings import *
from erm.lib.logger import Logger

#=============================Web Flow Implementation

class Oauth2WebFlow (object):
    
    def __init__(self, api_endpoint, api_key, api_secret, redirect_uri, 
                 authorize_url= "/oauth/authorize",
                 access_token_url = "/oauth/access_token",
                 uri_scheme= "https"):
        self.URI_SCHEME        = uri_scheme
        self.API_ENDPOINT      = api_endpoint
        self.AUTHORIZE_URL     = authorize_url
        self.ACCESS_TOKEN_URL  = access_token_url
        self.BASE_URL          = "%s://%s" % (self.URI_SCHEME, self.API_ENDPOINT)
        
        self.API_KEY       = api_key
        self.API_SECRET    = api_secret
        self.REDIRECT_URI  = redirect_uri
        self.request_token = None # that comes later
        self.access_token  = None # that comes later and later
        
        self.request_token_secret = None
        self.access_token_secret  = None
                
    def getAuthorizeURL(self, scope=""):
        _url= "%s://%s%s?client_id=%s&redirect_uri=%s" % (self.URI_SCHEME, 
                                                           self.API_ENDPOINT, 
                                                           self.AUTHORIZE_URL, 
                                                           self.API_KEY, 
                                                           urllib.quote_plus(self.REDIRECT_URI))
        if scope!="":
            _url = "%s&scope=%s" % (_url, scope)
        return _url
    
    def getAccessToken(self, code):
#         _url= "%s?type=web_server&client_id=%s&redirect_uri=%s&client_secret=%s&code=%s" % ( 
#                                                            self.ACCESS_TOKEN_URL, 
#                                                            self.API_KEY, 
#                                                            self.REDIRECT_URI,
#                                                            self.API_SECRET,
#                                                            code)
#         #
#         connection = httplib.HTTPSConnection(self.API_ENDPOINT)
#         connection.request('GET', _url)
#         response = connection.getresponse()
#         if response is None:
#             self.request_oauth_error = "No HTTP response received."
#             connection.close()
#             return False
# 
#         response = response.read()
#         connection.close()
#                 if response is None:
#             self.request_oauth_error = "No HTTP response received."

                
        args = dict()
#         args["type"]="client_cred"
        args["client_id"]=self.API_KEY
        args["redirect_uri"]=self.REDIRECT_URI#urllib.quote_plus(self.REDIRECT_URI)
        args["client_secret"] = self.API_SECRET
        args["code"] = code
        response = urllib.urlopen(
                "https://graph.facebook.com/oauth/access_token?" +
                urllib.urlencode(args)).read()        

        oauth_problem = response.find('"error":')>-1
        if oauth_problem:
            _json=cjson.decode(response)
            raise Exception("%s: %s" % (_json['error']['type'], _json['error']['message']))
        else:
            return response.split('=')[1]
# 

#=============================Client Credentials' Implementation

'''The following class is simply a clone of web flow, not sure wether it's correct...'''

class Oauth2ClientCredentials (object):
    
    def __init__(self, api_endpoint, api_key, api_secret, redirect_uri, 
                 authorize_url= "/oauth/authorize",
                 access_token_url = "/oauth/access_token",
                 uri_scheme= "https"):
        self.URI_SCHEME        = uri_scheme
        self.API_ENDPOINT      = api_endpoint
        self.AUTHORIZE_URL     = authorize_url
        self.ACCESS_TOKEN_URL  = access_token_url
        self.BASE_URL          = "%s://%s" % (self.URI_SCHEME, self.API_ENDPOINT)
        
        self.API_KEY       = api_key
        self.API_SECRET    = api_secret
        self.REDIRECT_URI  = redirect_uri
        self.request_token = None # that comes later
        self.access_token  = None # that comes later and later
        
        self.request_token_secret = None
        self.access_token_secret  = None
                
    def getAuthorizeURL(self, scope=""):
        _url= "%s://%s%s?client_id=%s&redirect_uri=%s" % (self.URI_SCHEME, 
                                                           self.API_ENDPOINT, 
                                                           self.AUTHORIZE_URL, 
                                                           self.API_KEY, 
                                                           self.REDIRECT_URI)
        if scope!="":
            _url = "%s&scope=%s" % (_url, scope)
        return _url
    
    def getAccessToken(self, code):
        _url= "%s?type=client_cred&client_id=%s&redirect_uri=%s&client_secret=%s&code=%s" % ( 
                                                           self.ACCESS_TOKEN_URL, 
                                                           self.API_KEY, 
                                                           self.REDIRECT_URI,
                                                           self.API_SECRET,
                                                           code)
        #
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request('GET', _url)
        response = connection.getresponse()
        if response is None:
            self.request_oauth_error = "No HTTP response received."
            connection.close()
            return False

        response = response.read()
        connection.close()
                
        oauth_problem = response.find('"error":')>-1
        if oauth_problem:
            _json=cjson.decode(response)
            raise Exception("%s: %s" % (_json['error']['type'], _json['error']['message']))
        else:
            return response.split('=')[1]

#         
# api_endpoint='graph.facebook.com'
# api_key = '174404302575613'
# api_secret = '049c917813fc7d074c5eb992e75a053d'
# redirect_uri = 'http://www.evectors.com&scope=publish_stream,offline_access'
# 
# client=Oauth2ClientCredentials(api_endpoint, api_key, api_secret, redirect_uri)
# print client.getAuthorizeURL()
# token=client.getAccessToken('dasdadwq')
# print "\n\n%s" % token