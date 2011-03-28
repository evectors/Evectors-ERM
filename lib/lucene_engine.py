import sys, os, stat

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from django.core.management import setup_environ
import settings
setup_environ(settings)

import lucene
from lib.logger import Logger

lucene.initVM()

TAG_SCHEMA_SEPARATOR='xxsxx'
TAG_MINUS_REPLACEMENT='xxmxx'

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
            os.mkdir(self.dir, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO)
            self.new_index=True
        self.JCCEnvObj = lucene.getVMEnv() 
        self.JCCEnvObj.attachCurrentThread()
        self.store = lucene.SimpleFSDirectory(lucene.File(self.dir))

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
 
    def build_tags_field(self, tags_list):
        _values=list()
        for _tag in tags_list:
            _schema=_tag.get("schema", "no_schema")
            if _schema=="" or _schema==None:
                _schema="no_schema"
            if _schema=="*":
                _schema=""
            _tag_line="%s%s%s" % (_tag.get('slug').replace('-', TAG_MINUS_REPLACEMENT), TAG_SCHEMA_SEPARATOR, _schema.replace(":", ""))
            _values.append(_tag_line)
        return _values
 
    def add_document(self, doc_fields):
        try:
            if self.get_writer():
                
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
                    doc.add(lucene.Field(_field.get('name'), 
                                         _value,
                                         _store,
                                         _analyze))
                self.writer.addDocument(doc, self.analyzer)
                self.writer.optimize()
            return True
        except Exception, err:
            self.logger.error("%s: %s - %s" % (Exception, err, doc_fields))
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
        try:
            self.delete_document(keyname, keyvalue)
            return self.add_document(doc_fields)
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
        return False
 
    def build_query(self, keys, query_string, type=None):
        if query_string[:1]=="*":
            query_string=query_string[1:]
        if len(keys)>1:
            SHOULD = lucene.BooleanClause.Occur.SHOULD
            _flags=[SHOULD for key in keys]
            _query = lucene.MultiFieldQueryParser.parse(lucene.Version.LUCENE_CURRENT,
                                    query_string, keys,
                                    _flags,
                                    self.analyzer)
        elif len(keys)==1:
            _query = lucene.QueryParser(lucene.Version.LUCENE_CURRENT, keys[0],
                     self.analyzer).parse(query_string)      
        return _query          
    
    def build_tags_query(self, tags_list):
        expression=''
        for tag_dict in tags_list:
            _schema=tag_dict.get("schema", "no_schema")
            if _schema=="":
                _schema="no_schema"
            _slug = tag_dict.get('slug')
            tag_term="%s%s%s" % (_slug.replace("!", " NOT ").replace('-', TAG_MINUS_REPLACEMENT), TAG_SCHEMA_SEPARATOR, _schema.replace(":", "")) #
            if expression!='':
                expression="%s %s %s " % (expression, tag_dict.get('mode', 'OR'), tag_term)
            else:
                expression=tag_term
        return expression

    
    def search(self, fields, queries, page_size=100, page_num=0, items_limit=None, bool_mode='SHOULD'):
        try:
            result=list()
            count=0
            queries_list=list()
            
            for single_query in queries:          
                
                try:
                    _query=''
                    keys=single_query.get('fields')
                    query_expr=single_query.get('query')
                    if single_query.get('type')=='tags':
                        query_expr=self.build_tags_query(query_expr)
                    queries_list.append(self.build_query(keys,query_expr))
                except Exception, err:
                    self.logger.error("%s: %s (%s)" % (Exception, err, single_query))
                    return ("%s: %s" % (err, single_query))
                                                            
            if len(queries_list)>0:
                if len(queries_list)==1:
                    global_query=queries_list[0]
                else:
                    global_query=lucene.BooleanQuery()
                    for _query in queries_list:
                        global_query.add(_query, getattr(lucene.BooleanClause.Occur, bool_mode, "SHOULD"))

                searcher = lucene.IndexSearcher(self.store, True)
                
                max_hits=min(100, page_size, items_limit)
                hits_to_retrieve=max(max_hits, page_size*(page_num+1))
                
                hits = searcher.search(global_query, hits_to_retrieve)                
                
                count=hits.totalHits
                
                if count>=page_size*page_num:
                    for hit_pos in range(page_size*page_num, min(page_size*(page_num+1), count)):
                        scoreDoc=hits.scoreDocs[hit_pos]
                        result_item=dict()
                        doc = searcher.doc(scoreDoc.doc)
                        for _field in fields:
                            result_item[_field]=doc.get(_field)
                        result_item['lucene_score']=scoreDoc.score
                        result.append(result_item)
                
            else:
                raise Exception, ("No query passed")
            return {"count":count, "page":page_num, "docs":result}
        except Exception, err:
            self.logger.error("%s: %s" % (Exception, err))
            return {"count":0, "page":1, "docs":list(), "msg":"%s: %s" % (Exception, err)}
        return False
        
        