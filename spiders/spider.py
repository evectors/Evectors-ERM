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
#from apps.aggregator.models import Feed, CrawlerLog, Entry, EntryHTMLContent, \
#            EntryHTMLSummary, EntryContent, Tag, TagScheme, EntryTag
from process_utils import *

BATCH_ITEMS_CHUNK=10
BATCH_SLEEP_SECONDS=1
BATCH_PAUSE_SECONDS=10
BATCH_PAUSE_SECONDS_SUBCHUNK=2

class Spider(object):
        
    def __init__(self, 
                 chunk_size=BATCH_ITEMS_CHUNK, 
                 sleep_seconds=BATCH_SLEEP_SECONDS, 
                 logger=None, 
                 run_forever=True, 
                 logging_level=logging.DEBUG, 
                 item_id=None, 
                 process_all=False, 
                 sql_where=""):
        
        self.name=name
        self.table=table
        self.chunk_size=chunk_size
        self.sleep_seconds=sleep_seconds
        self.last_parsed_info=None
        self.run_forever=run_forever and not item_id
        self.item_id=item_id
        self.process_all=process_all
        self.sql_where=sql_where
        
        if self.table=='entry':
            self.date_field='date_changed'
            self.table_oby=Entry
            self.join=' inner join aggregator_feed ft on ft.id=it.feed_id'
        elif self.table=='feed':
            self.date_field='modified'
            self.table_oby=Feed
            self.join=''
        
        logging.basicConfig(datefmt='%d-%m-%Y %H:%M:%S')
        self.logger = logging.getLogger('evectors.aggregator')
        self.logger.propagate = 0
        self.logger.setLevel(logging_level)
        
        default_formatter = logging.Formatter('%(asctime)s %(process)d %(levelname)-8s %(message)s')
        console_formatter = default_formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging_level)
        console_handler.setFormatter(default_formatter)
        self.logger.addHandler(console_handler)
        pass
    
 
    def saveInfo(self, info):
        pickleToFile('daemon_' + self.name, info)

    def loadInfo(self, default=None):
        try:
            #my_data=pickleFromFile('daemon_' + self.name)
            pickleFile=open(settings.PICKLER_DIR + 'daemon_' + self.name, 'r')
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
        
        #let's update records whose date changed fiels is null
        #transaction.enter_transaction_management()
        #cursor.execute('update aggregator_%s set %s=\'%s\' where %s is NULL' % (self.table, self.date_field, datetime.datetime.now(), self.date_field))
        #transaction.commit()
        #transaction.leave_transaction_management()       
        
        qs = Entry.objects.select_related()
        qs = qs.filter(hidden=False)
        
        if not self.item_id:
            
            if recent_date and self.last_parsed_info and self.last_parsed_info.has_key('date') and self.last_parsed_info['date']: 
                #query="select id,%s from aggregator_%s where (%s>='%s') order by %s  limit %s" % (self.date_field, self.table, self.date_field, self.last_parsed_info['date'], self.date_field, self.chunk_size)
                query="from aggregator_%s it%s where (%s>'%s') order by %s" % (self.table, self.join, self.date_field, self.last_parsed_info['date'], self.date_field)
            else:
                query='from aggregator_%s it%s order by %s' % (self.table, self.join, self.date_field)
        else:
            query='from aggregator_%s it where id = %s' % (self.table, self.item_id)
        
        if self.sql_where and self.sql_where!="":
            where_pos=query.find("where")
            if where_pos==-1:
                #query+=" where " + self.sql_where
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
                    #items_list+=[self.process_item(self.table_oby.objects.get(id=item['id']))]
                    self.logger.debug('item: %s (%s)' % (item['id'], item['date']))
                    try:
                        items_list+=[self.process_item(self.table_oby.objects.get(id=item['id']))]
                    except Exception, err:
                        self.logger.critical('Error processing item %s: %s' % (item['id'], err))
                        continue
                    #items_list+=item
                    if not recent_date and item['date']:
                        recent_date=item['date']
                    elif item['date']:
                        recent_date=max(recent_date, item['date'])
                            
                    #time.sleep(self.sleep_seconds*slow_by)
                    self.logger.debug(item)
                self.process_subchunk()
                try:
                    self.process_subchunk()
                except Exception, err:
                    self.logger.critical('Error processing subchunk: %s' % (err))
                    
                time.sleep(BATCH_PAUSE_SECONDS_SUBCHUNK)
                
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
        self.logger.debug(item.id)
        return (item.id)
    
    def process_subchunk(self):
        pass

    def loop(self):        
        processor_running=isAnotherMeRunning("daemon_main" + self.name)
        if processor_running[0]:
            self.logger.critical("A %s daemon is already running (since %s )! Exiting" % (self.name, processor_running[1][1]))
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
                    sleep_seconds=BATCH_PAUSE_SECONDS*slow_by
                    self.logger.debug("going to wait %s seconds" % sleep_seconds)
                    time.sleep(sleep_seconds)
                    fl_items=True
        pass

HIGH_LOAD=5.0
SAFE_LOAD=3.0
CRITICAL_LOAD=7.0
    
def main():
    my_proc=Spider("Test", 'feed', logger=logger, run_forever=False)
    my_proc.loop()
    #logger.debug("items: %s" % my_proc.process_chunk())
if __name__ == '__main__':
    main()
