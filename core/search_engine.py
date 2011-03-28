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

class SearchEngine(object):
    
    def __init__(self, 
                 entity_type, 
                 wipe_index=False):
        
        self.active=SEARCH_ENGINE_ACTIVE
        self.engine=SEARCH_ENGINE_ENGINE
                
        self.entity_type=entity_type
        if self.active:
            if self.engine=='lucene':
                from erm.lib.lucene_engine import LuceneEngine
                self.engine=LuceneEngine("erm_" + entity_type, wipe_index)
            pass

    def searchable_attrs(self, entity_type_obj):
        data_fields_keys=list()

        entity_type_attributes=entity_type_obj.to_dict(False).get('attributes')
        
        for attribute in entity_type_attributes:
            if (attribute.get('kind') in ('string', 'long_text')) and attribute.get('searchable'):
                data_fields_keys.append(attribute.get('slug'))
        return data_fields_keys
    
    def prepare_data(self, entity):
        data_fields=list()
        data_fields.append({"name":"entity_id", "value":str(entity.id), "store":True, "analyze":False })
        data_fields.append({"name":"entity_name", "value":entity.name, "store":True, "analyze":True })
        data_fields.append({"name":"entity_slug", "value":entity.slug, "store":True, "analyze":False })
        
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
    
    def search(self, queries, page_size=100, page_num=0, items_limit=None, mode='SHOULD'):
        result = dict()
        if self.active and self.engine:
            _queries=list()
            search_attrs=list()
            for query in queries:
                _query=query
                if query.get('query', "")!="":
                    if len(query.get('fields'))==0:
                        if len(search_attrs)==0:
                            entity_type_obj=erm.core.models.EntityType.objects.get(slug=self.entity_type)
                            search_attrs=self.searchable_attrs(entity_type_obj)
                        _query['fields']=search_attrs
                    _queries.append(_query)
            if len(_queries):
                result = self.engine.search(("entity_id", "entity_slug", "entity_name"), _queries, int(page_size), int(page_num), items_limit, mode)
        return result

def main():
    e=Entity.objects.get(slug='space2', type__slug='zzubber')
    se=SearchEngine(e.type.slug, True)
    et=EntityType.objects.get(slug=se.entity_type)
    print se.add_entity(e)

if __name__=='__main__':
    main()