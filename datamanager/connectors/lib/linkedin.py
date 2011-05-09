# -*- coding: utf-8 -*-

#######################################################################################
# Python implementation of LinkedIn OAuth Authorization, Profile and Connection APIs. #
#                                                                                     #
# Derived from library by: Ozgur Vatansever                                           #
# Email : ozgurvt@gmail.com                                                           #
# LinkedIn Account: http://www.linkedin.com/in/ozgurvt                                #
#                                                                                     #
# Extended by Simone Bettini (simone@evectors.com)                                    #
#######################################################################################

"""
Provides a Pure Python LinkedIn API Interface.
"""
try:
    import sha
except DeprecationWarning, derr:
    import hashlib
    sha = hashlib.sha1

import urllib, urllib2, time, random, httplib, hmac, hashlib, binascii, cgi, string, datetime

import calendar

from HTMLParser import HTMLParser

from xml.dom import minidom
from urlparse import urlparse
from xml.sax.saxutils import unescape

from lib.logger import Logger

ALL_PROFILE_FIELDS=[
    "id",
    "first-name",
    "last-name",
    "headline",
    "location",
    "industry",
    "distance",
    "relation-to-viewer",
    "current-status",
    "current-status-timestamp",
    "current-share",
    "connections",
    "num-connections",
    "num-connections-capped",
    "summary",
    "specialties",
    "proposal-comments",
    "associations",
    "honors",
    "interests",
    "positions",
    "educations",
    "three-current-positions",
    "three-past-positions",
    "num-recommenders",
    "recommendations-received",
    "phone-numbers",
    "im-accounts",
    "twitter-accounts",
    "date-of-birth",
    "main-address",
     "picture-url",
     "site-standard-profile-request",
     "api-standard-profile-request",
     "public-profile-url"
    ]

ALL_EDUCATION_FIELDS = ["id",
    "school_name", 
    "start-date", 
    "degree",
    "start-date",
    "end-date"]

ALL_POSITION_FIELDS = ["id",
    "title", 
    "summary", 
    "is-current",
    "start-date",
    "end-date",
    "company"]

ALL_COMPANY_FIELDS = ["name",
    "type", 
    "size", 
    "industry",
    "ticker"]

class OAuthError(Exception):
    """
    General OAuth exception, nothing special.
    """
    def __init__(self, value):
        self.parameter = value
        
    def __str__(self):
        return repr(self.parameter)


class Stripper(HTMLParser):
    """
    Stripper class that strips HTML entity.
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)
    
    def getAlteredData(self):
        return ''.join(self.fed)


class XMLBuilder(object):
    def __init__(self, rootTagName):
        self.document = minidom.Document()
        self.root = self.document.createElement(rootTagName)
        self.document.appendChild(self.root)

    def xml(self):
        return self.document.toxml()

    def __unicode__(self):
        return self.document.toprettyxml()

    def append_element_to_root(self, element):
        self.root.appendChild(element)

    def append_list_of_elements_to_element(self, element, elements):
        map(lambda x:element.appendChild(x),elements)
        return element

    def create_element(self, tag_name):
        return self.document.createElement(str(tag_name))

    def create_element_with_text_node(self, tag_name, text_node):
        text_node = self.document.createTextNode(str(text_node))
        element = self.document.createElement(str(tag_name))
        element.appendChild(text_node)
        return element

    def create_elements(self, **elements):
        return [self.create_element_with_text_node(tag_name, text_node) for tag_name, text_node in elements.items()]
        
class XmlObject (object):
    def _get_child_node(self, node, tagName):
        for child in node.childNodes:
            if getattr(child, 'tagName', None) == tagName:
                return child
        return None

    def _get_child(self, node, tagName, default=None):
        child=self._get_child_node(node, tagName)
        value = default
        if child:
            childNodes = child.childNodes
            if childNodes:
                return childNodes[0].nodeValue
        return value

    def _get_child_date(self, node, tagName):
        value = None
        child=self._get_child_node(node, tagName)
        if child is not None:
            try:
                year = self._get_child(child, "year")
                month = self._get_child(child, "month")
                day = self._get_child(child, "day")
                if year is not None:
                    value="%s" % year
                    if month is not None:
                        value="%s-%s" % (value, month)
                        if day is not None:
                            value="%s-%s" % (value, day)
            except Exception, err:
                Logger().error("XmlObject._get_child_date error: %s - %s" % (Exception, err))
        return value

class Education(XmlObject):
    """
    Class that wraps an education info of a user
    """
    def __init__(self):
        for _field in ALL_EDUCATION_FIELDS:
            setattr(self, _field, None)
        
    @staticmethod
    def create(node):
        """
        <educations total="">
         <education>
          <id>
          <school-name>
          <degree>
          <start-date>
           <year>
          </start-date>
          <end-date>
           <year>
          </end-date>
         </education>
        </educations>
        """
        children = node.getElementsByTagName("education")
        result = []
        for child in children:
            education = Education()
            education.id = education._get_child(child, "id")
            education.activities = education._get_child(child, "activities")
            education.notes = education._get_child(child, "notes")
            education.school_name = education._get_child(child, "school-name")
            education.degree = education._get_child(child, "degree")
            setattr(education, 'start-date', education._get_child_date(child, "start-date"))
            setattr(education, 'end-date', education._get_child_date(child, "end-date"))
            result.append(education)            
        return result

    def to_dict(self):
        result=dict()
        for _field in ALL_EDUCATION_FIELDS:
            result[_field]=getattr(self, _field, None)
        return result
        
class Company(XmlObject):
    """
    Class that wraps an education info of a user
    """
    def __init__(self):
        for _field in ALL_COMPANY_FIELDS:
            setattr(self, _field, None)
        
    @staticmethod
    def create(node):
        if node is not None:
            company = Company()
            for _field in ALL_COMPANY_FIELDS:
                setattr(company, _field, company._get_child(node, _field))
            return company
        else:
            return None
            
    def to_dict(self):
        result=dict()
        for _field in ALL_COMPANY_FIELDS:
            result[_field]=getattr(self, _field, None)
        return result
        
class Position(XmlObject):
    """
    Class that wraps a business position info of a user
    """
    def __init__(self):
        for _field in ALL_POSITION_FIELDS:
            setattr(self, _field, None)
        
    @staticmethod
    def get_list(node):
        """
        <positions total='1'>
         <position>
          <id>101526695</id>
          <title>Developer</title>
          <summary></summary>
          <start-date>
          <year>2009</year>
          <month>9</month>
          </start-date>
          <is-current>true</is-current>
          <company>
          <name>Akinon</name>
          </company>
         </position>
        </positions>
        """
        children = node.getElementsByTagName("position")
        result = []
        for child in children:
            position = Position()
            position.id = position._get_child(child, "id")
            position.title = position._get_child(child, "title")
            position.summary = position._get_child(child, "summary")
            try:
                position.company = Company.create(position._get_child_node(child, "company"))
            except Exception,err:
                Logger().error("Company.create error: %s - %s" % (Exception,err))
            
            setattr(position, 'start-date', position._get_child_date(child, "start-date"))
            setattr(position, 'end-date', position._get_child_date(child, "end-date"))
            result.append(position)

        return result
            
    def to_dict(self):
        result=dict()
        for _field in ALL_POSITION_FIELDS:
            _value=getattr(self, _field, None)
            if _field!="company":
                result[_field]=_value
            elif _value is not None:
                result[_field]=_value.to_dict()
            else:
                result[_field]=None
        return result
                
class Profile(XmlObject):
    """
    Wraps the data which comes from Profile API of LinkedIn.
    For further information, take a look at LinkedIn Profile API.
    """
    def __init__(self, xml_string=None, fields=dict()):
        
        self.PROFILE_SCALAR_FIELDS=[
                                    "public-profile-url",
                                    "num-recommenders",
                                    "picture-url",
                                    "id",
                                    "headline",
                                    "num-connections",
                                    "current-status-timestamp",
                                    "num-connections-capped",
                                    "first-name",
                                    "current-status",
                                    "distance",
                                    "last-name",
                                    "industry",
                                    "summary",
                                    "specialties",
                                    ]

        self.SIMPLY_NESTED_FIELDS={
                                    "location":"name",
                                    "public_profile":"url",
                                    "site-standard-profile-request":"url",
                                    "current-share":"comment"
                                    }

        self.DATE_FIELDS=[
                            "date-of-birth"
                         ]


        if xml_string is not None:
            self.parse(xml_string, fields)

    def parse(self, xml_string, fields=list()):
#        Logger().error(xml_string)
        try:
            document = minidom.parseString(xml_string)
            person_dom = self._get_child_node(document,"person") #document.getElementsByTagName("person")[0]
            self.extract(person_dom, fields)
        except Exception, err:
            self.error=err
            Logger().error("parse error: %s" % err)
            
    def extract(self, person, fields=list()):
        for field in fields:
            if field in self.PROFILE_SCALAR_FIELDS:
                setattr(self, field, self._get_child(person, field))
            if field in self.DATE_FIELDS:
                setattr(self, field, self._get_child_date(person, field))
            elif field in self.SIMPLY_NESTED_FIELDS.keys():
                node = self._get_child_node(person, field)
                if node:
#                     node = node[0]
                    setattr(self, field, self._get_child(node, self.SIMPLY_NESTED_FIELDS[field]))
            elif field == "positions":
                positions = self._get_child_node(person, "positions")
                if positions:
                    self.positions = Position.get_list(positions)
            elif field == "educations":
                # create educations
                educations = self._get_child_node(person, "educations")
                if educations:
                    self.educations = Education.create(educations)
            elif field=='connections':
                connections_array = person.getElementsByTagName("connections")
                connections_array = connections_array[0]
                persons = connections_array.getElementsByTagName("person")
                connections_list = []
                profile_fields=["id", 
                   "first-name",
                   "last-name",
                   "headline",
                   "location",
                   "industry",
                   "site-standard-profile-request",
                   ]
                for connection in persons:
                    connection_profile = Profile()
                    connection_profile.extract(connection, profile_fields)
                    connections_list.append(connection_profile.to_dict(profile_fields))
                self.connections=connections_list
                
            
    def to_dict(self, fields=list()):
        if len(fields)==0:
            fields = ALL_PROFILE_FIELDS
        result=dict()
        for field in fields:
            _value=getattr(self, field, None)
            try:
                if isinstance(_value, list):
                    _value_list=list()
                    for _item in _value:
                        try:
                            _value_list.append(_item.to_dict())
                        except Exception, err:
                            _value_list.append(_item)
                    result[field]=_value_list
                else:
                    result[field]=_value.to_dict()
            except Exception, err:
                result[field]=_value
        return result
        
    def _unescape(self, url):
        if url:
            return unescape(url)
        return url


class LinkedIn(object):
    def __init__(self, api_key, api_secret, callback_url):
        """
        LinkedIn Base class that simply implements LinkedIn OAuth Authorization and LinkedIn APIs such as Profile, Connection vs.

        @ LinkedIn OAuth Authorization
        ------------------------------
        In OAuth terminology, there are 2 tokens that we need in order to have permission to perform an API request.
        Those are requestToken and accessToken. Thus, this class basicly intends to wrap methods of OAuth spec. which
        are related of gettting requestToken and accessToken strings.

        @ Important Note:
        -----------------
        HMAC-SHA1 hashing algorithm will be used while encrypting a request body of an HTTP request. Other alternatives
        such as 'SHA-1' or 'PLAINTEXT' are ignored.

        @Reference for OAuth
        --------------------
        Please take a look at the link below if you have a basic knowledge of HTTP protocol
        - http://developer.linkedin.com/docs/DOC-1008

        
        Please create an application from the link below if you do not have an API key and secret key yet.
        - https://www.linkedin.com/secure/developer
        @api_key:    Your API key
        @api_secret: Your API secret key
        @callback_url: the return url when the user grants permission to Consumer.
        """
        # Credientials
        self.URI_SCHEME        = "https"
        self.API_ENDPOINT      = "api.linkedin.com"
        self.REQUEST_TOKEN_URL = "/uas/oauth/requestToken"
        self.ACCESS_TOKEN_URL  = "/uas/oauth/accessToken"
        self.AUTHORIZE_REDIRECT_URL      = "/uas/oauth/authorize"
        self.AUTHENTICATE_REDIRECT_URL      = "/uas/oauth/authenticate"
        self.version           = "1.0"
        self.signature_method  = "HMAC-SHA1" # as I said
        self.BASE_URL          = "%s://%s" % (self.URI_SCHEME, self.API_ENDPOINT)
        
        self.API_KEY       = api_key
        self.API_SECRET    = api_secret
        self.CALLBACK_URL  = callback_url
        self.request_token = None # that comes later
        self.access_token  = None # that comes later and later
        
        self.request_token_secret = None
        self.access_token_secret  = None
        
        self.verifier = None
        self.error    = None

        self.request_oauth_nonce     = None
        self.request_oauth_timestamp = None
        self.access_oauth_nonce      = None
        self.access_oauth_timestamp  = None
        self.request_oauth_error     = None
        self.access_oauth_error      = None
        
    def getRequestTokenURL(self):
        return "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, self.REQUEST_TOKEN_URL)

    def getAccessTokenURL(self):
        return "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, self.ACCESS_TOKEN_URL)

    def getAuthorizeURL(self, request_token = None):
        self.request_token = request_token and request_token or self.request_token
        if self.request_token is None:
            raise OAuthError("OAuth Request Token is NULL. Plase acquire this first.")
        return "%s%s?oauth_token=%s" % (self.BASE_URL, self.AUTHORIZE_REDIRECT_URL, self.request_token) 
    
    def getAuthenticateURL(self, request_token = None):
        self.request_token = request_token and request_token or self.request_token
        if self.request_token is None:
            raise OAuthError("OAuth Request Token is NULL. Plase acquire this first.")
        return "%s%s?oauth_token=%s" % (self.BASE_URL, self.AUTHENTICATE_REDIRECT_URL, self.request_token) 
    
    #################################################
    # HELPER FUNCTIONS                              #
    # You do not explicitly use those methods below #
    #################################################
    def _generate_nonce(self, length = 20):
        return ''.join([string.letters[random.randint(0, len(string.letters) - 1)] for i in range(length)])

    def _generate_timestamp(self):
        return int(time.time())
    
    def _quote(self, st):
        return urllib.quote(st, safe='~')

    def _utf8(self, st):
        return st.encode("utf-8") if isinstance(st, unicode) else str(st)

    def _urlencode(self, query_dict):
        keys_and_values = [(self._quote(self._utf8(k)), self._quote(self._utf8(v))) for k,v in query_dict.items()]
        keys_and_values.sort()
        return '&'.join(['%s=%s' % (k, v) for k, v in keys_and_values])

    def _get_value_from_raw_qs(self, key, qs):
        raw_qs = cgi.parse_qs(qs, keep_blank_values = False)
        rs = raw_qs.get(key)
        if type(rs) == list:
            return rs[0]
        else:
            return rs

    def _signature_base_string(self, method, uri, query_dict):
        return "&".join([self._quote(method), self._quote(uri), self._quote(self._urlencode(query_dict))])
        
    def _parse_error(self, str_as_xml):
        """
        Helper function in order to get error message from an xml string.
        In coming xml can be like this:
        <?xml version='1.0' encoding='UTF-8' standalone='yes'?>
        <error>
         <status>404</status>
         <timestamp>1262186271064</timestamp>
         <error-code>0000</error-code>
         <message>[invalid.property.name]. Couldn't find property with name: first_name</message>
        </error>
        """
        try:
            xmlDocument = minidom.parseString(str_as_xml)
            if len(xmlDocument.getElementsByTagName("error")) > 0: 
                error = xmlDocument.getElementsByTagName("message")
                if error:
                    error = error[0]
                    return error.childNodes[0].nodeValue
            return None
        except Exception, detail:
            raise OAuthError("Invalid XML String given: error: %s" % repr(detail))
        
    ########################
    # END HELPER FUNCTIONS #
    ########################

    def requestToken(self):
        """
        Performs the corresponding API which returns the request token in a query string
        The POST Querydict must include the following:
         * oauth_callback
         * oauth_consumer_key
         * oauth_nonce
         * oauth_signature_method
         * oauth_timestamp
         * oauth_version
        """
        #################
        # BEGIN ROUTINE #
        #################
        # clear everything
        self.clear()
        # initialization
        self.request_oauth_nonce = self._generate_nonce()
        self.request_oauth_timestamp = self._generate_timestamp()
        # create Signature Base String
        method = "POST"
        url = self.getRequestTokenURL()
        query_dict = {"oauth_callback": self.CALLBACK_URL,
                      "oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": self.request_oauth_nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": self.request_oauth_timestamp,
                      "oauth_version": self.version,
                      }
        query_string = self._quote(self._urlencode(query_dict))
        signature_base_string = "&".join([self._quote(method), self._quote(url), query_string])
        # create actual signature
        hashed = hmac.new(self._quote(self.API_SECRET) + "&", signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]
        # it is time to create the heaader of the http request that will be sent
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_callback="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (self.request_oauth_nonce, self._quote(self.CALLBACK_URL),
                           self.signature_method, self.request_oauth_timestamp,
                           self._quote(self.API_KEY), self._quote(signature), self.version)

        
        # next step is to establish an HTTPS connection through the LinkedIn API
        # and fetch the request token.
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, self.REQUEST_TOKEN_URL, body = self._urlencode(query_dict), headers = {'Authorization': header})
        response = connection.getresponse()
        if response is None:
            self.request_oauth_error = "No HTTP response received."
            connection.close()
            return False

        response = response.read()
        connection.close()
        
        oauth_problem = self._get_value_from_raw_qs("oauth_problem", response)
        if oauth_problem:
            self.request_oauth_error = oauth_problem
            return False

        self.request_token = self._get_value_from_raw_qs("oauth_token", response)
        self.request_token_secret = self._get_value_from_raw_qs("oauth_token_secret", response)
        return True


    def accessToken(self, request_token = None, request_token_secret = None, verifier = None):
        """
        Performs the corresponding API which returns the access token in a query string
        Accroding to the link (http://developer.linkedin.com/docs/DOC-1008), POST Querydict must include the following:
        * oauth_consumer_key
        * oauth_nonce
        * oauth_signature_method
        * oauth_timestamp
        * oauth_token (request token)
        * oauth_version
        """

        #################
        # BEGIN ROUTINE #
        #################
        self.request_token = request_token and request_token or self.request_token
        self.request_token_secret = request_token_secret and request_token_secret or self.request_token_secret
        self.verifier = verifier and verifier or self.verifier
        # if there is no request token, fail immediately
        if self.request_token is None:
            raise OAuthError("There is no Request Token. Please perform 'requestToken' method and obtain that token first.")

        if self.request_token_secret is None:
            raise OAuthError("There is no Request Token Secret. Please perform 'requestToken' method and obtain that token first.")

        if self.verifier is None:
            raise OAuthError("There is no Verifier Key. Please perform 'requestToken' method, redirect user to API authorize page and get the verifier.")
        
        # initialization
        self.access_oauth_nonce = self._generate_nonce()
        self.access_oauth_timestamp = self._generate_timestamp()

        # create Signature Base String
        method = "POST"
        url = self.getAccessTokenURL()
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": self.access_oauth_nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": self.access_oauth_timestamp,
                      "oauth_token" : self.request_token,
                      "oauth_verifier" : self.verifier,
                      "oauth_version": self.version,
                      }
        query_string = self._quote(self._urlencode(query_dict))
        signature_base_string = "&".join([self._quote(method), self._quote(url), query_string])
        # create actual signature
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.request_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]
        # it is time to create the heaader of the http request that will be sent
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_verifier="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (self._quote(self.access_oauth_nonce), self._quote(self.signature_method),
                           self.access_oauth_timestamp, self._quote(self.API_KEY),
                           self._quote(self.request_token), self._quote(self.verifier),
                           self._quote(signature), self._quote(self.version))

        # next step is to establish an HTTPS connection through the LinkedIn API
        # and fetch the request token.
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, self.ACCESS_TOKEN_URL, body = self._urlencode(query_dict), headers = {'Authorization': header})
        response = connection.getresponse()
        if response is None:
            self.access_oauth_error = "No HTTP response received."
            connection.close()
            return False

        response = response.read()
        connection.close()

        oauth_problem = self._get_value_from_raw_qs("oauth_problem", response)
        if oauth_problem:
            self.access_oauth_error = oauth_problem
            return False

        self.access_token = self._get_value_from_raw_qs("oauth_token", response)
        self.access_token_secret = self._get_value_from_raw_qs("oauth_token_secret", response)
        return True


    def GetProfile(self, member_id = None, url = None, fields=list()):
        """
        Gets the public profile for a specific user. It is determined by his/her member id or public url.
        If none of them is given, the information og the application's owner are returned.

        If none of them are given, current user's details are fetched.
        The argument '*fields' determines howmuch information will be fethced.

        Examples:
        client.GetProfile(merber_id = 123, url = None, 'first-name', 'last-name') : fetches the profile of a user whose id is 123. 

        client.GetProfile(merber_id = None, url = None, 'first-name', 'last-name') : fetches current user's profile

        client.GetProfile(member_id = None, 'http://www.linkedin.com/in/ozgurv') : fetches the profile of a  user whose profile url is http://www.linkedin.com/in/ozgurv
        
        @ Returns Profile instance
        """
        #################
        # BEGIN ROUTINE #
        #################
        # if there is no access token or secret, fail immediately
        if self.access_token is None:
            self.error = "There is no Access Token. Please perform 'accessToken' method and obtain that token first."
            raise OAuthError(self.error)
        
        if self.access_token_secret is None:
            self.error = "There is no Access Token Secret. Please perform 'accessToken' method and obtain that token first."
            raise OAuthError(self.error)
        
        # specify the url according to the parameters given
        raw_url = "/v1/people/"
        if url:
            url = self._quote(url)
            raw_url = (raw_url + "url=%s:public") % url
        elif member_id:
            raw_url = (raw_url + "id=%s" % member_id)
        else:
            raw_url = raw_url + "~"
        if url is None:
            known_fields=list()
            for item in fields:
                if item in ALL_PROFILE_FIELDS:
                    known_fields.append(item)
                    
            known_fields = ":(%s)" % ",".join(known_fields) if len(known_fields) > 0 else None
            if known_fields:
                raw_url = raw_url + known_fields
        
        # generate nonce and timestamp
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()

        # create signatrue and signature base string
        method = "GET"
        FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, raw_url)
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }
        
        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, hashlib.sha1)
        signature = binascii.b2a_base64(hashed.digest())[:-1]


        # create the HTTP header
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)
        
        # make the HTTP request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, raw_url, headers = {'Authorization': header})
        response = connection.getresponse()

        # according to the response, decide what you want to do
        if response is None:
            self.error = "No HTTP response received."
            connection.close()
            return None

        response = response.read()
        connection.close()

        error = self._parse_error(response)
        if error:
            self.error = error
            return None

        return Profile(response, fields) 
    ###############
    # END ROUTINE #
    ###############

    def GetConnections(self, member_id = None, public_url = None):
        """
        Fetches the connections of a user whose id is the given member_id or url is the given public_url
        If none of the parameters given, the connections of the current user are fetched.
        @Returns: a list of Profile instances or an empty list if there is no connection.

        Example urls:
        * http://api.linkedin.com/v1/people/~/connections (for current user)
        * http://api.linkedin.com/v1/people/id=12345/connections (fetch with member_id)
        * http://api.linkedin.com/v1/people/url=http%3A%2F%2Fwww.linkedin.com%2Fin%2Flbeebe/connections (fetch with public_url)
        """
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)
        
        #################
        # BEGIN ROUTINE #
        #################
        
        # first we need to specify the url according to the parameters given
        raw_url = "/v1/people/%s/connections"
        if member_id:
            raw_url = raw_url % ("id=" + member_id)
        elif public_url:
            raw_url = raw_url % ("url=" + self._quote(public_url))
        else:
            raw_url = raw_url % "~"

        # generate nonce and timestamp
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()
        
        # create signature and signature base string
        FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, raw_url)
        method = "GET"
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }
        
        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]

        # create the HTTP header
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)
        
        # make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, raw_url, headers = {'Authorization': header})
        response = connection.getresponse()

        # according to the response, decide what you want to do
        if response is None:
            self.error = "No HTTP response received."
            connection.close()
            return None

        response = response.read()
        connection.close()
        error = self._parse_error(response)
        if error:
            self.error = error
            return None


        document = minidom.parseString(response)
        connections = document.getElementsByTagName("person")
        result = []
        for connection in connections:
            profile = Profile(connection.toxml())
            if profile is not None:
                result.append(profile)

        ###############
        # END ROUTINE #
        ###############
        return result

    def GetSearch(self, parameters):
        """
        Use the Search API to find LinkedIn profiles using keywords,
        company, name, or other methods. This returns search results,
        which are an array of matching member profiles. Each matching
        profile is similar to a mini-profile popup view of LinkedIn
        member profiles.

        Request URL Structure:
        http://api.linkedin.com/v1/people?keywords=['+' delimited keywords]&name=[first name + last name]&company=[company name]&current-company=[true|false]&title=[title]&current-title=[true|false]&industry-code=[industry code]&search-location-type=[I,Y]&country-code=[country code]&postal-code=[postal code]&network=[in|out]&start=[number]&count=[1-10]&sort-criteria=[ctx|endorsers|distance|relevance]
        """
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)

        # first we need to specify the url according to the parameters given
        raw_url = "/v1/people"
        request_url = "%s?%s" % (raw_url, self._urlencode(parameters))
        
        # generate nonce and timestamp
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()
        
        # create signature and signature base string
        FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, raw_url)
        
        method = "GET"
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }
        query_dict.update(parameters)
        
        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]

        # create the HTTP header
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)

        # make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, request_url, headers = {'Authorization': header})
        response = connection.getresponse()
        
        # according to the response, decide what you want to do
        if response is None:
            self.error = "No HTTP response received."
            connection.close()
            return None

        response = response.read()

        connection.close()
        error = self._parse_error(response)
        if error:
            self.error = error
            return None

        document = minidom.parseString(response)
        connections = document.getElementsByTagName("person")
        result = []
        for connection in connections:
            profile = Profile(connection.toxml())
            if profile is not None:
                result.append(profile)
        return result

    def SendMessage(self, subject, message, ids = [], send_yourself = False):
        """
        Sends a Non-HTML message and subject to the members whose IDs are given as a parameter 'ids'.
        If the user gives more than 10 ids, the IDs after 10th ID are ignored.
        @Input: string x string x list x bool
        @Output: bool
        Returns True if successfully sends the message otherwise returns False.

        Important Note: You can send a message at most 10 connections at one time.
        
        Technical Explanation:
        ---------------------
        Sends a POST request to the URL 'http://api.linkedin.com/v1/people/~/mailbox'.
        The XML that will be sent looks like this:
        <?xml version='1.0' encoding='UTF-8'?>
          <mailbox-item>
            <recipients>
             <recipient>
               <person path='/people/{id}' />
             </recipient>
            </recipients>
            <subject>{subject}</subject>
            <body>{message}</body>
          </mailbox-item>

        The resulting XML would be like this:
        if result is None or '', it is guaranteed that you sent the message. If there occurs an error, you get the following:
        <?xml version='1.0' encoding='UTF-8' standalone='yes'?>
         <error>
           <status>...</status>
           <timestamp>...</timestamp>
           <error-code>...</error-code>
           <message>...</message>
          </error>
        """
        #######################################################################################
        # BEGIN ROUTINE                                                                       #
        # What we do here is first we need to shorten to ID list to 10 elements just in case. #
        # Then we need to strip HTML tags using HTMLParser library.                           #
        # Then we are going  to build up the XML body and post the request.                   #
        # According to the response parsed, we return True or False.                          #
        #######################################################################################
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)

        # Shorten the list.
        ids = ids[:10]
        if send_yourself:
            ids = ids[:9]
            ids.append("~")
            
        subjectStripper = Stripper()
        subjectStripper.feed(subject)
        subject = subjectStripper.getAlteredData()
        bodyStripper = Stripper()
        bodyStripper.feed(message)
        body = bodyStripper.getAlteredData()

        # Generate nonce and timestamp.
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()

        # create signature and signature base string
        URL = "/v1/people/~/mailbox"
        FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, URL)
        method = "POST"
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }
        
        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]

        # Create the HTTP header
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)
        
        # Build up the POST body.
        builder = XMLBuilder("mailbox-item")
        recipients_element = builder.create_element("recipients")
        subject_element = builder.create_element_with_text_node("subject", subject)
        body_element = builder.create_element_with_text_node("body", body)
        for member_id in ids:
            recipient_element = builder.create_element("recipient")
            person_element = builder.create_element("person")
            person_element.setAttribute("path", "/people/%s" % member_id)
            recipient_element.appendChild(person_element)
            recipients_element.appendChild(recipient_element)

        builder.append_element_to_root(recipients_element)
        builder.append_element_to_root(subject_element)
        builder.append_element_to_root(body_element)
        body = builder.xml()

        # Make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, URL, body = body, headers = {'Authorization': header})
        response = connection.getresponse()

        response = response.read()
        connection.close()

        # If API server sends us a response, we know that there occurs an error.
        # So we have to parse the response to make sure what causes the error.
        # and let the user know by returning False.
        if response:
            self.error = self._parse_error(response)
            return False

        ###############
        # END ROUTINE #
        ###############
        return True


    def SendInvitation(self, subject, message, first_name, last_name, email):
        """
        Sends an invitation to the given email address.
        This method is very similiar to 'SendMessage' method.
        @input: string x string x string x string x string
        @output: bool
        """
        
        #########################################################################################
        # BEGIN ROUTINE                                                                         #
        # What we do here is first, we need to check the access token.                          #
        # Then we need to strip HTML tags using the HTMLParser library.                         #
        # Then we are going to build up the XML body and post the request.                      #
        # According to the response parsed, we return True or False.                            #
        #########################################################################################
        
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)
        
        subjectStripper = Stripper()
        subjectStripper.feed(subject)
        subject = subjectStripper.getAlteredData()
        bodyStripper = Stripper()
        bodyStripper.feed(message)
        body = bodyStripper.getAlteredData()

        # Generate nonce and timestamp.
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()

        # create signature and signature base string
        URL = "/v1/people/~/mailbox"
        FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, URL)
        method = "POST"
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }
        
        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]

        # Create the HTTP header
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)
        
        # Build up the POST body.
        builder = XMLBuilder("mailbox-item")
        recipients_element = builder.create_element("recipients")
        subject_element = builder.create_element_with_text_node("subject", subject)
        body_element = builder.create_element_with_text_node("body", body)
        recipient_element = builder.create_element("recipient")
        person_element = builder.create_element("person")
        person_element.setAttribute("path", "/people/email=%s" % email)
        first_name_element = builder.create_element_with_text_node("first-name", first_name)
        last_name_element = builder.create_element_with_text_node("last-name", last_name)
        builder.append_list_of_elements_to_element(person_element, [first_name_element, last_name_element])
        recipient_element.appendChild(person_element)
        recipients_element.appendChild(recipient_element)

        item_content_element = builder.create_element("item-content")
        invitation_request_element = builder.create_element("invitation-request")
        connect_type_element = builder.create_element_with_text_node("connect-type", "friend")
        invitation_request_element.appendChild(connect_type_element)
        item_content_element.appendChild(invitation_request_element)
        
        
        builder.append_element_to_root(recipients_element)
        builder.append_element_to_root(subject_element)
        builder.append_element_to_root(body_element)
        builder.append_element_to_root(item_content_element)
        body = builder.xml()

        # Make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, URL, body = body, headers = {'Authorization': header})
        response = connection.getresponse()
        
        response = response.read()
        connection.close()

        # If API server sends us a response, we know that there occurs an error.
        # So we have to parse the response to make sure what causes the error.
        # and let the user know by returning False.
        if response:
            self.error = self._parse_error(response)
            return False

        ###############
        # END ROUTINE #
        ###############
        return True

    def SetStatus(self, status_message):
        """
        Issues a status of the connected user. There is a 140 character limit on status message.
        If it is longer than 140 characters, it is shortened.
        -----------
        Usage Rules
        * We must use an access token from the user.
        * We can only set status for the user who grants us access.
        -----------
        @input: string
        @output: bool
        """
        ##################
        # BEGIN ROUTINE  #
        ##################
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)

        # Shorten the message just in case.
        status_message = str(status_message)
        if len(status_message) > 140:
            status_message = status_message[:140]

        # Generate nonce and timestamp.
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()

        # create signature and signature base string
        URL = "/v1/people/~/current-status"
        FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, URL)
        method = "PUT"
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }
        
        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]

        # Create the HTTP header
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)


        # Build up the XML request
        builder = XMLBuilder("current-status")
        status_node = builder.document.createTextNode(status_message)
        builder.root.appendChild(status_node)
        body = builder.xml()
        
        # Make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, URL, body = body, headers = {'Authorization': header})
        response = connection.getresponse()
        
        response = response.read()
        connection.close()

        # If API server sends us a response, we know that there occurs an error.
        # So we have to parse the response to make sure what causes the error.
        # and let the user know by returning False.
        if response:
            self.error = self._parse_error(response)
            return False

        ###############
        # END ROUTINE #
        ###############
        return True

        
    def ClearStatus(self):
        """
        Clears the status of the connected user.
        -----------
        Usage Rules
        * We must use an access token from the user.
        * We can only set status for the user who grants us access.
        -----------
        @input: none
        @output: bool
        """
        ##################
        # BEGIN ROUTINE  #
        ##################
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)

        # Generate nonce and timestamp.
        nonce = self._generate_nonce()
        timestamp = self._generate_timestamp()

        # create signature and signature base string
        URL = "/v1/people/~/current-status"
        FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, URL)
        method = "DELETE"
        query_dict = {"oauth_consumer_key": self.API_KEY,
                      "oauth_nonce": nonce,
                      "oauth_signature_method": self.signature_method,
                      "oauth_timestamp": timestamp,
                      "oauth_token" : self.access_token,
                      "oauth_version": self.version
                      }
        
        signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
        hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]

        # Create the HTTP header
        header = 'OAuth realm="http://api.linkedin.com", '
        header += 'oauth_nonce="%s", '
        header += 'oauth_signature_method="%s", '
        header += 'oauth_timestamp="%d", '
        header += 'oauth_consumer_key="%s", '
        header += 'oauth_token="%s", '
        header += 'oauth_signature="%s", '
        header += 'oauth_version="%s"'
        header = header % (nonce, self.signature_method, timestamp,
                           self._quote(self.API_KEY), self._quote(self.access_token),
                           self._quote(signature), self.version)

        
        # Make the request
        connection = httplib.HTTPSConnection(self.API_ENDPOINT)
        connection.request(method, URL, headers = {'Authorization': header})
        response = connection.getresponse()
        
        response = response.read()
        connection.close()

        # If API server sends us a response, we know that there occurs an error.
        # So we have to parse the response to make sure what causes the error.
        # and let the user know by returning False.
        if response:
            self.error = self._parse_error(response)
            return False

        ###############
        # END ROUTINE #
        ###############
        return True
    
    def ShareUpdate(self, 
                    comment=None, 
                    title=None, 
                    submitted_url=None, 
                    submitted_image_url=None, 
                    description=None, 
                    visibility="connections-only"):
        """
        Use the Share API to have a member share content with their network or with all of LinkedIn
        -----------
        Usage Rules
        * We must use an access token from the user.
        * We can only share items for the user who grants us access.
        -----------
        visibility: anyone or connections-only


        @output: bool

        SAMPLE 
            <?xml version="1.0" encoding="UTF-8"?>
            <share>
              <comment>83% of employers will use social media to hire: 78% LinkedIn, 55% Facebook, 45% Twitter [SF Biz Times] http://bit.ly/cCpeOD</comment>
              <content>
                 <title>Survey: Social networks top hiring tool - San Francisco Business Times</title>
                 <submitted-url>http://sanfrancisco.bizjournals.com/sanfrancisco/stories/2010/06/28/daily34.html</submitted-url>
                 <submitted-image-url>http://images.bizjournals.com/travel/cityscapes/thumbs/sm_sanfrancisco.jpg</submitted-image-url>
              </content>
              <visibility>
                 <code>anyone</code>
              </visibility>
            </share>


        """
        ##################
        # BEGIN ROUTINE  #
        ##################
        # check the requirements
        if (not self.access_token) or (not self.access_token_secret):
            self.error = "You do not have an access token. Plase perform 'accessToken()' method first."
            raise OAuthError(self.error)
        
        all_text=''
        
        if comment is not None:
            comment = str(comment).strip()[:700]
            all_text+=comment
            
        if title is not None:
            title = str(title).strip()[:200]
            all_text+=title

        if description is not None:
            description = str(description).strip()[:400]
            all_text+=description
        
        if all_text!='':
        

            # Generate nonce and timestamp.
            nonce = self._generate_nonce()
            timestamp = self._generate_timestamp()
    
            # create signature and signature base string
            URL = "/v1/people/~/shares"
            FULL_URL = "%s://%s%s" % (self.URI_SCHEME, self.API_ENDPOINT, URL)
            method = "POST"
            query_dict = {"oauth_consumer_key": self.API_KEY,
                          "oauth_nonce": nonce,
                          "oauth_signature_method": self.signature_method,
                          "oauth_timestamp": timestamp,
                          "oauth_token" : self.access_token,
                          "oauth_version": self.version
                          }
    
            signature_base_string = "&".join([self._quote(method), self._quote(FULL_URL), self._quote(self._urlencode(query_dict))])
            hashed = hmac.new(self._quote(self.API_SECRET) + "&" + self._quote(self.access_token_secret), signature_base_string, hashlib.sha1)
            signature = binascii.b2a_base64(hashed.digest())[:-1]
    
            # Create the HTTP header
            header = 'OAuth realm="http://api.linkedin.com", '
            header += 'oauth_nonce="%s", '
            header += 'oauth_signature_method="%s", '
            header += 'oauth_timestamp="%d", '
            header += 'oauth_consumer_key="%s", '
            header += 'oauth_token="%s", '
            header += 'oauth_signature="%s", '
            header += 'oauth_version="%s"'
            header = header % (nonce, self.signature_method, timestamp,
                               self._quote(self.API_KEY), self._quote(self.access_token),
                               self._quote(signature), self.version)
    
    
            # Build up the XML request
            builder = XMLBuilder("share")
    
            if len(comment) > 0:
                comment_element = builder.create_element_with_text_node("comment", comment)
                builder.append_element_to_root(comment_element)
    
    
            if (submitted_url is not None) or (title is not None):
                content_element = builder.create_element("content")
                if submitted_url is not None:
                    submitted_url_element = builder.create_element_with_text_node("submitted-url", submitted_url)
                    content_element.appendChild(submitted_url_element)
    
                    # must have url to inlcude image url
                    if submitted_image_url is not None:
                        submitted_image_url_element = builder.create_element_with_text_node("submitted-image-url", submitted_image_url)
                        content_element.appendChild(submitted_image_url_element)
    
                if title is not None:
                    title_element = builder.create_element_with_text_node("title", title)
                    content_element.appendChild(title_element)
    
                if description is not None:
                    description_element = builder.create_element_with_text_node("description", description)
                    content_element.appendChild(description_element)
    
                builder.append_element_to_root(content_element)
    
            visibility_element = builder.create_element("visibility")
            code_element = builder.create_element_with_text_node("code", visibility)
            visibility_element.appendChild(code_element)
    
    
            builder.append_element_to_root(visibility_element)
    
            body = builder.xml()        
    
            # Make the request
            connection = httplib.HTTPSConnection(self.API_ENDPOINT)
            connection.request(method, URL, body = body, headers = {'Authorization': header})
            response = connection.getresponse()
    
            response = response.read()
            connection.close()
    
            # If API server sends us a response, we know that there occurs an error.
            # So we have to parse the response to make sure what causes the error.
            # and let the user know by returning False.
            if response:
                self.error = self._parse_error(response)
                return False
        else:
            self.error = "No comment, description, title provided"
            return False

            ###############
            # END ROUTINE #
            ###############
        return True

        
    def getRequestTokenError(self):
        return self.request_oauth_error

    def getAccessTokenError(self):
        return self.access_oauth_error

    def getError(self):
        return self.error
    
    def clear(self):
        self.request_token = None
        self.access_token  = None
        self.verifier      = None

        self.request_token_secret = None
        self.access_token_secret = None
        
        self.request_oauth_nonce     = None
        self.request_oauth_timestamp = None
        self.access_oauth_nonce      = None
        self.access_oauth_timestamp  = None
        
        self.request_oauth_error     = None
        self.access_oauth_error      = None
        self.error                   = None
