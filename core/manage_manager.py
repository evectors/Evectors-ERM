from erm.core.models import *
from erm.datamanager.models import *
from erm.lib.misc_utils import *
from erm.core.entity_manager import *
from erm.core.rel_manager import *
from erm.lib.api import ApiError, ERROR_CODES

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import EmptyQuerySet
from django.db import connection, DatabaseError, IntegrityError, transaction

def get_erm_tree(params):
    try:
        req_entity_type=None
        entity_types_params=dict()
        entity=None
        req_rel_type=None
        
        flat_dict=None
        flat=False
        if params.get('flat')=="1":
            flat_dict=dict()
            flat=True
        
        if params.get('entity'):
            try:
                entity=Entity.objects.get(id=int(params.get('entity')))
                req_entity_type=entity.type
            except:
                entity=None
        
        if not req_entity_type and params.get('entity_type_id'):
            try:
                req_entity_type=EntityType.objects.get(id=int(params.get('entity_type_id')))
            except:
                req_entity_type=None
                
        if not req_entity_type and params.get('entity_type'):
            try:
                req_entity_type=EntityType.objects.get(slug=params.get('entity_type'))
            except:
                req_entity_type=None
                
        req_rel_type=get_rel_type({"id":params.get('rel'), "slug":params.get('rel_slug')})
        if len(req_rel_type)==1:
            req_rel_type=req_rel_type[0]
        else:
            req_rel_type=None
                
        if req_entity_type:    
            entity_types_params={"id":req_entity_type.id}
        entity_types=get_entity_type(entity_types_params)
        result=dict()
        
        for entity_type in entity_types:
            entity_dict=dict()
            
            if not entity:
                for key in ("slug", "name", "id"):
                    entity_dict[key]=getattr(entity_type, key)
                    entity_dict['obj_type']='entity_type'
            else:
                for key in ("slug", "name", "id"):
                    entity_dict[key]=getattr(entity, key)
                    entity_dict['obj_type']='entity'
                entity_dict["type"]=req_entity_type.id
            
            
            rel_types_allowed=get_rel_type_allowed({"entity_type_from_id":entity_type.id})
            rel_reverse_types_allowed=get_rel_type_allowed({"entity_type_to_id":entity_type.id})
            rels_dict=dict()
            
            for rel_type_allowed in rel_types_allowed:
                if not req_rel_type or req_rel_type.id==rel_type_allowed.rel_type.id:
                    rel_type_key=rel_type_allowed.rel_type.name
                    if not rels_dict.has_key(rel_type_key):
                        rels_dict[rel_type_key]={"id":rel_type_allowed.rel_type.id,"name":rel_type_allowed.rel_type.name, "slug":rel_type_allowed.rel_type.slug, "count":0}
                    
                    if not entity:
                        rels_dict[rel_type_key]["count"]+=1
                        if params.get('to')=="1":
                            entity_to=dict((key, getattr(rel_type_allowed.entity_type_to,key))for key in ("slug", "name", "id"))
                            entity_to['obj_type']='entity_type'
                            if not rels_dict[rel_type_key].has_key('items'):
                                rels_dict[rel_type_key]['items']=list()
                            rels_dict[rel_type_key]['items'].append(entity_to)
                    else:
                        rels=Relationship.objects.filter(entity_from=entity, rel_type=rel_type_allowed.rel_type)
                        rels_dict[rel_type_key]["count"]+=rels.count()
                        if params.get('to')=="1":
                            offset=params.get("offset", 0)
                            limit=params.get("limit", 20)
                            rels_dict[rel_type_key]["offset"]=offset
                            rels_dict[rel_type_key]["limit"]=limit
                            relationships=rels[offset:offset+limit]
                            entity_to=[item.entity_to.to_dict(True) for item in relationships]
                            if flat:
                                for relationship in relationships:
                                    if not flat_dict.has_key(relationship.entity_to.id):
                                        flat_dict[relationship.entity_to.id]=relationship.entity_to.to_dict()
                            
                            if not rels_dict[rel_type_key].has_key('items'):
                                rels_dict[rel_type_key]['items']=list()
                            rels_dict[rel_type_key]['items'].extend(entity_to)
            if len(rels_dict)>0 or not req_rel_type:
                if params.get('rels')=="1":
                    entity_dict['relationships']=rels_dict.values()
                else:
                    entity_dict['relationships']=len(rels_dict)
                result[entity_type.name]=entity_dict

            rels_dict=dict()
            for rel_type_allowed in rel_reverse_types_allowed:
                if not req_rel_type or req_rel_type.id==rel_type_allowed.rel_type.id:
                    rel_type_key=rel_type_allowed.rel_type.name
                    if not rels_dict.has_key(rel_type_key):
                        rels_dict[rel_type_key]={"id":rel_type_allowed.rel_type.id,"name":rel_type_allowed.rel_type.name_reverse, "slug":rel_type_allowed.rel_type.slug, "count":0}
                    
                    if not entity:
                        rels_dict[rel_type_key]["count"]+=1
                        if params.get('to')=="1":
                            entity_from=dict((key, getattr(rel_type_allowed.entity_type_from,key))for key in ("slug", "name", "id"))
                            entity_from['obj_type']='entity_type'
                            if not rels_dict[rel_type_key].has_key('items'):
                                rels_dict[rel_type_key]['items']=list()
                            rels_dict[rel_type_key]['items'].append(entity_from)
                    else:
                        rels=Relationship.objects.filter(entity_from=entity, rel_type=rel_type_allowed.rel_type)
                        rels_dict[rel_type_key]["count"]+=rels.count()
                        if params.get('to')=="1":
                            offset=params.get("offset", 0)
                            limit=params.get("limit", 20)
                            rels_dict[rel_type_key]["offset"]=offset
                            rels_dict[rel_type_key]["limit"]=limit
                            relationships=rels[offset:offset+limit]
                            entity_from=[item.entity_from.to_dict(True) for item in relationships]
                            if flat:
                                for relationship in relationships:
                                    if not flat_dict.has_key(relationship.entity_from.id):
                                        flat_dict[relationship.entity_from.id]=relationship.entity_from.to_dict()
                            
                            if not rels_dict[rel_type_key].has_key('items'):
                                rels_dict[rel_type_key]['items']=list()
                            rels_dict[rel_type_key]['items'].extend(entity_from)
            if len(rels_dict)>0 or not req_rel_type:
                if params.get('rels')=="1":
                    entity_dict['reverse_relationships']=rels_dict.values()
                else:
                    entity_dict['reverse_relationships']=len(rels_dict)
                result[entity_type.name]=entity_dict

        if flat and entity:
            return {"entities":flat_dict.values()}
        else:
            return result.values()
    except Exception, err:
       raise ApiError(None, 101, err)

def get_entities_rel(params):
#    try:
        objects=Relationship.objects.all()

        entity_a=None
        entity_b=None
        
        
        if params.has_key('entity_from_id') and params.get('entity_from_id'):
            entity_a=Entity.objects.get(id=params.get('entity_from_id'))
        if not entity_a and params.has_key('entity_from') and params.get('entity_from') and params.has_key('entity_from_type') and params.get('entity_from_type'):
                entity_a=Entity.objects.get(slug=params.get('entity_from'), type__slug=params.get('entity_from_type'))

        if params.has_key('entity_to_id') and params.get('entity_to_id'):
            entity_b=Entity.objects.get(id=params.get('entity_to_id'))
        if not entity_b and params.has_key('entity_to') and params.get('entity_to') and params.has_key('entity_to_type') and params.get('entity_to_type'):
                entity_b=Entity.objects.get(slug=params.get('entity_to'), type__slug=params.get('entity_to_type'))
        
        result=list()
        if entity_a and entity_b:    
            forward_list=Relationship.objects.filter(entity_from=entity_a, entity_to=entity_b)
            for rel in forward_list:
                result.append(rel.to_dict())
            backward_list=Relationship.objects.filter(entity_from=entity_b, entity_to=entity_a)
            for rel in backward_list:
                rel_dict=rel.to_dict()
                rel_dict['rel_type']='-%s' % rel_dict['rel_type']
                result.append(rel_dict)
        return result
#    except Exception, err:
#       raise ApiError(None, 11101, err)

def search(params):
    search_string=params.get('string', "")
    tags_string=params.get('tags', "")
    entity_search=params.get('entity', "")

    if search_string!="" or tags_string!="":
        type=params.get("type", "")
        if type!="":
            try:
                entity_type=EntityType.objects.get(slug=type)
                if entity_type.do_index:
                    import erm.core.search_engine
                    search_engine=erm.core.search_engine.SearchEngine(type)
                    
                    queries=list()
                    
                    if search_string!="" and search_string!="*":
                        fields=list()
                        if params.get("fields", "")!="":
                            fields=params.get("fields", "").split(",")
                        queries.append({"fields":fields, "query":search_string})
                    
                    if tags_string!="":                        
                        or_chunks_list=tags_string.split("|")
                        bool_chunks_list=list()
                        for or_chunck in or_chunks_list:
                            found_one=False
                            if or_chunck!="":
                                and_chunks_list=or_chunck.split('&')
                                for and_chunk in and_chunks_list:
                                    if and_chunk!="":
                                        tags_split=and_chunk.split("{")
                                        tags=tags_split[0]
                                        schema=len(tags_split)>1 and tags_split[1][:-1] or "*"
                                        single_tags = tags.split(",")
                                                
                                        if not found_one:
                                            bool_chunks_list.append({"slug":single_tags[0], "schema":schema, "mode":"OR"})
                                            found_one=True
                                        else:
                                            bool_chunks_list.append({"slug":single_tags[0], "schema":schema, "mode":"AND"})
                                            
                                        for single_tag in single_tags[1:]:
                                            bool_chunks_list.append({"slug":single_tag, "schema":schema, "mode":"OR"})
                        if len(bool_chunks_list)>0:
                            queries.append({"fields":["tags"], "query":bool_chunks_list, "type":"tags"})

                    if len(queries):
                        page_size=int(params.get("page_size", 100))
                        page_num=max(int(params.get("page_num", 1))-1,0)
                        items_limit=params.get("items_limit", None)
                        if items_limit:
                            items_limit=int(items_limit)
                        mode=params.get("mode", "SHOULD")
                    
                        result=search_engine.search(queries, page_size, page_num, items_limit, mode)
                                        
                        if bool(int(params.get("get_entities", 0))):
                            entities_data=list()
                            for hit in result['docs']:
                                entity=Entity.objects.get(id=hit['entity_id']).to_dict(bool(int(params.get("compact", 1))), 
                                                          params.get("return_attrs", ""), 
                                                          params.get("return_tags", ""),
                                                          bool(int(params.get("rels", 0)))
                                                          )
                                entity['lucene_score']=hit['lucene_score']
                                entities_data.append(entity)
                            result['data']=entities_data
                        result['page']=result['page']+1
                        return result
                    else:
                        raise ApiError(None, "100", "No valid search passed" % type)
                else:
                    raise ApiError(None, "100", "Entity type %s can't be searched" % type)
            except Exception, err:
                raise ApiError(None, "100", "%s - %s" % (Exception, err))
        else:
            raise ApiError(None, "100", "An entity type is required")
        

    elif entity_search!="":
        #get_count=false
        items=dict((str(item.split(":")[0]),str(item.split(":")[1])) for item in entity_search.split(","))
        if items.has_key("query"):
            items["attributes"]=items["query"]
            del items["query"]
        for param in ["compact","return_tags","return_attrs"]:
            if items.has_key(param):
                params[param]=items[param]
                del items[param]
#        raise ApiError(None, 100, "%s" % items)
        
        return get_entity(items)
    return list()
    
def get_related_entities(params):
    from_entities=Entity.objects.filter(type__slug=params.get('entity_from_type'))
    res_entities=list()
    for from_entity in from_entities:
        to_entities=Entity.objects.filter(type__slug=params.get('entity_to_type'))
        to_entities=to_entities.filter(related_by__rel_type__slug=params.get('rel_type'))
        to_entities=to_entities.filter(related_by__entity_from=from_entity)
        entity_item=from_entity.to_dict()
        entity_item['relationship']=params.get('rel_type')
        entity_item['related']=[item.to_dict() for item in to_entities]
        res_entities.append(entity_item)
    return res_entities

def entity_connector_action(params):
    type_obj=EntityType.objects.get(slug=params.get('type'))
    united=params.get('united')
    target_obj_id=None
    if united:
        united_type,united_slug=united.split(":")
        entities=Entity.objects.filter(type__slug=united_type, slug=united_slug)
        if entities.count()==1 and entities[0].entity_union:
            united_entity=Entity.objects.filter(entity_union=entities[0].entity_union, type__slug=type_obj)
            if united_entity.count()==1:
                target_obj_id=united_entity[0].id
    if not target_obj_id and params.get('slug'):
        target_objs=get_entity({'slug':params.get('slug'), 'type':params.get('type')})
        if len(target_objs)==1:
            target_obj_id=target_objs[0].id
        elif len(target_objs)>1:
            raise ApiError(None, 101, "Too many entities selected")
    action=params.get('action')
    if action and action!="":
        return type_obj.repository.do_action(target_obj_id, action, params.get('parameters'))
    else:
        raise ApiError(None, 101, "No action passed")
        