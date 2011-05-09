#!/usr/bin/env python

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from django.core.management import setup_environ
import settings
setup_environ(settings)


import erm.core.models

from erm.lib.api import *
#import erm.datamanager.models

from erm.settings import *
from lib.logger import Logger
import time
import datetime
import urllib

class SearchEngine(object):
    
    def __init__(self, 
                 entity_type, 
                 wipe_index=False):
        
        self.active=SEARCH_ENGINE_ACTIVE
        self.engine=SEARCH_ENGINE_ENGINE
                
        self.entity_type=entity_type
        self.logger=Logger()

        if self.active:
            if self.engine=='lucene':
                from erm.lib.lucene_engine import LuceneEngine
                self.engine=LuceneEngine("erm_" + entity_type, wipe_index)
            pass

    def searchable_attrs(self, entity_type_obj):
        data_fields_keys=["entity_id", "entity_slug", "entity_name"]

        entity_type_attributes=entity_type_obj.to_dict(False).get('attributes')
        
        for attribute in entity_type_attributes:
            if (attribute.get('kind') in ('string', 'long_text', 'raw_text')) and attribute.get('searchable'):
                data_fields_keys.append(attribute.get('slug'))
        return data_fields_keys
    
    def prepare_data(self, entity):
        data_fields=list()
        
        data_fields.append({"name":"entity_id", 
                            "value":str(entity.id), 
                            "store":True, 
                            "analyze":False })

        data_fields.append({"name":"entity_name", 
                            "value":entity.name, 
                            "store":True, 
                            "analyze":True })

        data_fields.append({"name":"entity_type", 
                            "value":entity.type.slug, 
                            "store":True, 
                            "analyze":True })

        data_fields.append({"name":"entity_slug", 
                            "value":entity.slug, 
                            "store":True, 
                            "analyze":False })
        
        data_fields.append({"name":"entity_name_sort", 
                            "value":entity.name, 
                            "store": True, 
                            "analyze": False })
        
        data_fields.append({"name":"creation_date", 
                            "value":str(int(time.mktime(entity.creation_date.timetuple()))), 
                            "store":True, 
                            "analyze":False })
        
        data_fields.append({"name":"modification_date", 
                            "value":str(int(time.mktime(entity.modification_date.timetuple()))), 
                            "store":True, 
                            "analyze":False })

        if entity.custom_date:
            _custom_date=entity.custom_date
        else:    
            _custom_date=datetime.datetime(2000, 1, 1)
        
        data_fields.append({"name":"custom_date", 
                            "value":str(int(time.mktime(_custom_date.timetuple()))), 
                            "store":True, 
                            "analyze":False })
        
        data_fields_keys=self.searchable_attrs(entity.type)
        entity_dict=entity.to_dict(False)
        entity_attributes=entity_dict.get('attributes')
        for attribute in data_fields_keys:
            _value=entity_attributes.get(attribute)
            if _value==None:
                _value=""
            data_fields.append({"name":attribute, 
                                "value":_value, 
                                "store":False, 
                                "analyze":True })
        
        data_fields.append({"name":'tags', 
                            "value":entity_dict.get('tags'), 
                            "type":'tags',
                            "store":False, 
                            "analyze":True })

        for _item in SEARCH_ENGINE_SORTABLE_ATTRIBUTES.get(self.entity_type, []):
            _field=_item['field']
            _value=entity_attributes.get(_field)
            _kind=_item.get('kind', 'text')
            _name=_item.get('name', "%s_sort" % _field)
            if _kind=='datetime':
                _value=str(int(time.mktime(_value.timetuple())))
            elif _kind=='number':
                _value=_value[:_item.get('length',10)].zfill(_item.get('length',10))
            else: # _kind=='text':
                _value=_value[:_item.get('length',20)]
            _field_content={"name":_name, 
                                "value":_value, 
                                "type":"sort",
                                "store":True, 
                                "analyze": False}
            data_fields.append(_field_content)
            
        return data_fields
    
    def add_entity(self, entity):
        if self.active and self.engine:
            return self.engine.add_document(self.prepare_data(entity))
        else:
            return False
    
    def update_entity(self, entity):
        if self.active and self.engine:
            return self.engine.update_document(self.prepare_data(entity), "entity_id", str(entity.id))
        else:
            return False
    
    def delete_entity(self, entity):
        if self.active and self.engine:
            return self.engine.delete_document("entity_id", str(entity.id))
        else:
            return False
    
    def optimize(self):
        if self.active and self.engine:
            return self.engine.optimize()
        else:
            return False
    
    def search(self, 
               queries, 
               sort=[], 
               range=[],
               page_size=100, 
               page_num=0, 
               items_limit=None, 
               mode='SHOULD',
               get_query=False,
               preserve_query=False):
        result = dict()
        if self.active and self.engine:
            _queries=list()
            search_attrs=list()
            for query in queries:
                _query=query
                if query.get('query', "")!="":
                    if isinstance(query['query'], (str,unicode)):
                        query['query']=urllib.unquote(query['query'])
                    elif isinstance(query['query'], list):
                        for _item in query['query']:
                            if isinstance(_item, dict):
                                for key, value in _item.items():
                                    if isinstance(value, (str,unicode)):
                                        _item[key]=urllib.unquote(value)
                    if len(query.get('fields'))==0:
                        if len(search_attrs)==0:
                            entity_type_obj=erm.core.models.EntityType.objects.get(slug=self.entity_type)
                            search_attrs=self.searchable_attrs(entity_type_obj)
                        _query['fields']=search_attrs
                    _queries.append(_query)
            if len(_queries):
                result = self.engine.search(
                                            ("entity_id", 
                                             "entity_slug", 
                                             "entity_name",
                                             ), 
                                             _queries, 
                                             sort, 
                                             range, 
                                             int(page_size), 
                                             int(page_num), 
                                             items_limit, 
                                             mode,
                                             get_query,
                                             preserve_query)
        return result

def main():
    e=Entity.objects.get(slug='space2', type__slug='zzubber')
    se=SearchEngine(e.type.slug, True)
    et=EntityType.objects.get(slug=se.entity_type)
    print se.add_entity(e)

if __name__=='__main__':
    main()