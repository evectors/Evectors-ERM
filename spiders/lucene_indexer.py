#!/usr/bin/env python

# django bootstrap

import os
import sys

#sys.path.insert(0, '/opt/python2.5/site-packages')
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from django.core.management import setup_environ
import erm.settings
setup_environ(erm.settings)

# end django bootstrap

from erm.lib.batchprocessor import Processor 
from inspect import getfile, getsourcefile, getmodule
from optparse import OptionParser

import logging

from erm.lib.misc_utils import *
from erm.core.search_engine import SearchEngine

BATCH_ITEMS_CHUNK=100
BATCH_SLEEP_SECONDS=10
BATCH_SLEEP_SUBCHUNK_SECONDS=1

class Procedure(Processor):
    
    def __init__(self, 
                 name, 
                 table,
                 type=None, 
                 chunk_size=BATCH_ITEMS_CHUNK, 
                 sleep_seconds=BATCH_SLEEP_SECONDS, 
                 sleep_seconds_subchunk=BATCH_SLEEP_SUBCHUNK_SECONDS,
                 logger=None, 
                 run_forever=True, 
                 logging_level="DEBUG", 
                 item_id=None, 
                 process_all=False, 
                 sql_where=""
                 ):
                
        super(Procedure, self).__init__(processor_name=name, 
                                        table=table,
                                        type=type,
                                        chunk_size=chunk_size, 
                                        sleep_seconds=sleep_seconds, 
                                        logger=logger, 
                                        run_forever=run_forever, 
                                        logging_level=logging_level, 
                                        item_id=item_id, 
                                        process_all=process_all, 
                                        sql_where=sql_where,
                                        sleep_seconds_subchunk=sleep_seconds_subchunk,
                                        )
        self.reset_index=self.process_all
        self.add_items=self.reset_index
        self.type=type
        self.engine=SearchEngine(self.type, self.reset_index)
         
    def process_item(self, entity):
        if self.add_items:
            self.engine.add_entity(entity)
        else:
            self.engine.update_entity(entity)
        self.reset_index=False


def main():
    
    my_file_name = getfile(main).split("/")[-1:][0]
    my_name = my_file_name.split(".")[:1][0]
    
    USAGE = ("usage: %s [options] [filter]" % my_file_name)
    
    parser = OptionParser(USAGE)

    parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False,
        help="show (and log) debug messages")
    parser.add_option("-i", "--id", action="store", dest="item_id", default=None,
        help="Id of item to process")
    parser.add_option("-r", "--restart", action="store_true", dest="process_all", default=False,
        help="start processing from the first entry")
    parser.add_option("-s", "--singlerun", action="store_true", dest="single_run", default=False,
        help="Run a single cycle")
    parser.add_option("-t", "--type", action="store", dest="type", default="",
        help="entity type to process")
    parser.add_option("--sleep", action="store", dest="sleep_seconds", default=BATCH_SLEEP_SECONDS,
        help="pause time after each process loop")
    parser.add_option("--sleepsubchunk", action="store", dest="sleep_seconds_subchunk", default="1",
        help="pause time after each subchunk loop")
    parser.add_option("--chunksize", action="store", dest="chunk_size", default=BATCH_ITEMS_CHUNK,
        help="items to process in each chunk")
    
    opts, args = parser.parse_args()

    if opts.debug:
        logging_level = "DEBUG"
    else:
        logging_level = "WARNING"
    
    opts.sleep_seconds=int(opts.sleep_seconds)
    opts.sleep_seconds_subchunk=int(opts.sleep_seconds_subchunk)
    opts.chunk_size=int(opts.chunk_size)
   
    if opts.type!="":
        my_proc=Procedure(my_name, \
                          'entity', \
                          opts.type,\
                          run_forever=not opts.single_run, \
                          logging_level=logging_level, \
                          item_id=opts.item_id, \
                          process_all=opts.process_all,\
                          sleep_seconds=opts.sleep_seconds,\
                          sleep_seconds_subchunk=opts.sleep_seconds_subchunk,\
                          chunk_size=opts.chunk_size,
                          )
        
        my_proc.logger.warning("%s" % opts)
    
        my_proc.loop()
    else:
        raise Exception("Entity type (option -t) is required")
    #logger.debug("items: %s" % my_proc.process_chunk())
if __name__ == '__main__':
    main()


