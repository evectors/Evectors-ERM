from erm.core.models import *
from erm.datamanager.models import *
from erm.lib.misc_utils import *
from erm.lib.api import ApiError, ERROR_CODES
from erm.core.entity_manager import *

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import EmptyQuerySet
from django.db import connection, DatabaseError, IntegrityError, transaction

from urllib import unquote

from erm.lib.tags_utils import build_tags_Q_filter

#ERROR_CODES=dict()
#=====================generic or common errors=====================#
ERROR_CODES["11100"]="relationship manager: Error management error"
ERROR_CODES["11101"]="relationship manager: Generic error"
ERROR_CODES["11102"]="relationship manager: Missing or empty parameter"
ERROR_CODES["11103"]="relationship manager: Bad request format"
ERROR_CODES["11104"]="relationship manager: Invalid slug"
#=====================get errors=====================#
ERROR_CODES["11200"]="relationship manager: No object found" 
ERROR_CODES["11201"]="relationship manager: Search by attributes requires either type or type name" 
#=====================add errors=====================#
ERROR_CODES["11300"]="relationship manager: Object already existent"
ERROR_CODES["11311"]="relationship manager: No entity type found"
ERROR_CODES["11312"]="relationship manager: More entity types found"
ERROR_CODES["11313"]="relationship manager: Missing object"
ERROR_CODES["11314"]="relationship manager: Relationship exists"
ERROR_CODES["11315"]="relationship manager: Relationship not allowed"
ERROR_CODES["11316"]="relationship manager: Relationship not completely defined"
#=====================set errors=====================#
ERROR_CODES["11400"]="relationship manager: Object missing" #200 can also be returned
ERROR_CODES["11401"]="relationship manager: More objects found"
ERROR_CODES["11410"]="relationship manager: Can't change"
#=====================delete errors=====================#
ERROR_CODES["11500"]="relationship manager: Object missing" #200 can also be returned
ERROR_CODES["11501"]="relationship manager: More objects found"
ERROR_CODES["11502"]="relationship manager: Can't delete rel_type_allowed, some relationships of that type already exist"
#
##===============RELATIONSHIP TYPE=============#

def get_rel_type(params, api_obj=None):
    try:
        if params.has_key('c') and params.get('properties')=="1":
            obj=RelationshipType()
            return obj.properties()
        objects=RelationshipType.objects.all()
        if params.has_key('name') and params.get('name'):
            objects=objects.filter(name=params.get('name'))
        if params.has_key('slug') and params.get('slug'):
            objects=objects.filter(slug=params.get('slug'))
        if params.has_key('id') and params.get('id'):
            objects=objects.filter(id=params.get('id'))
        #Insert here additional filtering?
    
        if int(params.get('count', 0))==1:
            objects_count = objects.count()
            if api_obj is not None:
                api_obj.count=objects_count
            return objects_count
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
        
        result=list(objects[list_offset: list_offset+list_limit])
        
        return result
    except Exception, err:
       raise ApiError(None, 11101, err)

def add_rel_type(params):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        if params.has_key('slug') and params.get('slug'):
            slug = params.get('slug')
            name = params.get('name')
            
            if slug and slug!="" and slug == string_to_slug(slug):
                if not name or name=="":
                    name=slug
                name_reverse=params.get('name_reverse')
                if not name_reverse or name_reverse=="":
                    name_reverse="the reverse of %s" % name
                old_object=RelationshipType.objects.filter(slug=slug)
                if old_object.count()==0:
                    #TRANSACTION START?

                    status=params.get('status', 'A').upper()

                    new_obj=RelationshipType(slug=slug, 
                                             name=name, 
                                             name_reverse=name_reverse, 
                                             reciprocated=bool(params.get('reciprocated', False)),
                                             status=status,
                                             )
                    new_obj.save()
                    return new_obj
                else:
                    raise ApiError(None, 11300, "'%s'" % slug)
                   #TRANSACTION END?
            else:
                raise ApiError(None, 11104, "'%s'" % slug)
        else:
            raise ApiError(None, 11103, "name")
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

def set_rel_type(params):
    try:
        target_obj=get_rel_type({'slug':params.get('slug'), 'id':params.get('id')})
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj.name=params.get('name', target_obj.name)
            target_obj.name_reverse=params.get('name_reverse', target_obj.name_reverse)
            target_obj.reciprocated=params.get('reciprocated', target_obj.reciprocated)
            target_obj.status=params.get('status', target_obj.status).upper()
            target_obj.save()
            return target_obj
        elif len(target_obj)==0:
            raise ApiError(None, 11400)
        else:
            raise ApiError(None, 11401)
    except Exception, err:
        raise ApiError(None, 11101, err)

def del_rel_type(params):
    try:
        target_obj=get_rel_type({'slug':params.get('slug'), 'id':params.get('id')})
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj_data=target_obj.to_dict()
            #if entities of this type exist here we have to delete them
            target_obj.delete()
            return target_obj_data
        elif len(target_obj)==0:
            raise ApiError(None, 11500, name)
        else:
            raise ApiError(None, 11501, name)
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)
    
##===============RELATIONSHIP TYPE ALLOWED=============#

def get_rel_type_allowed(params, api_obj=None):
    try:
        if params.has_key('properties') and params.get('properties')=="1":
            obj=RelationshipTypeAllowed()
            return obj.properties()
        
#----------------------------------old naming compatibility -------------------------------------#
        if (not params.get('entity_from_type')):
            params['entity_from_type']=params.get('entity_type_from');
        if (not params.get('entity_to_type')):
            params['entity_to_type']=params.get('entity_type_to');
#-------------------------------------------------------------------------------------------------#

        objects=RelationshipTypeAllowed.objects.all()
        
        try:
            entity_from_type=get_entity_type({'slug':params.get('entity_from_type')})
            if len(entity_from_type)==1:
                objects=objects.filter(entity_type_from__id=entity_from_type[0].id)
        except:
            pass
        
        try:
            entity_to_type=get_entity_type({'slug':params.get('entity_to_type')})
            if len(entity_to_type)==1:
                objects=objects.filter(entity_type_to__id=entity_to_type[0].id)
        except:
            pass
        
        try:
            rel_type=get_rel_type({'slug':params.get('rel_type')})
            if len(rel_type)==1:
                objects=objects.filter(rel_type__id=rel_type[0].id)
        except:
            pass
        
        if int(params.get('count', 0))==1:
            objects_count = objects.count()
            if api_obj is not None:
                api_obj.count=objects_count
            return objects_count
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
        
        result=list(objects[list_offset: list_offset+list_limit])
        
        return result
    except Exception, err:
       raise ApiError(None, 11101, err)

def add_rel_type_allowed(params):
    try:
#----------------------------------old naming compatibility -------------------------------------#
        if (not params.get('entity_from_type')):
            params['entity_from_type']=params.get('entity_type_from');
        if (not params.get('entity_to_type')):
            params['entity_to_type']=params.get('entity_type_to');
#-------------------------------------------------------------------------------------------------#

        rel_type=None
        entity_from_type=None
        entity_to_type=None
        
        try:
            pass
        except:
            try:
                pass
            except:
                pass

        try:
            rel_type=get_rel_type({'slug':params.get('rel_type')})[0]
        except:
            pass
        
        try:
            entity_from_type=get_entity_type({'slug':params.get('entity_from_type')})[0]
        except:
            pass

        try:
            entity_to_type=get_entity_type({'slug':params.get('entity_to_type')})[0]
        except:
            pass
                
        if rel_type and entity_from_type and entity_to_type:
            old_object=RelationshipTypeAllowed.objects.filter(rel_type=rel_type, 
                                                              entity_type_from=entity_from_type, 
                                                              entity_type_to=entity_to_type)
            if old_object.count()==0:
                new_obj=RelationshipTypeAllowed(rel_type=rel_type, 
                                                entity_type_from=entity_from_type, 
                                                entity_type_to=entity_to_type)
                new_obj.save()
                
                return new_obj
            else:
                raise ApiError(None, 11300, "%s" % params)
        else:
            raise ApiError(None, 11103, "%s" % params)
    except Exception, err:
        raise ApiError(None, 11101, err)

def del_rel_type_allowed(params):
    try:
        target_obj=get_rel_type_allowed(params)
        if len(target_obj)==1:
            current_rels=get_rel(params)
            if len(current_rels)==0:
                target_obj=target_obj[0]
                target_obj_data=target_obj.to_dict()
                target_obj.delete()
                return target_obj_data
            else:
                raise ApiError(None, 11502, params)
        elif len(target_obj)==0:
            raise ApiError(None, 11500, params)
        else:
            raise ApiError(None, 11501, params)
    except Exception, err:
        raise ApiError(None, 11101, err)

#===============RELATIONSHIP TAG SCHEMA=============#    

def get_rel_tag_schema(params, api_obj=None):
    try:
        objects=RelationshipTagSchema.objects.all()
        if params.has_key('name') and params.get('name'):
            objects=objects.filter(name=params.get('name'))
        if params.has_key('id') and params.get('id'):
            objects=objects.filter(id=params.get('id'))
        #Insert here additional filtering
    
        if int(params.get('count', 0))==1:
            objects_count = objects.count()
            if api_obj is not None:
                api_obj.count=objects_count
            return objects_count
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
    
        result=list(objects[list_offset: list_offset+list_limit])
        
#        if len(result)==0:
#            raise ApiError(None, 11200)
            
        return result
    except Exception, err:
       raise ApiError(None, 11101, err)

def add_rel_tag_schema(params):
    try:
#        transaction.enter_transaction_management()
##        transaction.managed(True)
        if params.has_key('name') and params.get('name'):
            old_object=RelationshipTagSchema.objects.filter(name=params.get('name'))
            if old_object.count()>0:
                raise ApiError(None, 11300, params.get('name'))
            else:
                new_obj=RelationshipTagSchema(name=params.get('name'), 
                                              label=params.get('label', ""), 
                                              status=params.get('status', "A"))
                new_obj.save()
                return new_obj
        else:
            raise ApiError(None, 11103, "schema")
#        transaction.commit()
##        transaction.leave_transaction_management()
    except Exception, err:
##        transaction.rollback()
##        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

def set_rel_tag_schema(params):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        target_obj=get_rel_tag_schema({'name':params.get('name'), 'id':params.get('id')})
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj.label=params.get('label')
            target_obj.status=params.get('status', target_obj.status).upper()
            target_obj.save()
            return target_obj
        elif len(target_obj)==0:
            raise ApiError(None, 11400)
        else:
            raise ApiError(None, 11401)
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

def del_rel_tag_schema(id=None, schema=None):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        old_object=get_rel_tag_schema({'name':name, 'id':id})
        if len(old_object)==1:
            old_object_data=old_object[0].to_dict()
            old_object[0].delete()
            return old_object_data
        elif len(old_object)==0:
            raise ApiError(None, 11500, name)
        else:
            raise ApiError(None, 11501, name)
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

#===============RELATIONSHIP TAG=============#    

def get_rel_tag(params, api_obj = None):
    try:
        objects=EntityTag.objects.all()
        if params.has_key('slug') and params.get('slug'):
            objects=objects.filter(slug=params.get('slug'))
        if params.has_key('id') and params.get('id'):
            objects=objects.filter(id=params.get('id'))
        #Insert here additional filtering
    
        if int(params.get('count', 0))==1:
            objects_count = objects.count()
            if api_obj is not None:
                api_obj.count=objects_count
            return objects_count
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
    
        result=list(objects[list_offset: list_offset+list_limit])
        
        if len(result)==0:
            raise ApiError(None, 11200)
            
        return result
    except Exception, err:
       raise ApiError(None, 11101, err)

def add_rel_tag(params):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        if params.get('name',"")!="":
            slug = params.get('slug')
            
            if not slug or slug=="":
                slug = params.get('name',"")
            slug = string_to_slug(slug)#would a bad formed slug be passed, this will clean it up
            
            old_object=EntityTag.objects.filter(slug=slug)
            if old_object.count()>0:
                raise ApiError(None, 11300, "'%s'" % slug)
            else:
                new_obj=EntityTag(name=params.get('name'), slug=slug, status=params.get('status', "A"))
                new_obj.save()
                return new_obj
        else:
            raise ApiError(None, 11102, "name")
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

def set_rel_tag(params):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        target_obj=get_rel_tag({'id':params.get('id'), 'slug':params.get('slug')})
        if len(target_obj)==1:
            target_obj=target_obj[0]
            target_obj.status=params.get('status', target_obj.status).upper()
            target_obj.save()
            return target_obj
        elif len(target_obj)==0:
            raise ApiError(None, 11400)
        else:
            raise ApiError(None, 11401)
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

def del_rel_tag(id=None, slug=None):
    try:
#        transaction.enter_transaction_management()
#        transaction.managed(True)
        old_object=get_rel_tag({'slug':slug, 'id':id})
        if len(old_object)==1:
            old_object_data=old_object[0].to_dict()
            old_object[0].delete()
            return old_object_data
        elif len(old_object)==0:
            raise ApiError(None, 11500, [id, slug])
        else:
            raise ApiError(None, 11501, [id, slug])
#        transaction.commit()
#        transaction.leave_transaction_management()
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

##===============RELATIONSHIP=============#    

def get_rel(params, api_obj = None):
    try:
        if params.has_key('properties') and params.get('properties')=="1":
            obj=Relationship()
            return obj.properties()
        
        objects=Relationship.objects.all()

        if params.has_key('id') and params.get('id'):
            objects=objects.filter(id=params.get('id'))
            
        if params.has_key('rel_type_id') and params.get('rel_type_id'):
            objects=objects.filter(rel_type__id=params.get('rel_type_id'))
        if params.has_key('rel_type') and params.get('rel_type'):
            type_id=RelationshipType.objects.get(slug=params.get('rel_type')).id
            objects=objects.filter(rel_type__id=type_id)
            
        if params.has_key('entity_from_id') and params.get('entity_from_id'):
            objects=objects.filter(entity_from__id=params.get('entity_from_id'))

        if params.has_key('entity_from') and params.get('entity_from'):
            entities_from=Entity.objects.filter(slug=params.get('entity_from'))
            objects=objects.filter(entity_from__in=entities_from)

        if params.has_key('entity_from_type') and params.get('entity_from_type'):
            entity_from_type=EntityType.objects.get(slug=params.get('entity_from_type'))
            objects=objects.filter(entity_from__type=entity_from_type)

        if params.has_key('entity_to_id') and params.get('entity_to_id'):
            objects=objects.filter(entity_to__id=params.get('entity_to_id'))
            
        if params.has_key('entity_to') and params.get('entity_to'):
            entities_to=Entity.objects.filter(slug=params.get('entity_to'))
            objects=objects.filter(entity_to__in=entities_to)

        if params.has_key('entity_to_type') and params.get('entity_to_type'):
            entity_to_type=EntityType.objects.get(slug=params.get('entity_to_type'))
            objects=objects.filter(entity_to__type=entity_to_type)
            
        #TAGS FILTERING
        tags_filter=build_tags_Q_filter(params.get('tags', ""), 
                                        "tags", 
                                        "relationshiptagcorrelation",
                                        RelationshipTagSchema,
                                        objects)
        if tags_filter is not None:
            objects=objects.filter(tags_filter).distinct()
        
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
                    
                    subquery_wheres=["`core_relationshiptagcorrelation`.`object_id`=`core_relationship`.`id`"]
                    tag_select=""
                    if tag!="" or schema!="":
                        if tag!="":
                            subquery_wheres.append("core_relationshiptagcorrelation.object_tag_id='%s'" % tag)
                            #subquery_wheres.append("core_relationshiptagcorrelation.object_tag_id='%s'" % tag)
                            #objects=objects.filter(tags__slug=tag)
                            tag_select=tag
                        if schema!="":
                            schema_id=None
                            try:
                                schema_id=RelationshipTagSchema.objects.get(slug=unquote(schema)).id
                            except:
                                pass
                            try:
                                subquery_wheres.append("core_relationshiptagcorrelation.object_tag_schema_id='%s'" % schema_id)
                                #objects=objects.filter(relationshiptagcorrelation__object_tag_schema__slug=schema)
                            except:
                                pass
                            if tag_select!="":  
                                tag_select="%s_%s" % (tag_select, unquote(schema))
                            else:
                                tag_select=unquote(schema)
                        subquery_select='''SELECT DISTINCT core_relationshiptagcorrelation.weight 
                        FROM core_relationshiptagcorrelation WHERE %s  
                        GROUP BY `core_relationship`.`id`''' % (" AND ".join(subquery_wheres, ))
                        
                        tag_select="tag_sort_by_field" #% tag_select
                        subquery_order="%s%s" % (sign, tag_select)
                        
                        objects=objects.extra(select={tag_select: subquery_select})
                        
####################UNDOCUMENTED CALL, see http://stackoverflow.com/questions/327807/django-equivalent-for-count-and-group-by ###############################
                        objects.query.group_by = ['`core_relationship`.`id`']
#############################################################################################################################################################                        

                        objects=objects.order_by(subquery_order)
                        
                else:
                    objects=objects.order_by("%s%s" % (sign, sortby))

        if int(params.get('count', 0))==1:
            objects_count = objects.count()
            if api_obj is not None:
                api_obj.count=objects_count
            return objects_count
            
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
    
        result=list(objects[list_offset: list_offset+list_limit])

        #raise ApiError(None, 11101, "pippo3")
        
#        if len(result)==0:
#            raise ApiError(None, 11200, params)
            
        return result
    except Exception, err:
       raise ApiError(None, 11101, err)

def add_rel(params):
    try:
        rel_type_allowed=get_rel_type_allowed(params)
        if len(rel_type_allowed)==1:
            rel_type=get_rel_type({"id":params.get('rel_type_id'), "slug":params.get('rel_type')})
            if len(rel_type)==1:
                rel_type=rel_type[0]
            else:
                rel_type=None
            
#--------------------backward compatibility with old not following naming policy parameters--------#
            if (not params.get('entity_from_type_id')):
                params['entity_from_type_id']=params.get('entity_type_from_id');
            if (not params.get('entity_from_type')):
                params['entity_from_type']=params.get('entity_type_from');
#-------------------------------------------------------------------------------------------------#
           
            entity_from=get_entity({"id":params.get('entity_from_id'), "slug":params.get('entity_from'), 'type_id':params.get('entity_from_type_id'), 'type':params.get('entity_from_type')})
            if len(entity_from)==1:
                entity_from=entity_from[0]
            else:
                entity_from=None
    
#--------------------backward compatibility with old not following naming policy parameters--------#
            if (not params.get('entity_to_type_id')):
                params['entity_to_type_id']=params.get('entity_type_to_id');
            if (not params.get('entity_to_type')):
                params['entity_to_type']=params.get('entity_type_to');
#-------------------------------------------------------------------------------------------------#

            entity_to=get_entity({"id":params.get('entity_to_id'), "slug":params.get('entity_to'), 'type_id':params.get('entity_to_type_id'), 'type':params.get('entity_to_type')})
            if len(entity_to)==1:
                entity_to=entity_to[0]
            else:
                entity_to=None
            
            status=params.get('status', 'A').upper()

            if rel_type and entity_from and entity_to:
                old_obj=None
                try:
                    old_obj=Relationship.objects.get(rel_type = rel_type,  
                                         entity_from = entity_from, 
                                         entity_to = entity_to)
                except:
                    pass
                if old_obj==None:
                    if rel_type.reciprocated:
                        old_rev_obj=None
                        try:
                            old_rev_obj=Relationship.objects.get(rel_type = rel_type,  
                                                 entity_from = entity_to, 
                                                 entity_to = entity_from)
                        except:
                            pass
                        if old_rev_obj==None:
                            rev_obj=Relationship(rel_type = rel_type,  
                                                 entity_from = entity_to, 
                                                 entity_to = entity_from,
                                                 status=status)
                            rev_obj.save()
                            
                            rev_obj.set_tags(params.get('tags'))
                        else:
                            if params.get("skip_existsing_err")!="1":
                                raise ApiError(None, 11314, params)
    
                    new_obj=Relationship(rel_type = rel_type,  
                                         entity_from = entity_from, 
                                         entity_to = entity_to,
                                         status=status)
                    new_obj.save()
     
                    new_obj.set_tags(params.get('tags'))
    
                    return new_obj
                else:
                    if params.get("skip_existsing_err")!="1":
                        raise ApiError(None, 11314, params)
                    else:
                        return old_obj
            else:
                raise ApiError(None, 11313, "%s - %s" % ([rel_type , entity_from , entity_to], params))
        elif len(rel_type_allowed)==0:
            raise ApiError(None, 11315, params)
        else:
            raise ApiError(None, 11316, params)
    except Exception, err:
#        transaction.rollback()
#        transaction.leave_transaction_management()
        raise ApiError(None, 11101, err)

def set_rel(params):
    try:
        rel_type=get_rel_type({"id":params.get('rel_type_id'), "slug":params.get('rel_type')})
       
        if len(rel_type)==1:
            rel_type=rel_type[0]
        else:
            rel_type=None
                   
        entity_from=get_entity({"id":params.get('entity_from_id'), "slug":params.get('entity_from'), 'type_id':params.get('entity_from_type_id'), 'type':params.get('entity_from_type')})
        if len(entity_from)==1:
            entity_from=entity_from[0]
        else:
            entity_from=None

        entity_to=get_entity({"id":params.get('entity_to_id'), "slug":params.get('entity_to'), 'type_id':params.get('entity_to_type_id'), 'type':params.get('entity_to_type')})
        if len(entity_to)==1:
            entity_to=entity_to[0]
        else:
            entity_to=None
        
        target_obj=list()
        
        if rel_type and entity_from and entity_to:
            #target_obj=None
            try:
                target_obj=Relationship.objects.filter(rel_type = rel_type,  
                                     entity_from = entity_from, 
                                     entity_to = entity_to)
            except Exception, err:
                    pass
                
#        target_obj=get_rel(params)
        if len(target_obj)==1:
            target_obj=target_obj[0]
            
            target_obj.set_tags(params.get('tags'))
            
            status=params.get('status', target_obj.status).upper()
            if target_obj.status!=status:
                target_obj.status=status
                target_obj.save()
                
            return target_obj
        elif len(target_obj)==0:
            return add_rel(params)
            #raise ApiError(None, 11400)
        else:
            raise ApiError(None, 11401)
    except Exception, err:
        raise ApiError(None, 11101, err)

def del_rel(params):
    transaction.enter_transaction_management()
    try:
        old_object=get_rel(params)
        if len(old_object)==1:
            old_object_data=old_object[0].to_dict()
            if old_object[0].rel_type.reciprocated:
                try:
                    Relationship.objects.get(rel_type = old_object[0].rel_type,  
                                         entity_from = old_object[0].entity_to, 
                                         entity_to = old_object[0].entity_from).delete()
                except:
                    pass
            old_object[0].delete()
            transaction.commit()
            return old_object_data
        elif len(old_object)==0:
            raise ApiError(None, 11500, "%s" % params)
        else:
            raise ApiError(None, 11501, "%s" % params)
    except Exception, err:
        transaction.rollback()
        raise ApiError(None, 11101, err)
    finally:
        transaction.leave_transaction_management()

##===================================================================