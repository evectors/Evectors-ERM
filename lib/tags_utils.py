from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
import re
from urllib import unquote

def parse_tag(chunk):
    tag_split=chunk.split("{")
    
    tag=tag_split[0]
    
    schema=unquote(len(tag_split)>1 and tag_split[1][:-1] or "")
    
    return {'tag':tag, 'schema':schema}

def parse_expr(expr):
    or_chunks=list()
    and_chunks=list()
    
    chunks_list=expr.split("||")
    for item in chunks_list:
         if item.find("&&")<0 and item.find("^^")<0:
             or_chunks.append(parse_tag(item))
         else:
            sep="&&"
            if item.find("^^")>0:
                sep='^^'
            and_chunks.append(list(parse_tag(sub_item) for sub_item in item.split(sep)))
    return {"or":or_chunks, "and":and_chunks}

def build_chunk_Q_filter(chunk, tags_table, tagcorrelation_table, TagSchemaObject, schemas_dict):
    qset_inner = Q()

    all_negated=False
    schema_negated=False
    
    tag_key=""
    
    tags=chunk["tag"]
    
    if tags[:1]=="!":
        all_negated=True
        tags=tags[1:]
    
    schema=chunk["schema"]
    
    if schema[:1]=="!":
        schema_negated=True
        schema=schema[1:]
    
    if schema!='' and not unquote(schema) in schemas_dict:
        try:
            schemas_dict[unquote(schema)]=TagSchemaObject.objects.get(slug=unquote(schema)).id
        except ObjectDoesNotExist, err:
            schemas_dict[unquote(schema)]=0
        
    tags_re_list=re.split('((?:[^",]|(?:"(?:\\{2}|\\"|[^"])*?"))*)', tags)
    slugs_list=list()
    for item in tags_re_list:
        if item.strip()!='' and item.strip()!=',':
            slugs_list.append(item.strip())
#                        slugs_list.append(string_to_slug(item.strip()))
    #return slugs_list, schema
    if len(slugs_list):
        _kwargs=dict()
        if len(slugs_list)==1:
            _kwargs["%s__slug" % tags_table]=slugs_list[0]
        else:
            _kwargs["%s__slug__in" % tags_table]=slugs_list
        qset_inner |= Q(**_kwargs)
    
    if schema != '':
        _kwargs=dict()
        _kwargs["%s__object_tag_schema__id" % tagcorrelation_table]=schemas_dict[unquote(schema)]
        if not schema_negated:
            qset_inner &= Q(**_kwargs)
        else:
            qset_inner &= ~Q(**_kwargs)
    
    if all_negated:
        qset_inner = ~qset_inner
    
    return qset_inner
                        

def build_tags_Q_filter(tags_string, tags_table, tagcorrelation_table, TagSchemaObject, objects):
    if tags_string!="":

        expr= parse_expr(tags_string)
        
        or_chunks =expr['or']
        and_chunks = expr['and']
        schemas_dict=dict()
        
        qset = Q()

        if len(or_chunks)>0:
            for chunk in or_chunks:
                qset|= build_chunk_Q_filter(chunk, tags_table, tagcorrelation_table, TagSchemaObject, schemas_dict)

        if len(and_chunks)>0:
            
            for and_chunk in and_chunks:
                
                and_Q_list=list()
                
                for chunk in and_chunk:
                    and_Q_list.append({"Q":build_chunk_Q_filter(chunk, tags_table, tagcorrelation_table, TagSchemaObject, schemas_dict),
                                        "count":0})

#AND would require either multiple joins, that may heavily degrade performances, or more
#sophisticated functions available in django 1.x, that would anyway generate multiple joins
#the following approach is to:
# - sort by the descending results length (the cost of this operation is to extract the count of
#   tags returned by each query)
# - get the list of ids of shortest result and filter the remaining by that list (this requires another query)
# - repeat until the queries reduce to 1
# 
# this is not an optimal approach mostly because the number of queries it requires, but is probably
# not worse than doing possibly lots of useless joins and tries to optimize performances by
# reducing as soon as possible the size of results

                if len(and_Q_list)>1:
                    for and_qset in and_Q_list:
                        and_qset["count"]=objects.filter(and_qset["Q"]).count()
        
                    new_Q_list=[and_Q_list[0]]
                    and_Q_list.sort(lambda a,b: cmp(a['count'], b['count']))
        
                    if and_Q_list[0]['count']==0:
                        return and_Q_list[0]['Q']
                    
                    short_ids_list=list( item['id'] for item in objects.filter(and_Q_list[0]['Q']).values('id'))
                    
                    for _pos in range(len(and_Q_list)-1):
                        new_qset = and_Q_list[_pos+1]['Q'] & Q(id__in=short_ids_list)
                        new_Q_list[0] = {"Q":new_qset, "count":objects.filter(new_qset).count()}
                        short_ids_list=list( item['id'] for item in objects.filter(new_qset).values('id'))
                    and_Q_list = new_Q_list
        
                qset|= and_Q_list[0]['Q']
        
        return qset
    else:
        return None
