from django.db import models
from erm.lib.misc_utils import *
from django.db.models import Q

from django.db import connection, DatabaseError, IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist

from erm.lib.api import ApiError, ERROR_CODES

import datetime
import time

from erm.lib.logger import Logger
from erm.lib.db_utils import require_lock

import cjson

from urllib import unquote

#ERROR_CODES=dict()
#=====================generic or common errors=====================#
ERROR_CODES["12100"]="core model generic error: ?" 
#=====================set:tags=====================#
ERROR_CODES["12200"]="set tags: invalid slug" 
ERROR_CODES["12300"]="set tags: duplicate name with new slugs" 
ERROR_CODES["12400"]="set tags: either name or slug is required to define a tag" 
#=====================init=====================#

GENERIC_STATUS = (
    ('A', 'Active'),
    ('H', 'Hidden'), 
    ('I', 'Inactive'),
)
TAG_STATUS=GENERIC_STATUS
SCHEMA_STATUS=GENERIC_STATUS
ENTITY_TYPE_STATUS=GENERIC_STATUS
ENTITY_STATUS=GENERIC_STATUS
RELATIONSHIP_TYPE_STATUS=GENERIC_STATUS
RELATIONSHIP_STATUS=GENERIC_STATUS
UNION_STATUS=GENERIC_STATUS

def set_object_tags(obj, tags_list, object_tag_model, object_tag_schema_model, object_tag_correlation_model, object_tag_correlation_table_name, object_schemed_tag_model, type_attr='type'):
    
        tagcloud_tags=list()
        
        build_key = lambda slug, schema: "%s++%s" % (slug, schema)
            
        if tags_list: 
            
            if isinstance(tags_list, list):
                
                #separate tags to add and to delete
                all_tags_dict  = dict()
                tags_to_update = dict()
                tags_to_delete = dict()
                tags_added = dict()

                delete_tags_select=list()
                
                schemas_ids_dict = dict()
                
                for item in tags_list:
                    fl_skip_tag=False
                    
                    #if no slug is provided extract slug from name
                    name_value=""
                    slug_value=""
                    tag_negated=False
                    if (not item.has_key('slug')):
                        if item.has_key('name'):
                            name_negated=""
                            name_value=item['name']
                            if name_value[0]=="!":
                                tag_negated=True
                                name_value=name_value[1:]
                            slug_value =string_to_slug(name_value)
                        else:
                            raise ApiError(None, 12400)
                    else: 
                        if item.has_key('slug'):
                            slug_value=item['slug']
                            if slug_value[0]=="!":
                                tag_negated=True
                                slug_value=slug_value[1:]
                    
                    if slug_value!="":
                         #let's validate slug and name
                        if slug_value == string_to_slug(slug_value):
                            if name_value=="":
                                name_value=slug_value     
                            elif slug_value != string_to_slug(name_value):
                                tag_obj=object_tag_model.objects.filter(name=name_value)
                                if len(tag_obj)>0 and tag_obj[0].slug!=slug_value:
                                    #this name has already been mapped to another slug, raise an error
                                    raise ApiError(None, 12300, "%s: %s --> %s" % (name, slug, tag_obj[0].slug))
                        else:
                            #bad slug, raise an error
                            raise ApiError(None, 12200, "%s --> %s" % (slug, string_to_slug(slug)))
                    
                        schema_value=item.get('schema', None)
                        schema_key=schema_value
                        
                        if not schema_value:
                            schema_key="None"
                        elif not (schema_key in schemas_ids_dict):
                            schema_obj, schema_created=object_tag_schema_model.objects.get_or_create(slug=schema_key)
                            if schema_obj.name=="" or schema_obj.name==None:
                                schema_obj.name=schema_key
                                schema_obj.save()
                            schemas_ids_dict[schema_key]=str(schema_obj.id)
                        
                        item_to_process={"slug":slug_value, "name":name_value, "schema": schema_value, "weight":item.get('weight', "+0")}
                        
                        if item.get('tagcloud', "")!="":
                            tagcloud_tags.append(item_to_process)
                            fl_skip_tag= item['tagcloud'][-1:]=="!"
                        
                        if not fl_skip_tag:
                            schema_slug_key=build_key(slug_value, schema_key)
                            all_tags_dict[schema_slug_key]=item_to_process

                            
                            if not tag_negated:
                                tags_to_update[schema_slug_key]=item_to_process
                            else:
                                tags_to_delete[schema_slug_key]=item_to_process     
                                if not schema_value:
                                    schema_query = ' IS NULL'
                                else:
                                    schema_query="=%s" % schemas_ids_dict[schema_key]
                                delete_tags_select.append("(object_tag_id='%s' AND object_tag_schema_id%s)" % (slug_value, schema_query))
           
                
                if len(tags_to_delete):
                    delete_ids=list()
                    get_tags_query="DELETE FROM %s WHERE object_id=%s AND (%s);" % (object_tag_correlation_table_name, obj.id, " OR ".join(delete_tags_select))
                    cursor = connection.cursor()
                    cursor.execute(get_tags_query)
                    
                if len(tags_to_update):
                    
                    #Add or update passed tags
                    for tag_key, tag in tags_to_update.items(): 
                        tag_obj, tag_created=object_tag_model.objects.get_or_create(slug=tag['slug'],
                                                                 name=tag['name'])
    
                        schema_obj=None
                        if tag.has_key('schema') and tag['schema'] and tag['schema']!="":
                            schema_obj, schema_created=object_tag_schema_model.objects.get_or_create(slug=tag['schema'])
                            if schema_obj.name=="" or schema_obj.name==None:
                                schema_obj.name=tag['schema']
                                schema_obj.save()
                        
                        correlation, created=object_tag_correlation_model.objects.get_or_create(object=obj,
                                                                                        object_tag=tag_obj, 
                                                                                        object_type=getattr(obj, type_attr), 
                                                                                        object_tag_schema=schema_obj
                                                                                        )
                        if created:
                            tags_added[tag_key]={"tag_obj":tag_obj, "schema_obj":schema_obj}
                            
                        corr_weight=tag.get('weight', '+0')
                        if corr_weight!="+0":
                            correlation.update_weight(tag.get('weight', '+0'))
                            correlation.save()    
                
                if len(tags_to_delete):
                    for tag_key, tag_value in tags_to_delete.items():
                        try:
                            tag_obj = object_tag_model.objects.get(slug=tag_value['slug'])
                            schema_obj=None
                            if tag_value.has_key('schema') and tag_value['schema'] and tag_value['schema']!="":
                                schema_obj=object_tag_schema_model.objects.get(slug=tag_value['schema'])
                            try:
                                schemedtag = object_schemed_tag_model.objects.get(object_type=getattr(obj, type_attr),
                                                                                        tag=tag_obj, 
                                                                                        schema=schema_obj
                                                                                        )                        
                                if schemedtag.items_count>1:
                                    schemedtag.items_count-=1
                                    schemedtag.save()
                                else:
                                    schemedtag.delete()
                                    
                            except ObjectDoesNotExist:
                                pass
                        except ObjectDoesNotExist:
                            pass
                
                if (len(tags_to_delete)+len(tags_added))>0:
                    updated_correlations=object_tag_correlation_model.objects.filter(object=obj)#.values('object_tag', 'object_tag_schema', 'object_tag_schema__slug')
                    for tag_correlation in updated_correlations:
                        try:
                            schemedtag, schemedtag_created = object_schemed_tag_model.objects.get_or_create(object_type=getattr(obj, type_attr),
                                                                                    tag=tag_correlation.object_tag, 
                                                                                    schema=tag_correlation.object_tag_schema
                                                                                    )                        
                            related=cjson.decode(schemedtag.related)
                            
                            if len(tags_to_delete):
                                for tag_key in tags_to_delete.keys():
                                    if tag_key in related:
                                        if related[tag_key]['weight']>1:
                                            related[tag_key]['weight']-=1
                                        else: 
                                            del(related[tag_key])
                            
                            if len(tags_added):
                                for tag_key, tag_value in tags_added.items():
                                    if tag_value['tag_obj'].slug!=tag_correlation.object_tag.slug or tag_value['schema_obj'].id!=tag_correlation.object_tag_schema.id:
                                        if tag_key in related:
                                            related[tag_key]['weight']+=1
                                        else:
                                            related[tag_key]={'weight':1,
                                                              'tag':tag_value['tag_obj'].slug,
                                                              'schema':tag_value['schema_obj'].slug}
                            schemedtag.related=cjson.encode(related)
                            schemedtag.save()
                            
                        except ObjectDoesNotExist:
                            pass

                    if len(tags_added):
                        for tag_key, tag_value in tags_added.items():
                            tag_obj=tag_value['tag_obj']
                            schema_obj=tag_value['schema_obj']
                            schemedtag, schemedtag_created=object_schemed_tag_model.objects.get_or_create(object_type=getattr(obj, type_attr),
                                                                                        tag=tag_obj, 
                                                                                        schema=schema_obj
                                                                                        )
                            related=dict()
                            for tag_correlation in updated_correlations:
                                tag_key=build_key(tag_correlation.object_tag.slug, tag_correlation.object_tag_schema.slug)
                                if tag_value['tag_obj'].slug!=tag_correlation.object_tag.slug or tag_value['schema_obj'].id!=tag_correlation.object_tag_schema.id:
                                    if tag_key in related:
                                        related[tag_key]['weight']+=1
                                    else:
                                        related[tag_key]={'weight':1,
                                                          'tag':tag_correlation.object_tag.slug,
                                                          'schema':tag_correlation.object_tag_schema.slug}
                            
                            schemedtag.related=cjson.encode(related)
                            schemedtag.items_count=schemedtag.items_count+1
                            schemedtag.save()
                                

            else:
                raise Exception, "A list is expected to define tags, got: %s" % (tags_list)
                            
            if len(tagcloud_tags) and type_attr=='type': #this is valid just for rnities, not for relationships
                tagclouds=dict()
                for tagcloud_tag in tagcloud_tags:
                    if tagcloud_tag['slug']!="":
                        cloud_attribute=tagcloud_tag['tagcloud']
                        if cloud_attribute[-1:]=="!":
                            cloud_attribute=cloud_attribute[:-1]
                        if not (cloud_attribute in tagclouds):
                            old_attribute=obj.type.repository.get_record(obj.id, cloud_attribute)[cloud_attribute]
                            #raise ApiError(None,100, "==>%s" % old_attribute)
                            if (old_attribute!=None) and (old_attribute!=""):
                                tags_list=cjson.decode(old_attribute)
                                tagclouds[cloud_attribute]=dict(tag_item for tag_item in tags_list)
                            else:
                                tagclouds[cloud_attribute]=dict()
                        increment=1
                        cloud_slug=tagcloud_tag['slug']
                        if cloud_slug[0]=="!":
                            cloud_slug=cloud_slug[1:]
                            increment=-1
                        if not cloud_slug in tagclouds[cloud_attribute]:
                            tagclouds[cloud_attribute][cloud_slug]=0
                        
                        tagclouds[cloud_attribute][cloud_slug]+=increment
                
                clouds_attributes=dict()
                from operator import itemgetter
                for cloud_attribute_key, attribute_value in tagclouds.items():
                
                    cloud_sorted_list=list()
                    for tag_key, tag_weight in attribute_value.items():
                        if tag_weight>0:
                            cloud_sorted_list.append([tag_key, tag_weight])
                    
                    cloud_sorted_list.sort(key = itemgetter(1), reverse=True)
                    clouds_attributes[cloud_attribute_key] = cjson.encode(cloud_sorted_list)

                #raise ApiError(None,100, "==>%s" % clouds_attributes)    
                obj.type.repository.update_record(self.id, clouds_attributes)


class EntityUnion (models.Model):
    slug = models.CharField(max_length=255, unique=True, blank=False, null=False)
    name = models.CharField(max_length=255, unique=False, blank=True, null=True)
    status = models.CharField(max_length=1, choices=UNION_STATUS, default='A')

    def properties(self):
        return {'id':'integer', 
                'slug': 'str(255)', 
                'name': 'str(255)', 
                'status':'char'}
        
    def __unicode__(self):
        return self.name
    
    def to_dict(self, compact=False, types_opts={}):      
        
        #return self.status
      
        objects=Entity.objects.filter(entity_union=self)
        objects_dict=dict()
        default_opts={"compact":True}
        for object in objects:
            params=types_opts.get(object.type.slug, default_opts)
            objects_dict[object.type.slug]=object.to_dict(**params)
        name=self.name
        if not name:
            name=self.slug
        result = {'id':self.id, 
            'name': self.name, 
            'slug': self.slug, 
            'status': self.status,
            'entities':objects_dict
            }
        return result
    
#========ENTITIES========#

class EntityTagSchema(models.Model):
    slug = models.CharField(max_length=255, unique=True, blank=False, null=False)
    name = models.CharField(max_length=255, blank=True, unique=False, null=True)
    status = models.CharField(max_length=1, choices=SCHEMA_STATUS, default='A')
    
    def properties(self):
        return {'id':'integer', 
                'slug': 'str(255)', 
                'name': 'str(255)', 
                'status':'char'}
        
    def __unicode__(self):
        return self.name
    
    def to_dict(self, compact=False):
        return {'id':self.id, 
                'slug': self.slug, 
                'name': self.name, 
                'status': self.status}

class EntityTag (models.Model):
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    slug = models.CharField(max_length=255, unique=True, null=False, blank=False, primary_key=True)
    status = models.CharField(max_length=1, choices=TAG_STATUS, default='A')
    kind = models.CharField(max_length=10, null=True, blank=True, editable=False)#internal use, to mark tags when, for example, manually or programmatically set, and not extracted
    items_count = models.IntegerField(blank=True, default=0, editable=False)
#    relateds = models.ManyToManyField("self", through='EntityTagRelatedTag', symmetrical=False, null=True)

    def __unicode__(self):
        return "%s" %(self.slug)
        return "%s [%s]" %(self.name, self.slug)
    
    def properties(self):
        return {'id':'integer', 
                'name': 'str(255)', 
                'slug': 'str(255)', 
                'status':'char', 
                'kind':'char', 
                'items_count':'integer',
                'relateds':'*EntityTag', 
        }

    def to_dict(self, compact=True):
        d = dict(
            id=self.id,
            name=self.name, 
            slug=self.slug,
            status=self.status,
            items_count=self.items_count
        )
        if not compact:
            relateds=list()
            try:
                related_tags=EntityTagRelatedTag.objects.filter(Q(tag_a=self) | Q(tag_b=self))
                for obj in related_tags:
                    relateds.append( obj.to_dict())
                #DATA MANAGER CONNECTION HERE??
            except:
                pass
            d['relateds']=relateds
        return d
    

class EntityType (models.Model):
    slug = models.CharField(max_length=255, unique=True, blank=False, null=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    items_count = models.IntegerField(blank=True, default=0, editable=False)
    status = models.CharField(max_length=1, choices=ENTITY_TYPE_STATUS, default='A')
    do_index = models.BooleanField(null=False, default=True)

    def properties(self):
        return {'id':'integer', 
                'slug': 'str(255)', 
                'name': 'str(255)', 
                'status':'char', 
                'items_count':'integer',
                }

    def __unicode__(self):
        return self.name

    def to_dict(self, compact=False):
        
        d = dict(
            id=self.id, 
            slug=self.slug,
            name=self.name,
        )
        if not compact:
            d['attributes']=list()
            try:
                fields=self.repository.get_fields()
                for field in fields:
                    d['attributes'].append(field.to_dict())
            except:
                pass
            try:
                d['repository']=self.repository.id
            except:
                d['repository']=None
            try:
                d['repository_kind']=self.repository.kind
            except:
                d['repository_kind']=None
            try:
                d['conn_attributes']=self.repository.connector().get_default_attributes()
            except Exception, err:
                d['conn_attributes']="%s" % err
                pass

        return d

class EntitySchemedTag (models.Model):
    object_type = models.ForeignKey(EntityType, null=False, blank=False)
    tag = models.ForeignKey(EntityTag, null=False, blank=False)
    schema = models.ForeignKey(EntityTagSchema, null=True)
    items_count = models.IntegerField(blank=True, default=0, editable=False)
    related = models.TextField(null=False, blank=False, default='{}')

    def properties(self):
        return {'object_type':'*EntityType', 
                'tag':'*EntityTag', 
                'schema':'*EntityTagSchema', 
                'items_count':'integer',
                'relateds':'json',
        }
        
    def to_dict(self, compact=False):
        return {'object_type':self.object_type.slug, 
                'tag':self.tag.slug,
                'schema':self.schema.slug, 
                'items_count':self.items_count,
                'relateds':self.relateds}    
        
class Entity(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    slug = models.CharField(max_length=255, null=False, blank=False)
    uri = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    type = models.ForeignKey(EntityType, null=False, blank=False)
    tags = models.ManyToManyField(EntityTag, through = 'EntityTagCorrelation')
    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True, auto_now_add=True)
    custom_date = models.DateTimeField(auto_now_add=False, null=True, blank=True )
    status = models.CharField(max_length=1, choices=ENTITY_STATUS, default='A')
    entity_union = models.ForeignKey(EntityUnion, null=True, blank=True, default=None)     
    longitude = models.FloatField(blank=True, default=None, null=True)
    latitude = models.FloatField(blank=True, default=None, null=True)

    def properties(self):
        return {'id':'integer', 
                'name': 'str(255)', 
                'slug': 'str(255)', 
                'uri': 'str(255)', 
                'status':'char', 
                'type':'*EntityType', 
                'tags':'*Entitytag', 
                'creation_date':'date',
                'modification_date':'date',
                'entity_union':'*EntityUnion',
                'longitude':'float',
                'latitude':'float',
                }
 
    def __unicode__(self):
        return self.name
    
    def to_dict(self, compact=False, attributes="*", tags="*" ,rels=False, fl_mask_attributes_err=True, cache_life=0, fl_set_cache_date=False):
        d = dict(
            id=self.pk, 
            name=self.name, 
            slug=self.slug,
            type=self.type.slug,
            type_id=self.type.id,
            uri=self.uri, 
        )
        
        d['creation_date']=time.mktime(self.creation_date.timetuple())
        d['modification_date']=time.mktime(self.modification_date.timetuple())
        if self.custom_date:
            d['custom_date']=time.mktime(self.custom_date.timetuple())
        else:
            d['custom_date']=None
        if not compact:
            union_id=None
            if self.entity_union:
                union_id=self.entity_union.id
            d["union"]=union_id
            if tags!="":
                tags_list=list()
                try:
                    correlations=EntityTagCorrelation.objects.select_related().filter(object=self)
                    if tags!="*":
                        req_tags=tags.split("||")
                        qset = Q()
                        for chunk in req_tags:
                            qset_inner = Q()
                            req_tags_split=chunk.split("{")
                            req_slugs_list=req_tags_split[0].split(",")
                            schema=""
                            
                            if len(req_tags_split)>1: 
                                schema=req_tags_split[1][:-1]
                            if len(req_slugs_list)>0 and req_slugs_list!=['']:
                                qset_inner|=Q(object_tag__slug__in=req_slugs_list)
#                                correlations=correlations.filter(object_tag__slug__in=req_slugs_list)
                            if schema!="":
                                qset_inner&=Q(object_tag_schema__slug=unquote(schema))
#                                correlations=correlations.filter(object_tag_schema__slug=schema)
                            qset|=qset_inner
                        correlations=correlations.filter(qset)

                    for obj in correlations:
                        tags_list.append(obj.to_dict())                            
                    #DATA MANAGER CONNECTION HERE??
                except Exception, err:
                    tags_list=[{"err": "%s" % err}]
            
                d['tags']=tags_list
            
            if attributes!="":
                try:
                    d['attributes']=self.type.repository.get_record(self.id, attributes, cache_life, fl_set_cache_date)
                except Exception, err:
                    if fl_mask_attributes_err:
                        d['attributes']=[{"err": "%s" % err}]
                    else:
                        raise ApiError(None, 100, "Error: %s (%s)" % (Exception, err))

            if rels and rels!="":
                to_flag=True
                from_flag=False
                if type(rels) is bool:
                    to_flag=True
                    from_flag=True
                    rels="*"
                if rels!="*":
                    if rels[0]=="-" or rels[0]=="<":
                        from_flag=True
                        to_flag=False
                        rels=rels[1:]
                        if rels[0]=="+" or rels[0]==">":
                            to_flag=True
                            rels=rels[1:]
                    if rels[0]=="+" or rels[0]==">":
                        rels=rels[1:]
                        if rels[0]=="-" or rels[0]=="<":
                            to_flag=False
                            from_flag=True
                            rels=rels[1:]
                    
                try:
                    rel_objects=Relationship.objects.all()
                    if rels!="*":
                        rel_objects=rel_objects.filter(rel_type__slug=rels)
                    if to_flag:
                        rel_objects_to=rel_objects.filter(entity_from__type=self.type.id)
                        rel_objects_to=rel_objects.filter(entity_from__slug=self.slug)
                        d['relationships']=[rel_object.to_dict() for rel_object in rel_objects_to]
                    
                    #rel_objects=Relationship.objects.all()
                    if from_flag:
                        rel_objects=rel_objects.filter(entity_to__type=self.type.id)
                        rel_objects=rel_objects.filter(entity_to__slug=self.slug)
                        d['reverse_relationships']=[rel_object.to_dict() for rel_object in rel_objects]
                except Exception, err:
                    d['rel_err']=err
                

            d['creation_date_v']=self.creation_date.ctime()
            d['modification_date_v']=self.modification_date.ctime()
            if d['custom_date']:
                d['custom_date_v']=self.custom_date.ctime()
            else:
                d['custom_date_v']="NULL"
 
            d['longitude']=self.longitude
            d['latitude']=self.latitude
                                
        return d

    @require_lock('core_entitytagcorrelation','core_entityschemedtag', 'core_entitytagschema', 'core_entitytag', 'core_entity', 'core_entitytype')
    def set_tags(self, tags_list=None):
        
        object_tag_correlation_table_name = 'core_entitytagcorrelation'
        object_tag_model = EntityTag
        object_tag_schema_model = EntityTagSchema
        object_tag_correlation_model = EntityTagCorrelation
        object_schemed_tag_model = EntitySchemedTag
        
        return set_object_tags(self, tags_list, object_tag_model, object_tag_schema_model, object_tag_correlation_model, object_tag_correlation_table_name, object_schemed_tag_model)
        

    class Meta:
        verbose_name_plural = "entities"             
        unique_together = ("slug", "type")

class EntityTagCorrelation (models.Model):
    object = models.ForeignKey(Entity)
    object_type = models.ForeignKey(EntityType, null=False, blank=False)
    object_tag = models.ForeignKey(EntityTag)
    object_tag_schema = models.ForeignKey(EntityTagSchema, null=True)
    weight=models.IntegerField(blank=True, default=0, null=True)
    
    def properties(self):
        return {'id':'integer', 
                'object': '*Entity', 
                'object_type': '*EntityType', 
                'object_tag': '*EntityTag', 
                'object_tag_schema': '*EntityTagSchema', 
                'weight':'integer',
                }

    def update_weight(self, weight='+0'):
        new_weight=0
        try:
            if self.weight:
                new_weight=self.weight
        except:
            pass
        if str(weight)[-1:] != ('!'):
            try:
                new_weight+=int(weight)
            except:
                pass
        else:
            try:
                new_weight=int(weight[:-1])
            except:
                pass
        self.weight=new_weight
        self.save()
            
    def to_dict(self, compact=False):
        try:
           schema=self.object_tag_schema.slug
           schema_name=self.object_tag_schema.name
           schema_status=self.object_tag_schema.status
        except:
           schema=None
           schema_name=None
           schema_status="A"

        d=dict(
               id=self.id,
#               tag=self.object_tag.name,
               name=self.object_tag.name,
               slug=self.object_tag.slug,
               tag_status=self.object_tag.status,
               type=self.object_type.slug,
               schema=schema,
               schema_name=schema_name,
               schema_status=schema_status,
               weight=self.weight,
               )
        return d


#========RELATIONSHIPS========#

class RelationshipTagSchema(models.Model):
    slug = models.CharField(max_length=255, blank=False, unique=True, null=False)
    name = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=1, choices=SCHEMA_STATUS, default='A')
    
    def properties(self):
        return {'id':'integer', 
                'name': 'str(255)', 
                'slug': 'str(255)', 
                'status':'char'}
        
    def __unicode__(self):
        return self.name
    
    def to_dict(self, compact=False):
        return {'id':self.pk, 
                'slug': self.slug, 
                'name': self.name, 
                'status': self.status}

class RelationshipTag (models.Model):
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    slug = models.CharField(max_length=255, unique=True, null=False, blank=False, primary_key=True)
    status = models.CharField(max_length=1, choices=TAG_STATUS, default='A')
    kind = models.CharField(max_length=10, null=True, blank=True, editable=False)#internal use, to mark tags when, for example, manually or programmatically set, and not extracted
    items_count = models.IntegerField(blank=True, default=0, editable=False)
#    relateds = models.ManyToManyField("self", through='RelationshipTagRelatedTag', symmetrical=False, null=True)

    def __unicode__(self):
        return "%s" %(self.slug)

    def to_dict(self, compact=False):
        d = dict(
            name=self.name, 
            slug=self.slug,
            status=self.status,
            items_count=self.items_count
        )
        if not compact:
            relateds=list()
            try:
                related_tags=RelationshipTagRelatedTag.objects.filter(Q(tag_a=self) | Q(tag_b=self))
                for obj in related_tags:
                    relateds.append( obj.to_dict())
                #DATA MANAGER CONNECTION HERE??
            except:
                pass
            d['relateds']=relateds
        return d
    
   
class RelationshipType (models.Model):
    slug = models.CharField(max_length=255, unique=True, blank=False, null=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    name_reverse = models.CharField(max_length=255, blank=True, null=True)
    relationship_count = models.IntegerField(blank=True, default=0, editable=False)
    status = models.CharField(max_length=1, choices=RELATIONSHIP_TYPE_STATUS, default='A')
    reciprocated = models.BooleanField(default=False)

    def properties(self):
        return {'id':'integer', 
                'slug':'str(255)', 
                'name':'str(255)', 
                'name_reverse':'str(255)', 
                'relationship_count':'integer',
                'status':'char', 
                'reciprocated':'boolean', 
        }
        
    def __unicode__(self):
        return self.name

    def to_dict(self, compact=False):
        d = dict(
            id=self.pk, 
            slug=self.slug,
            name=self.name,
            name_reverse=self.name_reverse,
            status=self.status,
            reciprocated=self.reciprocated,
        )
                    
        return d

class RelationshipSchemedTag (models.Model):
    object_type = models.ForeignKey(RelationshipType, null=False, blank=False)
    tag = models.ForeignKey(RelationshipTag, null=False, blank=False)
    schema = models.ForeignKey(RelationshipTagSchema, null=True)
    items_count = models.IntegerField(blank=True, default=0, editable=False)
    related = models.TextField(null=False, blank=False, default='{}')

    def properties(self):
        return {'object_type':'*RelationshipType', 
                'tag':'*RelationshipTag', 
                'schema':'*EntityTagSchema', 
                'items_count':'RelationshipTagSchema',
                'relateds':'json',
        }
        
    def to_dict(self, compact=False):
        return {'object_type':self.object_type.slug, 
                'tag':self.tag.slug,
                'schema':self.schema.slug, 
                'items_count':self.items_count,
                'relateds':self.relateds}    
        
        
class RelationshipTypeAllowed(models.Model):
    rel_type = models.ForeignKey(RelationshipType, related_name='allowed')
    entity_type_from = models.ForeignKey(EntityType, related_name='entity_type_from')
    entity_type_to = models.ForeignKey(EntityType, related_name='entity_type_to')

    def properties(self):
        return {'id':'integer', 
                'rel_type':'*RelationshipType', 
                'entity_type_from':'*EntityType', 
                'entity_type_to':'*EntityType', 
        }
#    
    def rel_type_name(self):
        rel_desc=self.rel_type
        if self.rel_type.name:
            rel_desc=self.rel_type.name
        return ("%s > %s > %s" % (self.entity_type_from, rel_desc, self.entity_type_to))
    
    class Meta:
        verbose_name_plural = "relationship types allowed"         
            
    def to_dict(self, compact=False):
        d = dict(
            id=self.id,
            rel_type=self.rel_type.slug, 
            rel_type_id=self.rel_type.id, 
            entity_type_from=self.entity_type_from.slug,
            entity_type_from_id=self.entity_type_from.id,
            entity_type_to=self.entity_type_to.slug,
            entity_type_to_id=self.entity_type_to.id,
        )
        return d

class Relationship (models.Model):
    rel_type = models.ForeignKey(RelationshipType)
    tags = models.ManyToManyField(RelationshipTag, through = 'RelationshipTagCorrelation', blank=True, null=True)
    entity_from = models.ForeignKey(Entity, related_name = 'related_to')
    entity_to = models.ForeignKey(Entity, related_name = 'related_by')
    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True, auto_now_add=True)
    status = models.CharField(max_length=1, choices=RELATIONSHIP_STATUS, default='A')

    def properties(self):
        return {'id':'integer', 
                'rel_type':'*RelationshipType', 
                'entity_from':'*Entity', 
                'entity_to':'*Entity', 
                'tags':'*RelationshipTag', 
                'creation_date':'date',
                'modification_date':'date',
                'status':'char', 
       }

    def __unicode__(self):
        return "%s > %s > %s" % (self.entity_from.name, self.rel_type.name, self.entity_to.name)

    def to_dict(self, compact=False):
        d = dict(
            id=self.id,
            rel_type=self.rel_type.slug, 
            rel_type_id=self.rel_type.id, 
            entity_from=self.entity_from.slug,
            entity_from_type=self.entity_from.type.slug,
            entity_from_id=self.entity_from.id,
            entity_to=self.entity_to.slug,
            entity_to_type=self.entity_to.type.slug,
            entity_to_id=self.entity_to.id,
            creation_date=time.mktime(self.creation_date.timetuple()),
            modification_date=time.mktime(self.modification_date.timetuple()),
            status=self.status
        )
        if not compact:
            tags_list=list()
            try:
                correlations=RelationshipTagCorrelation.objects.filter(object=self)
                for obj in correlations:
                    tags_list.append( obj.to_dict())
                #DATA MANAGER CONNECTION HERE??
            except Exception, err:
                tags_list=[{"err": "%s" % err}]
        
            d['tags']=tags_list
        return d

    @require_lock('core_relationshiptagcorrelation','core_relationshipschemedtag', 'core_relationshiptagschema', 'core_relationshiptag', 'core_relationship', 'core_relationshiptype                                                                                                                                                                                                                                                                                                                                                                            ')
    def set_tags(self, tags_list=None):
        
        object_tag_correlation_table_name = 'core_relationshiptagcorrelation'
        object_tag_model = RelationshipTag
        object_tag_schema_model = RelationshipTagSchema
        object_tag_correlation_model = RelationshipTagCorrelation
        object_schemed_tag_model = RelationshipSchemedTag

        return set_object_tags(self, tags_list, object_tag_model, object_tag_schema_model, object_tag_correlation_model, object_tag_correlation_table_name, object_schemed_tag_model, 'rel_type')


class RelationshipTagCorrelation (models.Model):
    object = models.ForeignKey(Relationship)
    object_type = models.ForeignKey(RelationshipType)
    object_tag = models.ForeignKey(RelationshipTag)
    object_tag_schema = models.ForeignKey(RelationshipTagSchema, null=True)
    weight=models.IntegerField(blank=True, default=0, null=True)

    def properties(self):
        return {'id':'integer', 
                'object': '*Relationship', 
                'object_type': '*RelationshipType', 
                'object_tag': '*RelationshipTag', 
                'object_tag_schema': '*RelationshipTagSchema', 
                'weight':'integer',
                }

    def to_dict(self, compact=False):
        try:
           schema=self.object_tag_schema.slug
           schema_name=self.object_tag_schema.name
           schema_status=self.object_tag_schema.status
        except:
           schema=None
           schema_name=None
           schema_status="A"

        d=dict(
               id=self.id,
#               tag=self.object_tag.name,
               name=self.object_tag.name,
               slug=self.object_tag.slug,
               tag_status=self.object_tag.status,
               type=self.object_type.slug,
               schema=schema,
               schema_name=schema_name,
               schema_status=schema_status,
               weight=self.weight,
               )
        return d

    def update_weight(self, weight='+0'):
        new_weight=0
        try:
            if self.weight:
                new_weight=self.weight
        except:
            pass
        if str(weight)[-1:] != ('!'):
            try:
                new_weight+=int(weight)
            except:
                pass
        else:
            try:
                new_weight=int(weight[:-1])
            except:
                pass
        self.weight=new_weight
        self.save()
   
#=========ACTIVITIES========#

class Activity (models.Model):
    activity_id = models.IntegerField(null=True)
    title = models.CharField(max_length = 512,null=True,blank=True) 
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)
    published = models.DateTimeField() # time of activity
    url = models.URLField(blank=True,null=True)
    content = models.TextField()
    subject_uri = models.CharField(max_length = 512) 
    subject_description = models.TextField(null=True)
    verb_uri = models.CharField(max_length = 512) 
    verb_description = models.TextField(null=True)
    object_uri = models.CharField(max_length = 512, null=True) 
    object_description = models.TextField(null=True)

    def __unicode__(self):
        return "%s%s%s" %(self.published," - ",self.content)
    
    def to_dict(self, compact=False):
        d = dict(
            id=self.pk,
            activity_id=self.activity_id, 
            title=self.title, 
            published=time.mktime(self.published.timetuple()),
            published_v=self.published.ctime(),
            url = self.url,
            content=self.content,
            subject_uri = self.subject_uri,
            subject_description=self.subject_description,
            verb_uri=self.verb_uri,
            verb_description=self.verb_description,
            object_uri=self.object_uri,
            object_description=self.object_description     
        )

           
        return d
    
    class Meta:
        verbose_name_plural = "activity entries" 

#==============================UNIONS====================================#

          
