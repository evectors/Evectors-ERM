#!/usr/bin/env python2.5

# django bootstrap

import os
import sys

nomad = os.path.dirname(os.path.abspath(__file__))
while not nomad.endswith('/www'):
    print nomad
    if not nomad in sys.path:
        sys.path.insert(0, nomad)
    nomad=os.path.dirname(nomad)

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

from optparse import OptionParser

BATCH_ITEMS_CHUNK=10
BATCH_PAUSE_SECONDS=10
BATCH_PAUSE_SECONDS_SUBCHUNK=2

DB_TABLES={ "entity": {
                "obj":Entity, 
                "type_field":"type"
                }, 
            "relationship": {
                "obj":Relationship, 
                "type_field":"rel_type"
                }
            }

class Processor(object):
        
    def __init__(self, 
                 processor_name, 
                 table='entity', 
                 type=None, 
                 chunk_size=BATCH_ITEMS_CHUNK, 
                 sleep_seconds=BATCH_PAUSE_SECONDS, 
                 logger=None, 
                 run_forever=True, 
                 logging_level='DEBUG', 
                 item_id=None, 
                 process_all=False, 
                 sql_where="",
                 sleep_seconds_subchunk=BATCH_PAUSE_SECONDS_SUBCHUNK, 
                ):

        if logger is not None:
            self.logger=logger
        else:
            self.logger=Logger(logging_level, "batchprocessor", fl_stdoutlog=False, logger_name="batchprocessor")

        self.processor_name = processor_name
        self.table = table
        self.table_props = DB_TABLES.get(table, DB_TABLES['entity'])
        self.table_obj=self.table_props['obj']
        self.type_field=self.table_props['type_field']
        self.date_field = 'modification_date'
        self.chunk_size  =chunk_size
        self.sleep_seconds = sleep_seconds
        self.sleep_seconds_subchunk=sleep_seconds_subchunk
        self.last_parsed_info = self.loadInfo()
        self.run_forever = run_forever and not item_id
        self.item_id = item_id
        self.process_all = process_all
        self.sql_where = sql_where
        self.join = ''
        self.type=type
        self.cursor = connection.cursor()        

    def buildQuery(self):
        if self.item_id is None:
            wheres=list()
    
            if not self.process_all and self.last_parsed_info and self.last_parsed_info.get('last_start', None) is not None:
                wheres.append("(%s>'%s')" % (self.date_field, self.last_parsed_info['last_start']))
                self.logger.info('processing entities of type %s whose %s>%s'  %  (self.type, self.date_field, self.last_parsed_info['last_start']))
            else:
                self.logger.info('processing all entities of type %s'  %  (self.type))

            if "," in self.type:
                wheres.append( "t.slug IN ('%s')" % ("','".join(self.type.split(','))))
            else:
                wheres.append("t.slug='%s'" %(self.type))
            
            self.query_from_where="FROM core_%s it LEFT JOIN core_%stype t ON it.%s_id=t.id WHERE %s order by %s" % (self.table, self.table, self.type_field, ' AND '.join(wheres), self.date_field)

        else:
            if "," in self.item_id:
                self.logger.info('processing entities %s'  %  (self.item_id))
                self.query_from_where="FROM core_%s it WHERE id IN ('%s')" % (self.table, "','".join(self.item_id.split(',')))
            else:
                self.logger.info('processing entity %s'  %  (self.item_id))
                self.query_from_where='FROM core_%s it WHERE id = %s' % (self.table, self.item_id)
        
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
        
    def extract_chunk(self, chunk, items_count):
        self.logger.warning("%s/%s" % (chunk*self.chunk_size, items_count))
        extract_query = ('SELECT it.id ' + self.query_from_where + ' LIMIT %s OFFSET %s') % (self.chunk_size, chunk*self.chunk_size)
        self.logger.debug(extract_query)
        
        self.cursor.execute(extract_query)
        all_items=self.cursor.fetchall()
        return list (item[0] for item in all_items)

    
    def process_chunk(self, slow_by=1):
        
        self.chunk_started_at = datetime.datetime.now()

        self.buildQuery()
        
        items_list=list()

        items_count=0
        
        chunk=0
        
        self.logger.warning("%s items to process" % (items_count))
        
        chunk_items = self.extract_chunk(chunk, items_count)
        chunk+=1
        

        while len(chunk_items)>0:
            
            
            if len(chunk_items) + chunk*self.chunk_size>items_count:
                count_query='SELECT COUNT(*) ' + self.query_from_where
                self.cursor.execute(count_query)
                count_response=self.cursor.fetchall()
                self.logger.debug("==> %s (%s)" % (count_response, count_query))
                items_count=count_response[0][0]
                
                self.logger.debug('count: %s' % items_count)
    
            self.logger.debug("items: %s" % len(chunk_items))
            
            for item in chunk_items:
                self.logger.debug('item: %s' % (item))
                try:
                    items_list+=[self.process_item(self.table_obj.objects.get(id=item))]
                except Exception, err:
                    self.logger.critical('Error processing item %s: %s' % (item, err))
                    continue
                        
                self.logger.debug(item)

            try:
                self.process_subchunk()
            except Exception, err:
                self.logger.error('Error processing subchunk: %s' % (err))
                
            time.sleep(self.sleep_seconds_subchunk)
            
            self.logger.debug("--->%s" % self.chunk_started_at)
            
            chunk_items = self.extract_chunk(chunk, items_count)
            chunk+=1
        
        self.process_all = False
        
                
        if self.item_id:
            items_list=list()
        else:
            if not self.last_parsed_info:
                self.last_parsed_info=dict()
            self.last_parsed_info["last_start"]= self.chunk_started_at
            self.saveInfo(self.last_parsed_info)

        
        return (items_list)
        
    def process_item(self, item):
        self.logger.debug(item.slug)
        return (item.id)
    
    def process_subchunk(self):
        self.logger.debug("subchunk")
        pass

    def process_ended(self):
        self.cursor.close ()
        connection.close()
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
    parser = OptionParser()
    parser.add_option("-r", 
                      "--reprocess", 
                      action="store_true", 
                      dest="process_all", 
                      default=False)
    parser.add_option("-s", 
                      "--singlerun", 
                      action="store_false", 
                      dest="run_forever", 
                      default=True)
    parser.add_option("-n", 
                      "--name", 
                      action="store", 
                      dest="processor_name", 
                      default='Test')
    parser.add_option("-t", 
                      "--type", 
                      action="store", 
                      dest="type", 
                      default='user')
    parser.add_option("-c", 
                      "--chunk_size", 
                      action="store", 
                      dest="chunk_size", 
                      default=BATCH_ITEMS_CHUNK)
    parser.add_option("-p", 
                      "--pause_seconds", 
                      action="store", 
                      dest="sleep_seconds", 
                      default=BATCH_PAUSE_SECONDS)
    parser.add_option("-l", 
                      "--logging_level", 
                      action="store", 
                      dest="logging_level", 
                      default='DEBUG')
    parser.add_option("-q", 
                      "--sleep_seconds_subchunk", 
                      action="store", 
                      dest="sleep_seconds_subchunk", 
                      default=BATCH_PAUSE_SECONDS_SUBCHUNK)
    parser.add_option("-i", 
                      "--item_id", 
                      action="store", 
                      dest="item_id", 
                      default=None)
    opts, args = parser.parse_args()
    
    my_proc=Processor(processor_name=opts.processor_name,
                        type=opts.type,
                        chunk_size=int(opts.chunk_size),
                        sleep_seconds=int(opts.sleep_seconds),
                        run_forever=opts.run_forever,
                        logging_level=opts.logging_level,
                        item_id=opts.item_id,
                        process_all=opts.process_all,
                        sleep_seconds_subchunk=int(opts.sleep_seconds_subchunk)
                        )
    my_proc.loop()

if __name__ == '__main__':
    main()
