import datetime
import time

from django.db import models
from erm.core.models import EntityType
from erm.datamanager.connectors.simple import SimpleDbConnector
from erm.lib.api import ApiError, ERROR_CODES
from urllib import unquote

# Create your models here.
GENERIC_STATUS = (
    ('A', 'Active'),
    ('H', 'Hidden'), 
    ('I', 'Inactive'),
)

REPOSITORY_KIND = (
    ('T', 'Simple Table'),
    ('C', 'Complex database'), 
    ('E', 'External Resource'),
)

FIELD_KIND = (
    ('string', 'string (255 char)'),
    ('short_string', 'string (64 char)'),
    ('long_text', 'long text'),
    ('raw_text', 'raw text'),
    ('json', 'json data'),
    ('integer', 'integer'),
    ('float', 'float'),
    ('char', 'single char'),
    ('boolean', 'boolean'),
    ('datetime', 'datetime'),
    ('time', 'time'),
    ('image', 'image url (255 char)'),
)

#ERROR_CODES=dict()
#=====================generic or common errors=====================#
ERROR_CODES["2100"]="data manage model: ?" 
ERROR_CODES["2104"]="entity manager: Invalid slug"
ERROR_CODES["2105"]="data manager: Invalid Connector"
#=====================add_field=====================#
ERROR_CODES["2200"]="data manage model: Field exists" 
ERROR_CODES["2201"]="data manage model: Field wasn't created" 
ERROR_CODES["2202"]="data manage model: Name is required" 
#=====================set_field=====================#
ERROR_CODES["2300"]="data manage model: Field not found" 
ERROR_CODES["2301"]="data manage model: Error saving field" 
ERROR_CODES["2302"]="data manage model: Name is required" 
#=====================delete_field=====================#
ERROR_CODES["2400"]="data manage model: Field not found" 
ERROR_CODES["2401"]="data manage model: Error deletig field" 
ERROR_CODES["2402"]="data manage model: Name is required" 
#=====================init=====================#
ERROR_CODES["2400"]="data manage model: Database exists" 

class Repository(models.Model):
    slug = models.CharField(max_length=255, blank=False, unique=True, null=False)
    name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=1, choices=GENERIC_STATUS, default='A')
    kind = models.CharField(max_length=64, choices=REPOSITORY_KIND, default='T') 
    entity_type=models.OneToOneField(EntityType)
    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True, auto_now_add=True)
   
    def __unicode__(self):
        if self.name:
            return self.name
        else:
            return self.slug
            
    
    def to_dict(self, compact=False):
        
        
        d = {'id':self.pk, 
                'slug': self.slug, 
                'name': self.name, 
                'status': self.status,
                'kind': self.kind,
                'entity_type': self.entity_type,
                }
        if not compact:
            
            #add fields info here
            
            d['creation_date']=time.mktime(self.creation_date.timetuple())
            d['creation_date_v']=self.creation_date.ctime()
            d['modification_date']=time.mktime(self.modification_date.timetuple())
            d['modification_date_v']=self.modification_date.ctime()
            
            fields=self.get_fields()
            d['fields']=list()
            for field in fields:
                d['fields'].append(field.to_dict())
        return d
    
    def get_field(self, field_slug):
        return Field.objects.get(slug=field_slug, repository=self)
        
    def add_field(self, field_desc):
        try:
            self.get_field(field_desc.get("slug"))
            raise ApiError(None, 2200, field_desc.get("slug"))
        except:
            if field_desc.get('slug') and field_desc.get('slug')!="":
                field=Field(slug=field_desc.get('slug',''), 
                    name=field_desc.get('name',''), 
                    status=field_desc.get('status','A'), 
                    kind=field_desc.get('kind','string'), 
                    blank=field_desc.get('blank',True), 
                    unique=field_desc.get('unique',False), 
                    is_key=field_desc.get('is_key',False), 
                    editable=field_desc.get('editable',True), 
                    default=field_desc.get('default',''),
                    repository=self)
                field.save()
                try:
                    self.get_field(field_desc.get("slug"))
                except:
                    raise ApiError(None, 2201, field_desc.get("slug"))

            else:
                raise ApiError(None, 2202)
    
    def set_field(self, field_desc):
        if field_desc.get('slug') and field_desc.get('slug')!="":

            try:
               field=self.get_field(field_desc.get("slug"))
            except Exception, err:
               raise ApiError(None, 2300, "%s (%s)" % (err, field_desc.get("slug")))
            try:
                #raise ApiError(None, 2100, "%s" % (field.to_dict()))

                field.name=field_desc.get('name',field.name) 
                field.status=field_desc.get('status',field.status)
                field.kind=field_desc.get('kind',field.kind)
                field.blank=field_desc.get('blank',field.blank)
                field.unique=field_desc.get('unique',field.unique)
                field.is_key=field_desc.get('is_key',field.is_key)
                field.editable=field_desc.get('editable',field.editable)
                field.default=field_desc.get('default',field.default)
                field.save()
            except Exception, err:
                raise ApiError(None, 2301, "%s: %s" % (err, field_desc.get('slug')))
        else:
                raise ApiError(None, 2302)

    def del_field(self, field_slug):
        if field_slug and field_slug!="":
            try:
               field=self.get_field(field_slug)
            except:
               raise ApiError(None, 2400)
            try:
                field.delete()
            except Exception, err:
                raise ApiError(None, 2401, "%s: %s" % (err, field_slug))
        else:
                raise ApiError(None, 2402)

    def get_fields(self):
        return Field.objects.filter(repository=self)
    
    def set_fields(self, fields_desc):
        #raise ApiError(None, 100, ">%s" % fields_desc)
        field_slugs=list()
        fields_to_kill=list()
        #fields_desc.append(ENTITY_ID_FIELD)
        for field_desc in fields_desc:
            field_slug=field_desc.get("slug")
            if field_slug[0]!='-':
                
                field_slugs.append(field_slug)
                field=None
                try:
                    field=self.get_field(field_slug)
                except:
                    pass
                if field:
                    self.set_field(field_desc)
                else:
                    self.add_field(field_desc)
            else:
                fields_to_kill.append(field_slug[1:])
        fields_to_delete=Field.objects.filter(repository=self).exclude(slug__in=field_slugs).values('slug')
#        raise ApiError(None, 100, ">%s/%s" % (field_names, fields_to_delete))

        for field_to_delete in fields_to_delete:
            if field_to_delete['slug'] in fields_to_kill:
                self.del_field(field_to_delete['slug'])               
    
    def save(self, fl_update_fields=False):
        super(Repository, self).save()
        connector=self.connector()
        if not connector.table_exists():
            connector.create_table(dict())
        if fl_update_fields:
            fields_dict=dict()
            for field in  self.get_fields():
                field_desc=field.to_dict()
                fields_dict[field_desc.get("slug")]=field_desc
            connector.update_fields(fields_dict)
        
    def delete(self):
        connector=self.connector()
        if connector.table_exists():
            connector.delete_table()
        #raise ApiError(None, 2100)
        super(Repository, self).delete()

    def connector(self, fl_create_table=False, fields_desc=dict()):
        if self.kind=='T':
            connector_obj=SimpleDbConnector("et_%s" % self.entity_type.slug, fl_create_table, fields_desc)
            return connector_obj
        elif self.kind=='C':
            pass
        elif self.kind=='E':
            pass
        else:
            try:
                path=self.kind
                if len(path.split( "."))==1:
                    path="erm.datamanager.connectors.%s" % path
                import_string=('from %s import CustomConnector' % path)
                exec import_string
                connector_obj=CustomConnector("et_custom_%s" % self.entity_type.slug, fl_create_table, fields_desc)
                return connector_obj
            except Exception, err:
                raise ApiError(None, 2105, "%s (%s)" % (err, self.kind))
            
    def get_record(self, entity_id, attributes="*", cache_life=0, fl_set_cache_date=False):
        fields_slugs=Field.objects.filter(repository=self).values("slug")
        fields_list=list()
        atts_list=attributes.split(",")
        for field in fields_slugs:
            if atts_list==['*'] or field['slug'] in atts_list:
                fields_list.append(field['slug'])

        connector=self.connector()
        if cache_life!=0 or fl_set_cache_date:
            values_dict=connector.get_record(entity_id, fields_list, cache_life, fl_set_cache_date)
        else:
            values_dict=connector.get_record(entity_id, fields_list)

        response_dict=dict()
        for key, value in values_dict.items():
            if type(value)==datetime.datetime:
                value=time.mktime(value.timetuple())
            elif type(value)==datetime.timedelta:
                value=str(value)
            response_dict[key]=value
        return response_dict
    
    def add_record(self, entity_id, attributes):
        connector=self.connector()
        connector.add_record(entity_id, attributes)
        pass

    def update_record(self, entity_id, attributes):
        connector=self.connector()
        connector.update_record(entity_id, attributes)
        pass

    def delete_record(self, entity_id):
        connector=self.connector()
        connector.delete_record(entity_id)
        
    def do_action(self, entity_id, action, parameters):
        return getattr(self.connector(), action)(entity_id, parameters)
    
    def search(self, query, entity_id_list=None):
        fields_slugs=Field.objects.filter(repository=self).values("slug")
        fields_list=list()
        for field in fields_slugs:
            fields_list.append(field['slug'])
        connector=self.connector()
        
        query=unquote(query)
        records=connector.search(query, ["entity_id"], entity_id_list)
        #raise ApiError(None, 2100, "%s" % values_dict)
        
#        response_list=list()
#        for values_dict in records:
#            response_dict=dict()
#            for key, value in values_dict.items():
#                if type(value)==datetime.datetime:
#                    value=time.mktime(value.timetuple())
#                elif type(value)==datetime.timedelta:
#                    value=str(value)
#                response_dict[key]=value
#            response_list.append(response_dict)
#        return response.list
        return records

    class Meta:
        verbose_name_plural = "repositories"             

class Field(models.Model):
    slug = models.CharField(max_length=255, blank=False, null=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=1, choices=GENERIC_STATUS, default='A')
    kind =  models.CharField(max_length=255, blank=False, null=False, default="string")
    blank =  models.BooleanField(null=False, default=False)
    null =  models.BooleanField(null=False, default=True)
    editable =  models.BooleanField(null=False, default=False)
    unique =  models.BooleanField(null=False, default=False)
    is_key =  models.BooleanField(null=False, default=False)
    default = models.CharField(max_length=255, blank=True, null=True)
    searchable = models.BooleanField(null=False, default=True)
    repository = models.ForeignKey(Repository)
   
    def __unicode__(self):
        return self.name
    
    def to_dict(self, compact=False):
        
        d = {'id':self.pk, 
                'slug': self.slug, 
                'name': self.name, 
                'status': self.status,
                'kind': self.kind,
                'blank': self.blank,
                'null': self.null,
                'unique': self.unique,
                'is_key': self.is_key,
                'editable': self.editable,
                'default': self.default,
                'searchable':self.searchable,
                }
        return d
