from erm.core.models import *
from erm.lib.misc_utils import *
from datetime import date
from datetime import datetime
from erm.lib.api import ApiError, ERROR_CODES
from erm.core.entity_manager import get_entity
   
#===============ACTIVITY ENTRY=============#    

def get_activity(params):       
    
    objects = Activity.objects.all()
    
    if params.has_key('id') and params.get('id'):
        objects = objects.filter(id=params.get('id'))
        
    if params.has_key('activity_id') and params.get('activity_id'):
        objects = objects.filter(activity_id=params.get('activity_id'))
        
    objects=build_text_search(objects, "subject_uri", params)
    objects=build_text_search(objects, "verb_uri", params)
    objects=build_text_search(objects, "object_uri", params)
    objects=build_text_search(objects, "url", params)

    if params.get('entity_rel', '')!='':
        param_chunks=params.get('entity_rel', '').split(">")
        entity_from_type=param_chunks[0]
        rel=param_chunks[1]
        entity_to=param_chunks[2]
        funct_params={'type':entity_from_type, 'rel':"%s>%s" % (rel, entity_to), 'count':'1'}
        entities_count=get_entity(funct_params)
        if entities_count>0:
            funct_params['count']='0'
            funct_params['limit']=entities_count
            entity_objs=get_entity(funct_params)
            slugs_list=[("%s:%s" % (entity_from_type, obj.slug)) for obj in entity_objs]
            objects = objects.filter(subject_uri__in=slugs_list)
        else:
            objects = objects.filter(subject_uri__in=list())
        
    if params.has_key('published_interval') and params.get('published_interval'):
        objects = objects.filter(published__range=params.get('published_interval'))
        
    if params.get('distinct', '')!='':
        return list ( objects.values(params.get('distinct')).distinct());
    else:
        objects = objects.order_by('-published')
    
    #Insert here additional filtering
    list_offset=max(int(params.get('offset', 0)),0)
    list_limit=max(int(params.get('limit', 20)),1)

    #raise Exception, ("%s" % (params.get('subject_description')))

    if int(params.get('count', 0))==1:
        return objects.count()
            

    objectlist = list(objects[list_offset: list_offset+list_limit])
    
    if params.has_key('htmlformat') and params.get('htmlformat'):
        htmlobjectString = ""
        for object in objectlist:
           # htmlobject = object.to_dict()
            htmlobjectString = "%s%s%s%s" %(htmlobjectString,'<li>',object.content,'</li>')
        return htmlobjectString
    
    return list(objects[list_offset: list_offset+list_limit])

def get_entity_data(slug, type):
    objects=Entity.objects.all()
    entity=objects.get(slug=slug,type__slug=type) 
    return entity
    

def add_activity(params):
        try:        
            
            # SUBJECT
            if params.has_key('subject_entity') and params.get('subject_entity'):
                if params.has_key('subject_slug') and params.get('subject_slug') and params.has_key('subject_type') and params.get('subject_type') :
                   if params.has_key('subject_name') and params.get('subject_name') and params.has_key('subject_uri') and params.get('subject_uri'):
                       subject_description = params.get('subject_name')
                       subject_uri = params.get('subject_type') + ':' + params.get('subject_slug')
                       subject_link = params.get('subject_uri');
                   else:
                       entity = get_entity_data(params.get('subject_slug'),params.get('subject_type'))
                       subject_description = entity.name
                       subject_uri = "%s%s%s" %(entity.type.slug,":",entity.slug)
                       subject_link = entity.uri;
                else:
                    raise ApiError(None, 11102, "%s" % params)
            else:
                subject_description = params.get('subject_name')
                subject_uri = params.get('subject_uri')
                subject_link = params.get('subject_uri');
            
                       
            # OBJECT
            if params.has_key('object_entity') and params.get('object_entity'):
                if params.has_key('object_slug') and params.get('object_slug') and params.has_key('object_type') and params.get('object_type') :
                   if params.has_key('object_name') and params.get('object_name') and params.has_key('object_uri') and params.get('object_uri'):
                       object_description = params.get('object_name')
                       object_uri = params.get('object_type') + ':' + params.get('object_slug')
                       object_link = params.has_key('object_uri');
                   else:
                       entity = get_entity_data(params.get('object_slug'),params.get('object_type'))
                       object_description = entity.name
                       object_uri = "%s%s%s" %(entity.type.slug,":",entity.slug)
                       object_link = entity.uri;
                else:
                    raise ApiError(None, 11102, "%s" % params)
            else:
                object_description = params.get('object_name')
                object_uri = params.get('object_uri')
                object_link = params.get('object_uri');
                
            content = ''
            if subject_link != '' and subject_link != None:
                content = "%s%s%s%s%s%s" %(content,'<a href="',subject_link,'">',subject_description,'</a>')
            else:
                content = "%s%s" %(content,subject_description)
            
            content = "%s%s%s%s" %(content,' ', params.get('verb_description'), ' ')
            
            if object_link != '' and object_link != None:
                content = "%s%s%s%s%s%s" %(content,'<a href="',object_link,'">',object_description,'</a>')
            else:
                content = "%s%s" %(content,object_description)
            
           
            new_entry = Activity(
                        activity_id=params.get('activity_id'),
                        title=params.get('title'),
                        published=datetime.fromtimestamp(int(params.get('published'))),
                        url=params.get('url'),
                        content= content,
                        subject_uri= subject_uri,
                        subject_description=subject_description,
                        verb_uri=params.get('verb_uri'),
                        verb_description=params.get('verb_description'),
                        object_uri=object_uri,
                        object_description=object_description
                        
                        )
            new_entry.save()            
           
        except Exception, err:
            raise ApiError(None, 11101, err)
    
        return new_entry
                
def set_activity(raw_data):
    raise Exception, ("Can't modify activity entry attributes")

def del_activity(params):
    raise Exception, ("Can't delete activity entry yet")

#===============SPECIALIZED APIS=============#    

