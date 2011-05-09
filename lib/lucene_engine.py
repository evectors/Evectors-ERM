import sys, os, stat

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from django.core.management import setup_environ
import settings
setup_environ(settings)

import lucene
import re
import inspect
from lib.logger import Logger

from lib.misc_utils import string_to_slug
import urllib

if lucene.getVMEnv() is None:
    try:
        lucene.initVM(maxheap = settings.LUCENE_MAX_HEAP,
                      initialheap = settings.LUCENE_INITIAL_HEAP, 
                      maxstack = settings.LUCENE_MAX_STACK)
    except Exception, err:
        lucene.initVM()

TAG_SCHEMA_SEPARATOR='xsx'
TAG_MINUS_REPLACEMENT='xmx'
SCHEMA_COLON_REPLACEMENT='xcx'
DOT_REPLACEMENT='xdx'
UNDERSCORE_REPLACEMENT = 'xux'

LUCENE_GLOBAL_FIELD_NAME="_global_search_field"
BLOB_REPLACEMENTS_DICT = {  "0":"xnxzero",
                            "1":"xnxone",
                            "2":"xnxtwo",
                            "3":"xnxthree",
                            "4":"xnxfour",
                            "5":"xnxfive",
                            "6":"xnxsix",
                            "7":"xnxseven",
                            "8":"xnxeight",
                            "9":"xnxnine",
                            }

def multi_replace(replace_dict,text):
    for find_me, replace_with in replace_dict.items():
        text = text.replace(find_me, replace_with)
    return text

class LuceneEngine(object):
    
    def __init__(self, 
                 index_name='generic', 
                 wipe_index=False,
                 analyzer=lucene.SimpleAnalyzer(),
                 ):
        self.logger=Logger(logger_name='lucene')
        self.index_name=index_name
        self.analyzer=analyzer
        self.dir=os.path.join(settings.LUCENE_INDEX_DIR, self.index_name)
        self.new_index=wipe_index
        self.reader=None
        if not os.path.exists(self.dir):
            os.makedirs(self.dir, 0775)
            os.chmod(self.dir, 0775)
            self.new_index=True
        self.JCCEnvObj = lucene.getVMEnv() 
        self.JCCEnvObj.attachCurrentThread()
        self.store = lucene.SimpleFSDirectory(lucene.File(self.dir))
        self.text_blob=""

    def get_writer(self):
        try:
            self.writer = lucene.IndexWriter(self.store, 
                                             self.analyzer, 
                                             self.new_index,
                                             lucene.IndexWriter.MaxFieldLength.LIMITED)
            self.new_index=False
            return True
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
        return False
 
    def get_reader(self):
        try:
            self.reader = lucene.IndexReader.open(self.store, False)
            return True
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
        return False
 
    def get_hit_count(self, keyname, keyvalue):
        searcher = lucene.IndexSearcher(self.store, True)
        _term = lucene.Term(keyname, keyvalue)
        query = lucene.TermQuery(_term)
        hitCount = searcher.search(query, 1).totalHits#len(scoreDocs)
        searcher.close()

        return hitCount
    
    def build_tag_line(self, tag_slug, tag_schema, remove_star=True):
        if tag_schema=="" or tag_schema==None:
            tag_schema="no-schema"
        if not remove_star:
            tag_schema=tag_schema.replace("*", "xxstarxx")
        tag_schema=string_to_slug(urllib.unquote_plus(tag_schema)).replace("-", TAG_MINUS_REPLACEMENT).replace(".", DOT_REPLACEMENT).replace("_", UNDERSCORE_REPLACEMENT)
        if not remove_star:
            tag_schema=tag_schema.replace("xxstarxx", "*")

        return ("%s%s%s" % (tag_slug.replace('-', TAG_MINUS_REPLACEMENT),
                            TAG_SCHEMA_SEPARATOR, 
                            tag_schema))
        
    def build_tags_field(self, tags_list):
        _values=list()
        for _tag in tags_list:
            _tag_line=self.build_tag_line(_tag.get('slug'), _tag.get("schema", "no_schema"))
            self.add_to_blob(_tag.get('slug'))
            _values.append(_tag_line)
        return _values
    
    def add_to_blob(self, text):
        self.text_blob="%s\n%s" % (self.text_blob,multi_replace(BLOB_REPLACEMENTS_DICT, text))
    
    def add_document(self, doc_fields, optimize=False):
        self.logger.debug("lucene_engine going to add")
        try:
            if self.get_writer():
                
                self.text_blob=""
                doc = lucene.Document()
                for _field in doc_fields:
                    _store=lucene.Field.Store.NO
                    if _field.get('store'):
                        _store=lucene.Field.Store.YES
                    _analyze=lucene.Field.Index.NOT_ANALYZED
                    if _field.get('analyze'):
                        _analyze=lucene.Field.Index.ANALYZED
                    _value=_field.get('value')
                    if _field.get('type')=='tags':
                        _value='\n'.join(self.build_tags_field(_value))
                        self.logger.debug(_value)
                    else:
                        self.add_to_blob(_value)
                    doc.add(lucene.Field(_field.get('name'), 
                                         _value,
                                         _store,
                                         _analyze))
                doc.add(lucene.Field(LUCENE_GLOBAL_FIELD_NAME, 
                                     self.text_blob,
                                     lucene.Field.Store.NO,
                                     lucene.Field.Index.ANALYZED))
                self.writer.addDocument(doc, self.analyzer)
                if optimize:
                    self.writer.optimize()
            return True
        except Exception, err:
            self.logger.error("%s: %s - %s" % (Exception, err, doc_fields))
        finally:
            if self.writer:
                self.writer.close()

        return False

    def optimize(self):
        self.logger.debug("lucene_engine going to optimize")
        try:
            if self.get_writer():
                self.writer.optimize()
            return True
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
        finally:
            if self.writer:
                self.writer.close()

        return False

    def delete_document(self, keyname, keyvalue):
        try:
            if self.get_hit_count(keyname, keyvalue)>=1:
                self.reader = lucene.IndexReader.open(self.store, False)
                self.reader.deleteDocuments(lucene.Term(keyname, keyvalue))
            return self.get_hit_count(keyname, keyvalue)==0
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
        finally:
            if self.reader:
                self.reader.close()
        return False
    
    def update_document(self, doc_fields, keyname, keyvalue):
        self.logger.debug("lucene_engine going to update: (%s:%s)" % (keyname, keyvalue))

        try:
            self.delete_document(keyname, keyvalue)
            return self.add_document(doc_fields)
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
        return False
 
    def build_query(self, keys, query_string, type=None, mode='SHOULD'):
        _analyzer=self.analyzer
        
        if type in ('numeric', 'url'):
            _analyzer=lucene.WhitespaceAnalyzer()
            
        _query=None
        
        query_string=query_string.replace(':', '*')
            
        if query_string[:1]=="*":
            query_string=query_string[1:]
        
        if len(keys)>1:
            _flags=list()
            _keys=list()
            for _key in keys:
                if _key[-1:]=='!':
                    _mode='MUST'
                    _key=_key[:-1]
                else:
                    _mode=mode
                _keys.append(_key)
                _flags.append(getattr(lucene.BooleanClause.Occur, _mode))

            _query = lucene.MultiFieldQueryParser.parse(lucene.Version.LUCENE_CURRENT,
                                    query_string, 
                                    _keys,
                                    _flags,
                                    _analyzer)
        elif len(keys)==1:
            _key=keys[0]
            if _key[-1:]=='!':
                _key=_key[:-1]
                mode='MUST'
            _query = lucene.QueryParser(lucene.Version.LUCENE_CURRENT, 
                                        _key,
                                        _analyzer).parse(query_string)      
        return {"query":_query, "mode":mode}          
    
    def build_tags_query(self, tags_list):
        expression=''
        for tag_dict in tags_list:
            _slug = tag_dict.get('slug')
            self.logger.debug("%s" % tag_dict)
            tag_term=self.build_tag_line(_slug.replace("!", " NOT "), tag_dict.get("schema", ""), False)
            if expression!='':
                expression="%s %s %s " % (expression, tag_dict.get('mode', 'OR'), tag_term)
            else:
                expression=tag_term
        return expression

    
    def search(self, 
               fields, 
               queries, 
               sort=[], 
               items_range=[],
               page_size=100, 
               page_num=0, 
               items_limit=None, 
               bool_mode='SHOULD',
               get_query=False,
               preserve_query=False):

        try:
            result=list()
            count=0
            queries_list=list()
            
            should_queries=list()
            must_queries=list()
            
            for single_query in queries:          
                
                try:
                    _query=''
                    keys=single_query.get('fields')
                    query_expr=single_query.get('query')
                    query_mode=single_query.get('mode', bool_mode)
                    query_type=single_query.get('type', 'generic')
                    
                    if keys==[LUCENE_GLOBAL_FIELD_NAME] and query_type is not 'tags' and not preserve_query:
                        if '~' in query_expr:
                            _tilded_list=re.findall('(~[0-9\.]+)', query_expr)
                            _replacement_dict=dict()
                            _reverse_replacement_dict=dict()
                            _pos=0
                            for _item in _tilded_list:
                                _key='xtildex%s' % (multi_replace(BLOB_REPLACEMENTS_DICT, str(_pos)))
                                _replacement_dict[_item] = _key
                                _reverse_replacement_dict[_key] = _item
                                _pos+=1
                            query_expr = multi_replace(_replacement_dict, query_expr)
                            query_expr = multi_replace(BLOB_REPLACEMENTS_DICT, query_expr)
                            query_expr = multi_replace(_reverse_replacement_dict, query_expr)
                        else:
                            query_expr = multi_replace(BLOB_REPLACEMENTS_DICT, query_expr)
                    
                    if query_type=='tags':
                        query_expr=self.build_tags_query(query_expr)
                    if query_mode=='SHOULD':
                        should_queries.append(self.build_query(keys,query_expr, 
                                                         query_type, 
                                                         query_mode))
                    elif query_mode=='MUST':
                        must_queries.append(self.build_query(keys,query_expr, 
                                                         query_type, 
                                                         query_mode))
                    else:
                        queries_list.append(self.build_query(keys,query_expr, 
                                                         query_type, 
                                                         query_mode))
                except Exception, err:
                    self.logger.error("%s: %s (%s)" % (Exception, 
                                                       err, 
                                                       single_query))
                    return ("%s: %s" % (err, single_query))
            
            if len(items_range):
                for _range_query in items_range:
                    try:
                        _query=False
                        if _range_query['kind']=='NUMERIC':
                            _query=lucene.NumericRangeQuery.newIntRange(_range_query['field'], 
                                                  lucene.Integer(int(_range_query['from'])),
                                                  lucene.Integer(int(_range_query['to'])),
                                                  _range_query['inclusive'],
                                                  _range_query['inclusive'])
                        else:
                            _query=lucene.TermRangeQuery(_range_query['field'], 
                                                  str(_range_query['from']),
                                                  str(_range_query['to']),
                                                  _range_query['inclusive'],
                                                  _range_query['inclusive'])
                        if _query:
                            queries_list.append({'query':_query, 'mode':'MUST'})
                    except Exception, err:
                        self.logger.error("%s: %s (%s)" % (Exception, 
                                                           err, 
                                                           _range_query))
                        return ("%s: %s" % (err, _range_query))
                                                                   
            if len(should_queries)>0:
                if len(should_queries)==1:
                    queries_list.append({'query':should_queries[0]['query'], 'mode':"SHOULD"})
                else:
                    _temp_query=lucene.BooleanQuery()
                    for _query in should_queries:
                        _temp_query.add(_query['query'], 
                                         getattr(lucene.BooleanClause.Occur,"SHOULD")
                                         )
                    queries_list.append({'query':_temp_query, 'mode':bool_mode})

            if len(must_queries)>0:
                if len(must_queries)==1:
                    queries_list.append({'query':must_queries[0]['query'], 'mode':"MUST"})
                else:
                    _temp_query=lucene.BooleanQuery()
                    for _query in must_queries:
                        _temp_query.add(_query['query'], 
                                         getattr(lucene.BooleanClause.Occur,"MUST")
                                         )
                    queries_list.append({'query':_temp_query, 'mode':bool_mode})

            if len(queries_list)>0:
                if len(queries_list)==1:
                    global_query=queries_list[0]['query']
                else:
                    global_query=lucene.BooleanQuery()
                    for _query in queries_list:
                        global_query.add(_query['query'], 
                                         getattr(lucene.BooleanClause.Occur,"MUST")
                                         )
                                    
                searcher = lucene.IndexSearcher(self.store, True)
                
                max_hits=min(100, page_size, items_limit)
                hits_to_retrieve=max(max_hits, page_size*(page_num+1))
                
                    
                    
                if len(sort):
                    sort_fields=list()
                    for _item in sort:
                        _reverse=False
                        if _item[:1]=='-':
                            _reverse=True
                            _item=_item[1:]
                        sort_fields.append(lucene.SortField(_item,lucene.SortField.STRING, _reverse))
                    sort_by=lucene.Sort(sort_fields)
                    hits = searcher.search(global_query, None, hits_to_retrieve, sort_by)
                else:
                    hits = searcher.search(global_query, None, hits_to_retrieve)                
                
                count=hits.totalHits
                
                if count>=page_size*page_num:
                    for hit_pos in range(page_size*page_num, min(page_size*(page_num+1), count)):
                        scoreDoc=hits.scoreDocs[hit_pos]
                        result_item=dict()
                        doc = searcher.doc(scoreDoc.doc)
                        for _field in fields:
                            result_item[_field]=doc.get(_field)
                        if len(sort)==0:
                            result_item['lucene_score']=scoreDoc.score
                        else:
                            result_item['lucene_score']=0
                        result.append(result_item)
                searcher.close()   
            else:
                raise Exception, ("No query passed")
            
            result={"count":count, "page":page_num, "docs":result}
            
            if get_query:
                result['query']= "%s - %s" % (queries, global_query) 

            return result
            
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
            return {"count":0, "page":1, "docs":list(), "msg":"%s: %s" % (Exception, err)}
        return False
        
        