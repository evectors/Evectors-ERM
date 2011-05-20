#!/usr/bin/env python

# django bootstrap

import os
import sys

#sys.path.insert(0, '/opt/python2.5/site-packages')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import settings
if getattr(settings, "MIXED_DJANGO_ENVIRONMENT", None) is not None:    
        import sys
        sys.path.insert(0, settings.AGG_MIXED_DJANGO_INSTALL_PATH)

from django.core.management import setup_environ
setup_environ(settings)

# end django bootstrap

import urllib, urllib2

import test_settings

if test_settings.ENVIRONMENT is 'Aggregator':
    from apps.aggregator.models import *
    API_KEY=ApiKey.objects.filter(status='E')[0].key
elif test_settings.ENVIRONMENT is 'ERM':
    API_KEY=settings.SECRET_KEY
    if isinstance(API_KEY, list):
        API_KEY=API_KEY[0]


from django.core.management import setup_environ
setup_environ(settings)

import unittest
#import erm.settings

import cjson

from optparse import OptionParser

TESTS=[
       {'type':'relative', 
        'url':'/core/api/%s/entity/type=zzubber', 
        'method':'GET', 
        'format':'json', 
        'check':{'success':True, 'data__count__gt':0}},
       {'type':'relative', 
        'url':'/core/api/%s/entity/type=zzubberz', 
        'method':'GET', 
        'format':'json', 
        'check':{'success':True, 'data__count__gt':0}},
       {'type':'relative', 
        'url':'/core/api/%s/entity/type=zzubber', 
        'method':'GET', 
        'format':'json', 
        'check':{'success':True, 'data__count__is':0}}
       ]
class TestApi(unittest.TestCase):
            
    def __init__(self, testname, descriptor, url):
        super(TestApi, self).__init__(testname)
        self.descriptor = descriptor
        self.base_url = url 

    def test_descriptor(self):
        _type = self.descriptor.get('type', None)
        if _type is not None:
            if _type in ('relative', 'absolute'):
                try:
                    _url=self.descriptor['url']
                    if '%s' in _url:
                        _url=_url.replace('%25', '*25')
                        _url=_url % API_KEY
                        _url=_url.replace('*25', '%25')
                        
                    if _type =='relative':
                        _url=self.base_url + _url
                    
                    data=self.descriptor.get('data', None)
                    method = self.descriptor.get('method', 'GET')
                    if data is None:
                        req = urllib2.Request(_url)
                    else:
                        if self.descriptor.get('format_data', None) == "json":
                            post_data = cjson.encode(data)
                        else:
                            post_data = data

                        req = urllib2.Request(_url, post_data)
                    req.get_method = lambda: method                     
                    try:
                        response = urllib2.urlopen(req)
                        response_text=response.read()
                    except urllib2.HTTPError,error:
                        self.fail("%s (%s) - %s" % (error.code, _url, error.read()))
                    #self.failIf(True, '%s' % response)
                    
                    operator='exact'
                    action=None
                    _format= self.descriptor.get('format', None)
                    if _format=='json':
                        _res=cjson.decode(response_text)
                        for key,value in self.descriptor.get('check', dict()).items():
                            operator='exact'
                            action=None
                            if '__' in key:
                                _chunks=key.split('__')
                                key = _chunks[0]
                                if len(_chunks)==2:
                                    operator = _chunks[1]
                                elif len(_chunks)==3:
                                    action=_chunks[1]
                                    operator = _chunks[2]
                            key_value=_res
                            for path_chunk in key.split('.'):
                                #print "%s [%s]\n\n" % (key_value, path_chunk)
                                chunk_pos=None
                                if '[' in path_chunk:
                                    path_chunk,chunk_pos=path_chunk.split('[')
                                    chunk_pos=int(chunk_pos[:-1])
                                if path_chunk!="":
                                    key_value=key_value.get(path_chunk, None)
                                if chunk_pos is not None:
                                    key_value=key_value[chunk_pos]
                            if action is not None:
                                if action=='count' or action=='len':
                                    key_value=len(key_value)
                                else:
                                    key_value=eval('%s(key_value)' % operation)
                            operators={"gt":">",
                                       "lt":"<",
                                       "gte":">=",
                                       "lte":"<=",
                                       "exact":"==",
                                       "ne":"!=",
                                       }
                            #print "%s [%s - %s]\n\n" % (key_value, operator, value)
                            
                            if operator in operators.keys():
                                if not isinstance(value, int) and not isinstance(value, bool) and value is not None:
                                    value="'%s'" % value 
                                if not isinstance(key_value, int) and not isinstance(key_value, bool) and key_value is not None:
                                    key_value="'%s'" % key_value 
                                expression=("%s %s %s" % (key_value, operators[operator], value))
                                #print expression
                                if not eval(expression):
                                    self.fail("bad result for key '%s': %s [expression: %s] - %s - %s" % (key, key_value, expression, _url, _res))
                            else:
                                self.fail("unknown operator: %s - %s" % (operator, _url))
                except urllib2.HTTPError,error:
                    self.fail("%s (%s)" % (error.code, _url))
                except Exception,error:
                    self.fail("%s (%s) - %s - %s" % (Exception, error, _url, self.descriptor))
            elif _type=='dummy':
                pass
            else:
                self.fail("unknown test type: %s" % (_type))
if __name__ == '__main__':
    USAGE = "usage: api.py [options] [filter]"
    parser = OptionParser(USAGE)
    parser.add_option("--testfile", 
                      action="store", 
                      dest="testfilepath", 
                      default=test_settings.TESTS_PATH,
                      help="pass a custom tests json file path")

    parser.add_option("-u", "--url", 
                      action="store", 
                      dest="url", 
                      default=test_settings.API_URL,
                      help="ERM server url")

    opts, args = parser.parse_args()
    
    jsonfile=open(opts.testfilepath,"r")
    
    try:
        jsontext = jsonfile.read()
        TESTS=cjson.decode(jsontext)
        suite = unittest.TestSuite()
        for test_descriptor in TESTS:
            suite.addTest(TestApi('test_descriptor', test_descriptor, opts.url))
                    
        unittest.TextTestRunner().run(suite)
    except Exception, err:
        raise
    finally:
        jsonfile.close()