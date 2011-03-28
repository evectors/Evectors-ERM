#!/usr/bin/env python
 
# django bootstrap

import os
import stat
import sys

#sys.path.insert(0, '/opt/python2.5/site-packages')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import settings

# if settings.MIXED_DJANGO_ENVIRONMENT:    
#         import sys
#         sys.path.insert(0, settings.AGG_MIXED_DJANGO_INSTALL_PATH)
# 
from django.core.management import setup_environ
setup_environ(settings)

# end django bootstrap

import logging
import logging.handlers
import inspect

class UniversallyWritableRotatingFileHandler(logging.handlers.RotatingFileHandler):

    def doRollover(self):
        """
        Override base class method to make the new log file group writable.
        """
        # Rotate the file first.
        logging.handlers.RotatingFileHandler.doRollover(self)

        # Extend write permission.
        currMode = os.stat(self.baseFilename).st_mode
        os.chmod(self.baseFilename, currMode | (stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO))

def setupFileAndPermission(the_path):
    if not os.path.exists(the_path):
        _file=open(the_path, 'w')
        _file.close()
        currMode = os.stat(the_path).st_mode
        os.chmod(the_path, currMode | (stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO))


class Logger(object):
    """
    This class can be used to manage error logging
        Instantiating Logger with no args makes logging to be saved to different files according to the 
        logging level for example:
            logger=Logger()
            logger.debug(msg) => msg will be saved to settings defined LOG_DIR/LOG_FILE_NAME.log
            logger.log(msg) => msg will be saved to settings defined LOG_DIR/LOG_FILE_NAME.log
            logger.info(msg) => msg will be saved to settings defined LOG_DIR/LOG_FILE_NAME.log
            logger.warning(msg) => msg will be saved to settings defined LOG_DIR/LOG_FILE_NAME_err.log
            logger.error(msg) => msg will be saved to settings defined LOG_DIR/LOG_FILE_NAME_err.log
            logger.critical(msg) => msg will be saved to settings defined LOG_DIR/LOG_FILE_NAME_err.log
        
        to set a minimal level of logging either change settings DEBUG_LEVEL value or pass the level as
        threshold_level param when instantiating Logger class:
            
            logger=Logger('ERROR') => just logger.error and logger.critical messages will be logged
        
        to have the log files saved elsewhere but default /var/log/pages/generic_log[_err].log files
        either pass log_dir and file_name params, or properly set LOG_DIR and LOG_FILE_NAME in settings
        
        to have the logger ouput to stdoutlog either call the log with fl_tostdoutlog set to True or
        set LOG_TO_STDOUTLOG to True in settings
        
        all log calls accept an optional extra_info parameter that will be added to msg when logging if 
        LOG_VERBOSE setting is set to True
    """
     
    def __init__(self, threshold_level=None, file_name=None, log_dir=None, fl_stdoutlog=None, logger_name=None):
        if not logger_name:
            logger_name=getattr(settings, "LOG_LOGGER", "pages_logger")
        self.verbose=getattr(settings, "LOG_VERBOSE", False)
        init_errs=None
        if not (logger_name in logging.Logger.manager.loggerDict):
            if threshold_level==None or not hasattr(logging, threshold_level):
                threshold_level=getattr(settings, "LOG_THRESHOLD","NOTSET")
            threshold_level=getattr(logging, threshold_level)
            if fl_stdoutlog==None:
                fl_stdoutlog=getattr(settings, "LOG_TO_STDOUTLOG", False)
            line_format=getattr(settings, "LOG_FORMAT", '%(asctime)s %(process)d %(levelname)-8s %(message)s')
            date_format=getattr(settings, "LOG_DATE_FORMAT", '%d-%m-%Y %H:%M:%S')
            logging.basicConfig(datefmt=date_format, format=line_format, level=threshold_level)
            if not fl_stdoutlog:
                try:
                    if log_dir==None:
                        log_dir=getattr(settings, "LOG_DIR", "/var/log/pages/")
                    if file_name==None:
                        file_name=getattr(settings, "LOG_FILE_NAME", "generic_log")
                    
                    log_path=log_dir+file_name+".log"
                    setupFileAndPermission(log_path)
                    log_handler = UniversallyWritableRotatingFileHandler(log_path, maxBytes=1024*1024*20, backupCount=5)
                    log_handler.setFormatter(logging.Formatter(line_format))
                    logging.getLogger('').addHandler(log_handler)
    
                    log_path=log_dir+file_name+"_err.log"
                    setupFileAndPermission(log_path)
                    err_handler = UniversallyWritableRotatingFileHandler(log_path, maxBytes=1024*1024*20, backupCount=5)
                    err_handler.setFormatter(logging.Formatter(line_format))
                    err_handler.setLevel(logging.ERROR)
                    logging.getLogger('').addHandler(err_handler)
                    
                    class FilterLog(logging.Filter):
                        def __init__(self, name=None): pass
                        def filter(self, record): 
                            return record.levelno<=logging.WARNING
                            
                    log_filter=FilterLog()
                    log_handler.addFilter(log_filter)
                except Exception, err:
                    init_errs="Log initialization error: %s - %s" % (Exception, err)
                    fl_stdoutlog=True
            if fl_stdoutlog:
                log_handler = logging.StreamHandler(sys.stdout)
                log_handler.setFormatter(logging.Formatter(line_format))
        self.logger = logging.getLogger(logger_name)
        if init_errs:
            try:
                self.logger.error(init_errs)
            except Exception, err:
                pass
            
    def log(self, msg, extra_info=None):
        try:
            if extra_info!=None and self.verbose:
                msg = "%s [%s]" % (msg, extra_info)
            self.logger.info(msg)
        except Exception, err:
            try:
                print("%s - %s" % (Exception, err))
            except Exception, err:
            	pass
    
    def info(self, msg, extra_info=None):
        try:
            if extra_info!=None and self.verbose:
                msg = "%s [%s]" % (msg, extra_info)
            self.logger.info(msg)
        except Exception, err:
            try:
                print("%s - %s" % (Exception, err))
            except Exception, err:
            	pass
    #
    def debug(self, msg, extra_info=None):
        try:
            if extra_info!=None and self.verbose:
                msg = "%s [%s]" % (msg, extra_info)
            self.logger.debug(msg)
        except Exception, err:
            try:
                print("%s - %s" % (Exception, err))
            except Exception, err:
                pass
#
    def warning(self, msg, extra_info=None):
        try:
            if extra_info!=None and self.verbose:
                msg = "%s [%s]" % (msg, extra_info)
            stack_inspect=inspect.stack()[1]
            try:
                funct=os.path.basename(stack_inspect[1])
            except Exception, err:
                funct = 'unknown'
            msg="%s: %s line %s" % (msg, funct, stack_inspect[2])
            self.logger.warning(msg)
        except Exception, err:
            try:
                print("%s - %s" % (Exception, err))
            except Exception, err:
                pass
#
    def error(self, msg, extra_info=None):
        try:
            if extra_info!=None and self.verbose:
                msg = "%s [%s]" % (msg, extra_info)
            stack_inspect=inspect.stack()[1]
            try:
                funct=os.path.basename(stack_inspect[1])
            except Exception, err:
                funct = 'unknown'
            msg="%s: %s line %s" % (msg, funct, stack_inspect[2])
            if self.verbose:
                try:
                    msg="%s - [%s]" % (msg,inspect.trace())
                except Exception, err:
                    msg="%s - [Error extracting trace:%s]" % (msg,err)
            self.logger.error(msg)
        except Exception, err:
            try:
                print("%s - %s" % (Exception, err))
            except Exception, err:
                pass
#
    def critical(self, msg, extra_info=None):
        try:
            if extra_info!=None and self.verbose:
                msg = "%s [%s]" % (msg, extra_info)
            stack_inspect=inspect.stack()[1]
            try:
                funct=os.path.basename(stack_inspect[1])
            except Exception, err:
                funct = 'unknown'
            msg="%s: %s line %s" % (msg, funct, stack_inspect[2])
            if self.verbose:
                try:
                    msg="%s - [%s]" % (msg,inspect.trace())
                except Exception, err:
                    msg="%s - [Error extracting trace:%s]" % (msg,err)
            self.logger.critical(msg)
        except Exception, err:
            try:
                print("%s - %s" % (Exception, err))
            except Exception, err:
                pass
            