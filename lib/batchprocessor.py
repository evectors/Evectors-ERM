#!/usr/bin/env python2.5

# django bootstrap

import os
import sys

#sys.path.insert(0, '/opt/python2.5/site-packages')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from django.core.management import setup_environ
import settings
setup_environ(settings)

# end django bootstrap

import time
import datetime
import md5
import logging
import pickle
import settings

from django.db import connection, transaction

from erm.core.models import Entity, Relationship
# from apps.aggregator.models import Feed, CrawlerLog, Entry, EntryHTMLContent, \
#             EntryHTMLSummary, EntryContent, Tag, TagScheme, EntryTag
from lib.process_utils import *

from erm.lib.logger import Logger

BATCH_ITEMS_CHUNK=10
BATCH_PAUSE_SECONDS=10
BATCH_PAUSE_SECONDS_SUBCHUNK=2

DB_TABLES={"entity": {"obj":Entity, "type_field":"type"}, "relationship": {"obj":Relationship, "type_field":"rel_type"}}
class Processor(object):
        
    def __init__(self, 
                 processor_name, 
                 table='entity', 
                 type=None, 
                 chunk_size=BATCH_ITEMS_CHUNK, 
                 sleep_seconds=BATCH_PAUSE_SECONDS, 
                 logger=None, run_forever=True, 
                 logging_level=logging.DEBUG, 
                 item_id=None, 
                 process_all=False, 
                 sql_where="",
                 sleep_seconds_subchunk=BATCH_PAUSE_SECONDS_SUBCHUNK, 
                ):

        self.processor_name = processor_name
        self.table = table
        self.table_props = DB_TABLES.get(table, DB_TABLES['entity'])
        self.table_obj=self.table_props['obj']
        self.type_field=self.table_props['type_field']
        self.date_field = 'modification_date'
        self.chunk_size  =chunk_size
        self.sleep_seconds = sleep_seconds
        self.sleep_seconds_subchunk=sleep_seconds_subchunk
        self.last_parsed_info = None
        self.run_forever = run_forever and not item_id
        self.item_id = item_id
        self.process_all = process_all
        self.sql_where = sql_where
        self.join = ''
        self.type=type
                
        self.logger=Logger(logging_level, "batchprocessor", fl_stdoutlog=True)
        
        pass
    
 
    def saveInfo(self, info):
        pickleToFile('daemon_' + self.processor_name, info)

    def loadInfo(self, default=None):
        try:
            #my_data=pickleFromFile('daemon_' + self.processor_name)
            pickleFile=open(os.path.join(settings.PICKLER_DIR,  'daemon_' + self.processor_name), 'r')
            my_data=pickle.load(pickleFile)
            pickleFile.close()
            self.logger.debug('Info: %s' % (my_data,))
            return my_data
        except Exception, err:
            self.logger.critical('Error loading info: %s - %s' % (Exception, err))
            return default
        
    def process_chunk(self, slow_by=1):
        self.last_parsed_info=self.loadInfo()
        recent_date=None
        try:
            if not self.process_all:
                recent_date=self.last_parsed_info['date']
                self.logger.debug("===>%s" % self.last_parsed_info.get('date', "NULL"))
            else:
                self.process_all=False
        except:
            pass
 
        cursor = connection.cursor()
        items_list=list()
                
        if not self.item_id:
            if recent_date and self.last_parsed_info and self.last_parsed_info.has_key('date') and self.last_parsed_info['date']: 
                query="from core_%s it left join core_%stype t on it.%s_id=t.id where (%s>'%s') order by %s" % (self.table, self.table, self.type_field, self.date_field, self.last_parsed_info['date'], self.date_field)
            else:
                query='from core_%s it left join core_%stype t on it.%s_id=t.id order by %s' % (self.table, self.table, self.type_field, self.date_field)
        else:
            query='from core_%s it where id = %s' % (self.table, self.item_id)
        
        if self.type and self.type!="":
            where_type = "t.slug='%s'" %(self.type)
            if (not self.sql_where) or self.sql_where=="":
                self.sql_where=where_type
            else:
                self.sql_where = "%s and %s" % (self.sql_where, where_type)
            
        if self.sql_where and self.sql_where!="":
            where_pos=query.find("where")
            if where_pos==-1:
                query=query.replace("order", "where %s order" % self.sql_where)
            else:
                query=query.replace("where", "where %s and" % self.sql_where)
        
        self.logger.debug(query)
    
        count_query='select count(*) ' + query
        cursor.execute(count_query)
                
        items_count=cursor.fetchall()[0][0]
        self.logger.debug('count: %s' % items_count)
        
        chunk=0
        
        while chunk*self.chunk_size<items_count:
            self.logger.warning("%s/%s" % (chunk*self.chunk_size, items_count))
            extract_query = ('select it.id,it.%s ' + query + ' limit %s offset %s') % (self.date_field, self.chunk_size, chunk*self.chunk_size)
            self.logger.debug(extract_query)
            
            cursor.execute(extract_query)
            all_items=cursor.fetchall()
            fields = ('id','date')
            new_items = [dict(zip(fields, r)) for r in all_items]

            self.logger.debug("items: %s" % new_items)
            
            if len(new_items):        
                for item in new_items:
                    self.logger.debug('item: %s (%s)' % (item['id'], item['date']))
                    try:
                        items_list+=[self.process_item(self.table_obj.objects.get(id=item['id']))]
                    except Exception, err:
                        self.logger.critical('Error processing item %s: %s' % (item['id'], err))
                        continue
                    if not recent_date and item['date']:
                        recent_date=item['date']
                    elif item['date']:
                        recent_date=max(recent_date, item['date'])
                            
                    self.logger.debug(item)
                try:
                    self.process_subchunk()
                except Exception, err:
                    self.logger.critical('Error processing subchunk: %s' % (err))
                    
                time.sleep(self.sleep_seconds_subchunk)
                
                if not self.last_parsed_info:
                    self.last_parsed_info=dict()
                self.last_parsed_info["date"]= recent_date
                self.saveInfo(self.last_parsed_info)
            else:
                break
            self.logger.debug("--->%s" % recent_date)
            
            chunk+=1
            
        if self.item_id:
            items_list=list()
        return (items_list)
        
    def process_item(self, item):
        self.logger.debug(item.slug)
        return (item.id)
    
    def process_subchunk(self):
        self.logger.debug("subchunk")
        pass

    def process_ended(self):
        self.logger.debug("process ended")
        pass

    def loop(self):        
        processor_running=isAnotherMeRunning("daemon_main_" + self.processor_name)
        if processor_running[0]:
            self.logger.critical("A %s daemon is already running (since %s )! Exiting" % (self.processor_name, processor_running[1][1]))
        else:
            fl_items=True
            while fl_items or self.run_forever:
                flExecute=True
                slow_by=1
                avgLoad = getServerLoad()
                if avgLoad[0]>HIGH_LOAD:
                    self.logger.critical("Load is excessive (%s), skipping." % avgLoad[0])
                    flExecute=False
                elif avgLoad[0]>SAFE_LOAD:
                    self.logger.critical("Load is a bit too high (%s), slowing processing." % avgLoad[0])
                    slow_by=2
                if flExecute:
                    while fl_items:
                        fl_items=len(self.process_chunk(slow_by))>0
                        
                if self.item_id:
                    break
                    
                if  self.run_forever or not flExecute:
                    sleep_seconds=self.sleep_seconds*slow_by
                    self.logger.debug("going to wait %s seconds" % sleep_seconds)
                    time.sleep(sleep_seconds)
                    fl_items=True
            self.process_ended()

HIGH_LOAD=5.0
SAFE_LOAD=3.0
CRITICAL_LOAD=7.0
    
def main():
    my_proc=Processor("Test", 'entity', 'zzubber', run_forever=False)
    my_proc.loop()
if __name__ == '__main__':
    main()
