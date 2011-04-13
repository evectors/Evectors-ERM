from erm.core.models import *
from erm.datamanager.models import *
from erm.lib.misc_utils import *
from erm.lib.api import ApiError, ERROR_CODES

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import EmptyQuerySet
from django.db import connection, DatabaseError, IntegrityError, transaction
from django.db.models import Q

import re

from erm.lib.logger import *

from urllib import unquote

#ERROR_CODES=dict()
#=====================generic or common errors=====================#
ERROR_CODES["1100"]="entity manager: Error management error"
ERROR_CODES["1101"]="entity manager: Generic error"
ERROR_CODES["1102"]="entity manager: Missing or empty parameter"
ERROR_CODES["1103"]="entity manager: Bad request format"
ERROR_CODES["1104"]="entity manager: Invalid slug"
#=====================get errors=====================#
ERROR_CODES["1200"]="entity manager: No object found" 
ERROR_CODES["1201"]="entity manager: Search by attributes requires type" 
#=====================add errors=====================#
ERROR_CODES["1300"]="entity manager: Object already existent"
ERROR_CODES["1311"]="entity manager: No entity type found"
ERROR_CODES["1312"]="entity manager: More entity types found"
ERROR_CODES["1313"]="entity manager: Repository error"
#=====================set errors=====================#
ERROR_CODES["1400"]="entity manager: Object missing" #200 can also be returned
ERROR_CODES["1401"]="entity manager: More objects found"
ERROR_CODES["1410"]="entity manager: Can't change"
#=====================delete errors=====================#
ERROR_CODES["1500"]="entity manager: Object missing" #200 can also be returned
ERROR_CODES["1501"]="entity manager: More objects found"
#=====================union errors=====================#
ERROR_CODES["1600"]="entity manager: Can't make unions with more entities of the same type" #200 can also be returned
ERROR_CODES["1601"]="entity manager: At least 2 entities are requested to build an union"
ERROR_CODES["1602"]="entity manager: Can't make unions of entities already belonging to different unions"
ERROR_CODES["1603"]="entity manager: PUT is not supported by entity_union"
ERROR_CODES["1604"]="entity manager: entity_type param is required"


#===============UNION=============#

def get_entity_union(params):
    try:
        if params.has_key('properties') and params.get('properties')=="1":
            obj=EntityUnion()
            return obj.properties()
        
        objects=EntityUnion.objects.select_related()
        if params.has_key('slug') and params.get('slug'):
            objects=objects.filter(name=params.get('slug'))
        if params.has_key('id') and params.get('id'):
            objects=objects.filter(id=params.get('id'))
        if params.has_key('entity') and params.get('entity'):
            slug,type=params.get('entity').split(":")
            entities=Entity.objects.filter(type__slug=type, slug=slug)
            if entities.count()==1 and entities[0].entity_union:
                objects=objects.filter(id=entities[0].entity_union.id)
            else:
                return list()
            
        objects_count=objects.count()
        if int(params.get('count', 0))==1:
            result = objects_count
        else:
            list_offset=max(int(params.get('offset', 0)),0)
            list_limit=max(int(params.get('limit', 20)),1)
        
            result = list(objects[list_offset: list_offset+list_limit])
            
            if params.has_key("attributes") and params.get('attributes'):
                if objects_count==1:
                    united_chunks=params.get('attributes').split("|")
                    types_opts=dict()
                    for item in united_chunks:
                        type, attributes=item.split("{")
                        types_opts[type]={"compact":False, "attributes":attributes[:-1], "tags":""}
                    result=objects[0].to_dict(False, types_opts=types_opts)
                elif objects_count>1:
                    raise ApiError(None, 1501, params.get('slug'))
            if params.has_key("tags") and params.get('tags'):
                if objects_count==1:
                    united_chunks=params.get('tags').split("|")
                    types_opts=dict()
                    for item in united_chunks:
                        type, tags=item.split("{")
                        attributes=""
                        if types_opts.has_key(type):
                            attributes=types_opts[type]["attributes"]
                        types_opts[type]={"compact":False, "attributes":attributes, "tags":tags[:-1]}
                    result=objects[0].to_dict(False, types_opts=types_opts)
                elif objects_count>1:
                    raise ApiError(None, 1501, params.get('slug'))
            
        return result
    except Exception, err:
       raise ApiError(None, 1101, err)

def add_entity_union(params):
    try:
        entities_list=params.get('entities',[])
        if len(entities_list)>1:
            entities_dict=dict()
            for entity in entities_list:
                type=entity.get("type")
                if not entities_dict.has_key(type):
                    entities_dict[type]=entity.get("slug")
                else:
                    raise ApiError(None, 1600, "%s: %s and %s" % (type, entities_dict[type], entity.get("slug")))
            if len(entities_dict)>1:
                unions=list()
                entities=list()
                for type, slug in entities_dict.items():
                    entity_type=EntityType.objects.get(slug=type)
                    entity=Entity.objects.get(type=entity_type, slug=slug)
                    union = entity.entity_union
                    entities.append(entity)
                    if union and not union in unions:
                        unions.append(union)
                if len(unions)==0:
                    slug=str(long(time.time() * 1e6))
                    union=EntityUnion(slug=slug, name=slug)
                    union.save();
                    unions.append(union)
                if len(unions)==1:
                    for entity in entities:
                        entity.entity_union=unions[0]
                        entity.save()
                    return unions[0]#{"slug":unions[0].slug, "id":unions[0].id, "entities":entities_dict}
                else:
                    raise ApiError(None, 1602)
            else:
                raise ApiError(None, 1601)
        else:
            raise ApiError(None, 1601)
    except Exception, err:
        raise ApiError(None, 100, err)

def set_entity_union(params):
    raise ApiError(None, 1603)

def del_entity_union(params):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        target_obj=get_entity_union(params)
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj_data=target_obj.to_dict()
            objects=Entity.objects.filter(entity_union=target_obj)
            for object in objects:
                object.entity_union=None
                object.save()
            target_obj.delete()
            #if entities of this type exist here we have to delete them
            return target_obj_data
        elif len(target_obj)==0:
            raise ApiError(None, 1500, params.get('slug'))
        else:
            raise ApiError(None, 1501, params.get('slug'))
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 1101, err)

#===============ENTITY TYPE=============#

def get_entity_type(params):
    try:
        if params.has_key('properties') and params.get('properties')=="1":
            obj=EntityType()
            return obj.properties()
        
        objects=EntityType.objects.select_related()
        if params.has_key('slug') and params.get('slug'):
            objects=objects.filter(slug=params.get('slug'))
        if params.has_key('id') and params.get('id'):
            objects=objects.filter(id=params.get('id'))
        #Insert here additional filtering?
    
        if int(params.get('count', 0))==1:
            return objects.count()
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
        
        result=list(objects[list_offset: list_offset+list_limit])
        
        return result
    except Exception, err:
       raise ApiError(None, 1101, err)

def add_entity_type(params):
    try:
        if params.has_key('slug') and params.get('slug'):
            old_object=EntityType.objects.filter(slug=params.get('slug'))
            if old_object.count()==0:
                #TRANSACTION START?
                slug = params.get('slug')
                if slug and slug!="" and slug == string_to_slug(slug):
                    name=params.get('name')
                    if not name or name=="":
                        name=slug
                    new_obj=EntityType(slug=slug, name=name, do_index=bool(params.get('do_index', True)))
                    new_obj.save()
                    repository_kind=params.get('repository_kind', 'T')
                    #create an instance in data manager repository
                    try:
                        repository=Repository(slug=new_obj.slug, name=new_obj.name, entity_type=new_obj, kind=repository_kind)#, entity_type_id=new_obj.id)
                        repository.save()
            
                        repository.set_fields(params.get('attributes', dict()))
                        repository.save(True)
                    except Exception, err:
                        new_obj.delete()
                        raise ApiError(None, 1313, err)

                   #TRANSACTION END?
                    return new_obj
                else:
                    raise ApiError(None, 1104, "'%s'" % slug)
            else:
                raise ApiError(None, 1300, params.get('slug'))
        else:
            raise ApiError(None, 1103, "slug")
    except Exception, err:
        raise ApiError(None, 1101, err)

def set_entity_type(params):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        target_obj=get_entity_type({'slug':params.get('slug'), 'id':params.get('id')})
        if len(target_obj)==1:
                #TRANSACTION START?
            target_obj=target_obj[0]

            try:
                repository = target_obj.repository
            except ObjectDoesNotExist:
                repository = Repository(slug=target_obj.slug, entity_type=target_obj)
                repository.save()
            if isinstance(repository, EmptyQuerySet):
                repository = Repository(slug=target_obj.slug, entity_type=target_obj)
                repository.save()
            repository.set_fields(params.get('attributes', dict()))
            repository.save(True)
            
            target_obj.name=params.get('name', target_obj.name)
            target_obj.do_index=bool(params.get('do_index', target_obj.do_index))
            target_obj.save()
                #TRANSACTION END?
            return target_obj
        elif len(target_obj)==0:
            raise ApiError(None, 1400)
        else:
            raise ApiError(None, 1401)
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 1101, err)

def del_entity_type(params):
    try:
        target_obj=get_entity_type({'slug':params.get('slug'), 'id':params.get('id')})
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj_data=target_obj.to_dict()
            target_obj.repository.delete()
            target_obj.delete()
            return target_obj_data
        elif len(target_obj)==0:
            raise ApiError(None, 1500, "slug: %s - id: %s" % (params.get('slug'), params.get('id')))
        else:
            raise ApiError(None, 1501, params.get('slug'))
    except Exception, err:
        raise ApiError(None, 1101, err)

#===============ENTITY TYPE ATTRIBUTE=============#    

def get_entity_type_attribute(params):
    try:
        if params.has_key('properties') and params.get('properties')=="1":
            obj=EntityType()
            return obj.properties()
        
        objects=EntityType.objects.select_related()
        if params.has_key('entity_name') and params.get('entity_name'):
            objects=objects.filter(name=params.get('entity_name'))
        if params.has_key('entity_id') and params.get('entity_id'):
            objects=objects.filter(id=params.get('entity_id'))
        #Insert here additional filtering?
        
        if len(object)==1:
            target_obj=objects[0]
            try:
                repository = target_obj.repository
            except ObjectDoesNotExist:
                repository = Repository(name=target_obj.name, entity_type=target_obj)
                repository.save()
            if isinstance(repository, EmptyQuerySet):
                repository = Repository(name=target_obj.name, entity_type=target_obj)
                repository.save()
            repository.set_fields(params.get('attributes', dict()))
            repository.save(True)
        else:
            return []
        if int(params.get('count', 0))==1:
            return objects.count()
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
        
        result=list(objects[list_offset: list_offset+list_limit])
        
#         if len(result)==0:
#             raise ApiError(None, 1200)
            
        return result
    except Exception, err:
       raise ApiError(None, 1101, err)

#===============ENTITY TAG SCHEMA=============#    

def get_entity_tag_schema(params):
    try:
        if params.has_key('properties') and params.get('properties')=="1":
            obj=EntityTagSchema()
            return obj.properties()
        
        objects=EntityTagSchema.objects.select_related()
        if params.has_key('slug') and params.get('slug'):
            objects=objects.filter(slug=params.get('slug'))
        if params.has_key('id') and params.get('id'):
            objects=objects.filter(id=params.get('id'))
        #Insert here additional filtering
    
        if int(params.get('count', 0))==1:
            return objects.count()
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
    
        result=list(objects[list_offset: list_offset+list_limit])
        
        return result
    except Exception, err:
       raise ApiError(None, 1101, err)

def add_entity_tag_schema(params):
    try:
        if params.has_key('slug') and params.get('slug'):
            old_object=EntityTagSchema.objects.filter(slug=params.get('slug'))
            if old_object.count()==0:
                slug = params.get('slug')
                if slug and slug!="" and slug == string_to_slug(slug):
                    name=params.get('name')
                    if not name or name=="":
                        name=slug
                    new_obj=EntityTagSchema(slug=slug, 
                                            name=name, 
                                            status=params.get('status', "A"))
                    new_obj.save()
                    return new_obj
                else:
                    raise ApiError(None, 1104, "'%s'" % slug)
            else:
                raise ApiError(None, 1300, params.get('slug'))
        else:
            raise ApiError(None, 1103, "slug")
    except Exception, err:
        raise ApiError(None, 1101, err)

def set_entity_tag_schema(params):
    try:
        target_obj=get_entity_tag_schema({'slug':params.get('slug'), 'id':params.get('id')})
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj.name=params.get('name', target_obj.name)
            target_obj.status=params.get('status', target_obj.status)
            target_obj.save()
            return target_obj
        elif len(target_obj)==0:
            raise ApiError(None, 1400, params.get('slug'))
        else:
            raise ApiError(None, 1401, params.get('slug'))
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 1101, err)

def del_entity_tag_schema(params): #id=None, slug=None):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        old_object=get_entity_tag_schema(params)#{'slug':slug, 'id':id})
        if len(old_object)==1:
            old_object_data=old_object[0].to_dict()
            old_object[0].delete()
            return old_object_data
        elif len(old_object)==0:
            raise ApiError(None, 1500, params)
        else:
            raise ApiError(None, 1501, params)
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 1101, err)

#===============ENTITY TAG=============#    

def get_entity_tag(params):

    if params.has_key('entity_type'):
        try:        
            from django.db import connection
            
            query="""SELECT object_tag_id, ets.slug, COUNT(object_tag_id) AS entities_count 
                FROM core_entitytagcorrelation AS etc 
                INNER JOIN core_entity AS e ON e.id=etc.object_id 
                INNER JOIN core_entitytagschema AS ets ON ets.id=etc.object_tag_schema_id 
                WHERE e.type_id=%s %s 
                GROUP BY etc.object_tag_schema_id, etc.object_tag_id 
                ORDER BY entities_count DESC 
                LIMIT %s;"""
                #% (entity_type_id, wheres_string, limit)
            
            entity_type_id=EntityType.objects.get(slug=params.get('entity_type')).id
            wheres_string=""
            
            schemas=params.get('schema')
            schemas_wheres=list()
            schemas_wheres_not=list()
            if schemas and schemas!="":
                schemas_list=schemas.split(",")
                schema_where="%s AND etc.object_tag_schema_id%s=%s" 
                not_string=""
                for _schema in  schemas_list:
                    if _schema[0]=="!":
                        not_string="!"
                        schemas_wheres_not.append(str(EntityTagSchema.objects.get(slug=unquote(_schema[1:])).id))
                    else:
                        schemas_wheres.append(str(EntityTagSchema.objects.get(slug=unquote(_schema)).id))
            
            if len(schemas_wheres):
                wheres_string="%s AND etc.object_tag_schema_id IN (%s)" % (wheres_string, ",".join(schemas_wheres))
            if len(schemas_wheres_not):
                wheres_string="%s AND etc.object_tag_schema_id NOT IN (%s)" % (wheres_string, ",".join(schemas_wheres_not))
            limit=params.get('limit', 100)
            
            query=query %  (entity_type_id, wheres_string, limit)
            
            if params.get('query'):
                return ' '.join(query.split())
            
            cursor = connection.cursor()
            cursor.execute(' '.join(query.split()))
            all_items=cursor.fetchall()
            fields = ('tag','schema', 'entities_count')
            items_dict = [dict(zip(fields, r)) for r in all_items]
            
            for tag_item in items_dict:
                tag_item['related']=list()

            return items_dict
        
        except Exception, err:
           raise ApiError(None, 1101, err)
    else:
        raise ApiError(None, 1604, None)

def add_entity_tag(params):
    try:
        if params.has_key('slug') and params.get('slug') and params.has_key('name') and params.get('name'):
            slug = params.get('slug')
            name = params.get('name')
            
            if slug and slug!="" and slug == string_to_slug(slug):
            
                old_object=EntityTag.objects.filter(slug=slug)
                if old_object.count()==0:
                    old_object=EntityTag.objects.filter(name=name)
                    if old_object.count()==0:
                        new_obj=EntityTag(name=name, slug=slug, status=params.get('status', "A"))
                        new_obj.save()
                        return new_obj
                    else:
                        raise ApiError(None, 1300, name)
                else:
                    raise ApiError(None, 1300, slug)
            else:
                raise ApiError(None, 1104, "'%s'" % slug)
        else:
            raise ApiError(None, 1102, "name")
    except Exception, err:
        raise ApiError(None, 1101, err)

def set_entity_tag(params):
    try:
        target_obj=get_entity_tag({'id':params.get('id'), 'slug':params.get('slug')})
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj.status=params.get('status', target_obj.status)
            target_obj.save()
            return target_obj
        elif len(target_obj)==0:
            raise ApiError(None, 1400)
        else:
            raise ApiError(None, 1401)
    except Exception, err:
        raise ApiError(None, 1101, err)

def del_entity_tag(params): #id=None, slug=None):
    try:
        old_object=get_entity_tag(params)#{'slug':slug, 'id':id})
        if len(old_object)==1:
            old_object_data=old_object[0].to_dict()
            old_object[0].delete()
            return old_object_data
        elif len(old_object)==0:
            raise ApiError(None, 1500, params)
        else:
            raise ApiError(None, 1501, params)
    except Exception, err:
        raise ApiError(None, 1101, err)

#===============ENTITY=============#    
            
def get_entity(params):
    try:
        real_params=dict([key, value] for key, value in params.items() if (value!=None and value!=""))
        
        real_keys=set(real_params.keys())
        
        if real_params.get('properties', "0")=="1":
            return Entity().properties()
        
        objects=Entity.objects.select_related()
        
        type_ids=list()

        if real_params.has_key('type') and real_params.get('type'):
            type_slug_list=str(real_params.get('type')).split(',')
            type_ids=[str(item['id']) for item in EntityType.objects.filter(slug__in=type_slug_list).values('id')]

        if real_params.has_key('type_id') and real_params.get('type_id'):
            type_ids=str(real_params.get('type_id')).split(',')

        if len(type_ids)==0:
            return list()

        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
        
#===========================>Specialized query: filtering on tag, ordered by tag weight            
        fast_tags_sort_params=set(['type', 'sort', 'limit', 'offset', 'jindent', 'total_count', 'compact', 'return_tags', 'return_attrs'])
        fl_do_fast_tags_sort=False
        if len(real_keys.difference(fast_tags_sort_params))==0 and ('sort' in real_params) and len(real_params['sort'].split(','))==1 and ("tag:" in real_params['sort']):
            
            fl_do_fast_tags_sort=True
            sort_tag=real_params['sort'].split(":")[1]
            sort_schema=""
            if sort_tag.find("{")>=0:
                sort_tag, sort_schema=sort_tag.split('{')
                sort_schema=sort_schema[:-1]
            
            if sort_tag[:1]=='-':
                direction='DESC'
                sort_tag=sort_tag[1:]
            else:
                direction='ASC'
            
            tags_filter=real_params.get('tags', '')
            if tags_filter!="":
                if ("&" in tags_filter) or ("!" in tags_filter):
                    fl_do_fast_tags_sort=False
                else:
                    tags_blocks=list()
                    for tag_block_string in real_params.get('tags', '').split('|'):
                        if tag_block_string!="":
                            block_tag = tag_block_string
                            block_schema = ""
                            if "{" in tag_block_string:
                                block_tag, block_schema=tag_block_string.split('{')
                                block_schema=block_schema[:-1]
                            tags_blocks.append({"tag":block_tag, "schema":block_schema})
                    fl_do_fast_tags_sort = not (len(tags_blocks)>1 or (sort_tag not in tags_blocks[0]['tag'].split(',')) or (sort_schema!="" and  tags_blocks[0]['schema']!="" and sort_schema!=tags_blocks[0]['schema']))

                    if sort_schema=="" and  tags_blocks[0]['schema']!="":
                        sort_schema=tags_blocks[0]['schema']

        if fl_do_fast_tags_sort:
            
            wheres_list=list()

            if len(type_ids)==1:
                wheres_list.append("core_entitytagcorrelation.object_type_id = %s" % type_ids[0])
            elif len(type_ids)>1:
                wheres_list.append("core_entitytagcorrelation.object_type_id IN (%s)" % ','.join(type_ids))
            
            if sort_tag!="":
                wheres_list.append("core_entitytagcorrelation.object_tag_id = '%s'" % sort_tag)
            
            if sort_schema!="":
                wheres_list.append("core_entitytagcorrelation.object_tag_schema_id = (SELECT id FROM core_entitytagschema WHERE core_entitytagschema.slug='%s')" % unquote(sort_schema))

            core_selection="FROM core_entitytagcorrelation WHERE %s" % " AND ".join(wheres_list)
            
            if int(real_params.get('total_count', 0))==1 or int(real_params.get('count', 0))==1:
                count_query = "SELECT COUNT(*) %s" % core_selection
                cursor = connection.cursor()
                cursor.execute(count_query)
                total_items=int(cursor.fetchone()[0])
                if int(real_params.get('count', 0))==1:
                    return total_items
                
            global_query="SELECT object_id %s ORDER BY core_entitytagcorrelation.weight %s LIMIT %s,%s" % (core_selection, direction, list_offset, list_limit)

            cursor = connection.cursor()
            cursor.execute(global_query)
            ids_list=list(cursor_item[0] for cursor_item in cursor.fetchall())
            objects=objects.filter(id__in=ids_list)
#===========================>Good'ol generic stuff
        else:
 
            if len(type_ids)==1:
                objects=objects.filter(type__id=type_ids[0])
            elif len(type_ids)>1:
                objects=objects.filter(type__id__in=type_ids)
            else:
                return list()

            united=params.get('united')
            if united:
                united_type,united_slug=united.split(":")
                united_entities=Entity.objects.filter(type__slug=united_type, slug=united_slug)
                if united_entities.count()==1 and united_entities[0].entity_union:
                    objects=objects.filter(entity_union=united_entities[0].entity_union)
                else:
                    return list()
            
            if params.has_key('id') and params.get('id'):
                ids_list=str(params.get('id')).split(",")
                if len(ids_list)==1:
                    objects=objects.filter(id=ids_list[0])
                elif len(ids_list)>1:
                    objects=objects.filter(id__in=ids_list)
    
            objects=build_text_search(objects, "slug", params)
            
            objects=build_text_search(objects, "uri", params)
    
            objects=build_text_search(objects, "name", params)
    
            objects=build_date_search(objects, "creation_date", params)
    
            objects=build_date_search(objects, "modification_date", params)
    
            objects=build_date_search(objects, "custom_date", params)
                        
            #RELATIONSHIPS FILTERING
            if params.get('rel', "")!="":
                or_chunks_list=params.get('rel', "").split("||")
                chunks_list=list()
                for item in or_chunks_list:
                     if item.find("&&")<0:
                         chunks_list.append({"match":item, "mode":"or"})
                     else:
                         for and_item in item.split("&&"):
                             chunks_list.append({"match":and_item, "mode":"and"})
                
                qset_rel = Q()
                             
                for chunk in chunks_list:
                    
                    if chunk["match"].find("<")>0:
                        chunk_match=chunk["match"]
                        chunk_match=chunk_match.replace("<", ">")
                        sign='-'
                        if chunk_match[0]=="+":
                            chunk_match=chunk_match[1:]
                        elif chunk_match=='-':
                            chunk_match=chunk_match[1:]
                            sign='+'
                        chunk_match="%s%s" % (sign, chunk_match)
                        chunk["match"]=chunk_match
                    
                    qset_rel_inner = Q()
                    rel_list=chunk["match"].split('>')
                    #return rel_list
                    rel, rel_tags=rel_list[0].split('[')
                    if rel_tags!="":
                        rel_tags=rel_tags[:-1]
                    entity=rel_list[1].split("{")
                    entity_type=""
                    if len(entity)>1:
                        entity_type=entity[1][:-1]
                    entity=entity[0]
                    if entity!="":
                        entity=entity.split(',')
                    
                    if rel=="":
                        if entity!="":
                            qset_rel_inner&=(Q(related_to__entity_to__slug__in=entity) | Q(related_by__entity_from__slug__in=entity))
                    elif rel[0]=='-':
                        if len(rel)>1:
                            qset_rel_inner&=Q(related_by__rel_type__slug=rel[1:])
                        if entity!="":
                            qset_rel_inner&=Q(related_by__entity_from__slug__in=entity)
                        if entity_type!="":
                            qset_rel_inner&=Q(related_by__entity_from__type__slug=entity_type)
                    else:
                        
                        if rel[0]=="+":
                            rel=rel[1:]
                        
                        if len(rel)>0:
                            qset_rel_inner&=Q(related_to__rel_type__slug=rel)
                    
                        if entity!="":
                            qset_rel_inner&=Q(related_to__entity_to__slug__in=entity)
                    
                        if entity_type!="":
                            qset_rel_inner&=Q(related_to__entity_to__type__slug=entity_type)
                    
                    
                
                    if chunk["mode"]=="and":
                        qset_rel&=qset_rel_inner
                    else:
                        qset_rel|=qset_rel_inner
                    
                #return dir(qset)
                objects=objects.filter(qset_rel).distinct()
                
#======================>TAGS FILTERING
            if params.get('tags', "")!="":
                or_chunks_list=params.get('tags', "").split("||")
                chunks_list=list()
                schemas_dict=dict()
                for item in or_chunks_list:
                     if item.find("&&")<0:
                         chunks_list.append({"match":item, "mode":"or"})
                     else:
                         for and_item in item.split("&&"):
                             chunks_list.append({"match":and_item, "mode":"and"})
                qset = Q()
                for chunk in chunks_list:
                    all_negated=False
                    schema_negated=False
                    
                    tag_key=""
                    
                    qset_inner = Q()
                    
                    tags_split=chunk["match"].split("{")
                    
                    tags=tags_split[0]
                    
                    if tags[:1]=="!":
                        all_negated=True
                        tags=tags[1:]
                    
                    schema=len(tags_split)>1 and tags_split[1][:-1] or ""
                    
                    if schema[:1]=="!":
                        schema_negated=True
                        schema=schema[1:]
                    
                    if schema!='' and not schema in schemas_dict:
                        schemas_dict[schema]=EntityTagSchema.objects.get(slug=unquote(schema)).id
                        
                    tags_re_list=re.split('((?:[^",]|(?:"(?:\\{2}|\\"|[^"])*?"))*)', tags)
                    slugs_list=list()
                    for item in tags_re_list:
                        if item.strip()!='' and item.strip()!=',':
                            slugs_list.append(item.strip())
    #                        slugs_list.append(string_to_slug(item.strip()))
                    #return slugs_list, schema
                    if len(slugs_list):
                        if len(slugs_list)==1:
                            qset_inner |= Q(tags__slug=slugs_list[0])
                        else:
                            qset_inner |= Q(tags__slug__in=slugs_list)
                    if schema != '':
                        if not schema_negated:
                            qset_inner &= Q(entitytagcorrelation__object_tag_schema__id=schemas_dict[unquote(schema)])
                        else:
                            qset_inner &= ~Q(entitytagcorrelation__object_tag_schema__id=schemas_dict[unquote(schema)])
                    
                    if all_negated:
                        qset_inner = ~qset_inner
                            
                    if chunk["mode"]=="and":
                        qset&=qset_inner
                    else:
                        qset|=qset_inner
                objects=objects.filter(qset)
                    
            if params.has_key('attributes') and params.get('attributes'):
                entity_type=params.get('type')
                if entity_type and entity_type!="":
                    entities_list=Repository.objects.get(entity_type__slug=entity_type).search(params.get('attributes'))
                    entities_list=[entity_item['entity_id'] for entity_item in entities_list]
                    objects=objects.filter(id__in=entities_list)
    
                else:
                    raise ApiError(None, 1201, err)
            else:
                pass
    
            _NE=params.get('NE')
            _SW=params.get('SW')
            
            _center=params.get('center')
            _radius=params.get('radius')
            
            if (_center and _radius) or (_NE and _SW):
                if (_center and _radius):
                    _center_lat, _center_lon = _center.split(',')
                    _center_lat=float(_center_lat)
                    _center_lon=float(_center_lon)
                    
                    _length_conversion=1
                    if _radius.lower().endswith('mi'):
                        _length_conversion=1.609
                    
                    _radius_num=''
                    for char in _radius:
                        if char.isdigit():
                            _radius_num+=char
                    
                    _radius_num=float(_radius_num)*_length_conversion
                    
                    _delta_degrees=0.008983153*_radius_num
                    
                    _north=_center_lat+_delta_degrees
                    _south=_center_lat-_delta_degrees
                    _west =_center_lon-_delta_degrees
                    _east =_center_lon+_delta_degrees
                
                else:
                    _north, _east=_NE.split(',')
                    _south, _west=_SW.split(',')
                    _north=float(_north)
                    _south=float(_south)
                    _east=float(_east)
                    _west=float(_west)
                objects=objects.filter(latitude__isnull=False)
                objects=objects.filter(longitude__isnull=False)
                objects=objects.filter(latitude__range=(_south, _north))
                objects=objects.filter(longitude__range=(_west, _east))
    
            result=list()
    
            if params.get('distinct', '')!='':
                return list ( objects.values(params.get('distinct')).distinct());
    
            if int(params.get('count', 0))==1:
                return objects.count()
            
            if params.get('sort', "")!="":
                order_by=params.get('sort', "").split(',')
                for sortby in order_by:
                    sign=""
                    if sortby[:1]=='-':
                        sign='-'
                        sortby=sortby[1:]
                    if sortby.startswith('tag:'):
                        tag=sortby.split(":")[1]
                        schema=""
                        if tag.find("{")>=0:
                            tag_list=tag.split('{')
                            tag=tag_list[0]
                            schema=tag_list[1][:-1]
                        
                        subquery_wheres=["`core_entitytagcorrelation`.`object_id`=`core_entity`.`id`"]
                        tag_select=""
                        if tag!="" or schema!="":
                            if tag!="":
                                subquery_wheres.append("core_entitytagcorrelation.object_tag_id='%s'" % tag)
                                #subquery_wheres.append("core_entitytagcorrelation.object_tag_id='%s'" % tag)
                                #objects=objects.filter(tags__slug=tag)
                                tag_select=tag
                            if schema!="":
                                schema_id=None
                                try:
                                    schema_id=EntityTagSchema.objects.get(slug=unquote(schema)).id
                                except:
                                    pass
                                try:
                                    subquery_wheres.append("core_entitytagcorrelation.object_tag_schema_id='%s'" % schema_id)
                                    #objects=objects.filter(entitytagcorrelation__object_tag_schema__slug=schema)
                                except:
                                    pass
                                if tag_select!="":  
                                    tag_select="%s_%s" % (tag_select, unquote(schema))
                                else:
                                    tag_select=unquote(schema)
                            subquery_select='''SELECT DISTINCT core_entitytagcorrelation.weight 
                            FROM core_entitytagcorrelation WHERE %s  
                            GROUP BY `core_entity`.`id`''' % (" AND ".join(subquery_wheres, ))
                            
                            tag_select="tag_sort_by_field" #% tag_select
                            subquery_order="%s%s" % (sign, tag_select)
                            
                            objects=objects.extra(select={tag_select: subquery_select})
                            
    ####################UNDOCUMENTED CALL, see http://stackoverflow.com/questions/327807/django-equivalent-for-count-and-group-by ###############################
                            objects.query.group_by = ['`core_entity`.`id`']
    #############################################################################################################################################################                        
    
                            objects=objects.order_by(subquery_order)
                            
                    else:
                        objects=objects.order_by("%s%s" % (sign, sortby))

            if int(params.get('paged', 0))==1 or int(params.get('total_count', 0))==1:
                total_items = objects.count()
    
        if int(params.get('paged', 0))==1:
            page_size=int(params.get('page_size', 100))
            page_num=int(params.get('page_num', 0))
            if total_items>=page_size*page_num:
                list_offset=page_size*page_num
                list_limit=page_size
                items=list(objects[list_offset: list_offset+list_limit])
                items_dicts=[object.to_dict(compact=bool(params.get('compact', 1))) for object in items]
                result={"count":total_items, "page":page_num, "data":items_dicts}
            else:
                result = list()
        else:
            list_offset=max(int(params.get('offset', 0)),0)
            list_limit=max(int(params.get('limit', 20)),1)
        
            if params.has_key('step') and params.get('step')!="":
                result=list(objects[list_offset: list_offset+list_limit:int(params.get('step',1))])
            else:
                result=list(objects[list_offset: list_offset+list_limit])
                
            if int(params.get('total_count', 0))==1:
                result={"count":total_items, "data":[item.to_dict(bool(int(params.get('compact', 1))), params.get('return_attrs', ""), params.get('return_tags', "") ,params.get('rels', "")) for item in result]}            
                
        return result
    except Exception, err:
       raise ApiError(None, 1101, err)

def add_entity(params):
    if params.get('slug',"")!="":
        slug = params.get('slug')
        name = params.get('name')
       
        if slug and slug!="" and slug == string_to_slug(slug):
            
            if not name or name=="":
                name=slug
                
            obj_type=None
            if params.has_key('type') and params.get('type'):
                try:
                    obj_type=EntityType.objects.get(slug=params.get('type'))
                except:
                    pass
            if not obj_type:
                try:
                    obj_type=EntityType.objects.get(id=params.get('type_id'))
                except:
                    pass

            _longitude=None
            _latitude=None
            
            try:
                _longitude=float(params.get('longitude'))
            except Exception, err:
                pass
            
            try:
                _latitude=float(params.get('latitude'))
            except Exception, err:
                pass
            
            if obj_type:
                fl_double = False
                fl_force = int(params.get('force','0')==1)
                slug_progressive=""
                
                while (not fl_double) or fl_force:
                    inner_slug=slug
                    if slug_progressive!="":
                        inner_slug = "%s-%s" % (inner_slug, slug_progressive)
                    try:
                        #TRANSACTION?
                        entity_union=None                        
                        new_obj=Entity(
                                       slug=inner_slug, 
                                       status=params.get('status', "A"), 
                                       type=obj_type, 
                                       entity_union=entity_union,
                                       name=name,
                                       uri=params.get('uri'),
                                       longitude=_longitude,
                                       latitude=_latitude
                                       )

                        passed_custom_date=params.get('custom_date')
                        if passed_custom_date and passed_custom_date!=None and passed_custom_date!="0":
                            new_obj.custom_date=datetime.datetime.fromtimestamp(float(passed_custom_date))
                        else:
                            new_obj.custom_date=None
                            
                        if params.get('password'):
                            new_obj.password=params.get('password')
    #                    raise ApiError(None, 1101, "%s" % params.get('status', "B")) 
                        new_obj.save()
                        
                        if new_obj.type.repository:
                            new_obj.type.repository.add_record(new_obj.id, params.get('attributes', dict()))
                        
                        new_obj.set_tags(params.get('tags'))
                            
                        #TRANSACTION END?
                        if not params.get('skip_return_data') or params.get('skip_return_data')==0:
                            return new_obj
                        else:
                            return dict()
                        
                    except IntegrityError, err:
                        fl_double=True
                        if fl_force:
                            progr_num=1
                            similar_slugs=Entity.objects.filter(slug__istartswith=slug, type=obj_type).values('slug')
                            slugs_list=[old_slug["slug"] for old_slug in similar_slugs]
                            while ("%s-%s" % (slug, ("%s" % progr_num).zfill(SLUG_PROGRESSIVE_LENGTH))) in slugs_list:
                                progr_num+=1
                            slug_progressive = ("%s" % progr_num).zfill(SLUG_PROGRESSIVE_LENGTH)
                        else:
                            raise ApiError(None, 1300, "%s of type %s (%s)" % (slug, obj_type.name, Entity.objects.filter(slug=slug, type=obj_type)[0].id))
                    except Exception, err:
                        raise ApiError(None, 1101, "%s-%s" % (Exception, err))
            else:
                raise ApiError(None, 1311, "entity_type slug='%s', entity_type id='%s'" % (params.get('type'), params.get('type_id')))
        else:
            raise ApiError(None, 1104, "'%s' -> '%s'" % (slug, string_to_slug(slug)))
    else:
        raise ApiError(None, 1102, "slug")

def set_entity(params):
    target_obj=get_entity({'id':params.get('id'), 
                           'slug':params.get('slug'), 
                           'type_id':params.get('type_id'), 
                           'type':params.get('type'),
                           'united':params.get('united')})
    if len(target_obj)==1:
        try:
            #TRANSACTION?
            target_obj=target_obj[0]
            
            union_obj=None
            old_union=target_obj.entity_union
            
            if params.has_key('union') and params.get('union'):
                try:
                    union_obj=EntityUnion.objects.get(slug=params.get('union'))
                except:
                    pass
            if not union_obj:
                if params.has_key('union_id') and params.get('union_id'):
                    try:
                        union_obj=EntityUnion.objects.get(id=params.get('union_id'))
                    except:
                        union_obj=target_obj.entity_union
                else:
                    union_obj=target_obj.entity_union
            target_obj.entity_union=union_obj

            if old_union and old_union!=union_obj:       
                if Entity.objects.filter(entity_union=old_union).count()==0:
                    old_union.delete()
            
            
            target_obj.status=params.get('status', target_obj.status)
            target_obj.name=params.get('name', target_obj.name)
            target_obj.password=params.get('password', target_obj.password)
            target_obj.uri=params.get('uri', target_obj.uri)
            
            _longitude=target_obj.longitude
            _latitude=target_obj.latitude
            
            try:
                _longitude=float(params.get('longitude', _longitude))
            except Exception, err:
                pass
            
            try:
                _latitude=float(params.get('latitude', _latitude))
            except Exception, err:
                pass

            target_obj.latitude=_latitude
            target_obj.longitude=_longitude

            if params.has_key('custom_date'):
                if params.get('custom_date'):
                    target_obj.custom_date=datetime.datetime.fromtimestamp(float(params.get('custom_date')))
                else:
                    target_obj.custom_date=None
            #manage tags here
            target_obj.save()
            
            if target_obj.type.repository:
                target_obj.type.repository.update_record(target_obj.id, params.get('attributes', dict()))

            target_obj.set_tags(params.get('tags'))
            #TRANSACTION END?
            if not params.get('skip_return_data') or params.get('skip_return_data')==0:
                return target_obj
            else:
                return dict()
        except Exception, err:
            raise ApiError(None, 1101, err)
    elif len(target_obj)==0:
        raise ApiError(None, 1400)
    else:
        raise ApiError(None, 1401)

def del_entity(params):
    old_object=get_entity(params)
    if len(old_object)==1:
        try:
            old_object_data=old_object[0].to_dict(False, "*", "*", True)
            old_object[0].type.repository.delete_record(old_object[0].id)
            if params.get('dump')!="":
                try:
                    pickleToFile("%s_%s_%s" % (old_object[0].id, old_object[0].slug, old_object[0].type.slug),old_object_data, DELETED_ENTITIES_DUMP_DIR)
                except Exception, err:
                    pass
            old_object[0].delete()
            return old_object_data
        except Exception, err:
            raise ApiError(None, 1101, err)
    elif len(old_object)==0:
        raise ApiError(None, 1500, params)
    else:
        raise ApiError(None, 1501, params)

#===================================================================

