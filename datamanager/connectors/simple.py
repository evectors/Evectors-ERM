import MySQLdb
#import atexit
import datetime
import time
import unicodedata        

from erm.datamanager.connectors.connector import Connector
from erm.settings import *
from erm.lib.api import ApiError, ERROR_CODES
from django.utils.encoding import smart_str, smart_unicode

from erm.lib.logger import Logger   

INIT_STATEMENTS = ("SET NAMES UTF8", 
                   "SET AUTOCOMMIT = 0", 
                   "SET @innodb_lock_wait_timeout = 50")

#=====================generic or common errors=====================#
ERROR_CODES["3100"]="simple connector: Missing database"
ERROR_CODES["3101"]="simple connector: Generic error"
ERROR_CODES["3102"]="simple connector: Database error"

#=====================create_table=====================#
ERROR_CODES["3200"]="simple connector: Table exists" 
ERROR_CODES["3201"]="simple connector: Table wasn't created" 
#=====================add_field=====================#
ERROR_CODES["3300"]="simple connector: Field exists" 
ERROR_CODES["3301"]="simple connector: Field wasn't created" 
#=====================set_field=====================#
ERROR_CODES["3400"]="simple connector: Field missing" 
ERROR_CODES["3401"]="simple connector: Field wasn't updated" 
ERROR_CODES["3402"]="simple connector: Unknown field" 
#=====================delete_field=====================#
ERROR_CODES["3500"]="simple connector: Field missing" 
ERROR_CODES["3501"]="simple connector: Field wasn't deleted" 
#=====================init=====================#
ERROR_CODES["3600"]="simple connector: Table exists" 

#=====================delete_table=====================#
ERROR_CODES["3700"]="simple connector: Table missing" 
ERROR_CODES["3701"]="simple connector: Table not deleted" 

#=====================add_record=====================#
ERROR_CODES["3800"]="simple connector: Not null entity id is required" 
ERROR_CODES["3801"]="simple connector: Entity record is already present" 
ERROR_CODES["3802"]="simple connector: Entity record not created" 
ERROR_CODES["3803"]="simple connector: Entity record add issue" 

#=====================update_record=====================#
ERROR_CODES["3900"]="simple connector: Not null entity id is required" 
ERROR_CODES["3901"]="simple connector: Entity record not found" 
ERROR_CODES["3902"]="simple connector: Entity record update issue" 

#=====================delete_record=====================#
ERROR_CODES["3910"]="simple connector: Not null entity id is required" 
ERROR_CODES["3911"]="simple connector: Entity record not deleted" 

#=====================get_record=====================#
ERROR_CODES["3920"]="simple connector: Not null entity id is required" 
ERROR_CODES["3921"]="simple connector: Entity record missing" 

QUERY_CREATE_TABLE="CREATE TABLE `%s`.`%s` (`entity_id` integer NOT NULL PRIMARY KEY); "        
QUERY_DELETE_TABLE="DROP TABLE `%s`.`%s`; "        
QUERY_COUNT_TABLE="""SELECT count(*) 
FROM information_schema.Tables 
WHERE TABLE_SCHEMA='%s' 
AND TABLE_NAME='%s';"""
QUERY_COUNT_DB="""SELECT count(*) 
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME='%s';"""

QUERY_COUNT_FIELD="""SELECT count(*) FROM information_schema.columns WHERE  
TABLE_SCHEMA='%s' AND 
TABLE_NAME='%s' AND 
COLUMN_NAME='%s'"""

QUERY_ADD_FIELD="ALTER TABLE `%s`.`%s` ADD `%s` %s %s;"
QUERY_MODIFY_FIELD="ALTER TABLE `%s`.`%s` MODIFY `%s` %s %s;"
QUERY_DELETE_FIELD ="ALTER TABLE `%s`.`%s` DROP `%s`;"

QUERY_GET_FIELDS_TYPES = """SELECT column_name,column_type FROM information_schema.columns WHERE 
TABLE_SCHEMA='%s' AND 
TABLE_NAME='%s';"""

QUERY_EXTRA_FIELDS="""SELECT COLUMN_NAME FROM information_schema.columns WHERE  
TABLE_SCHEMA='%s' AND 
TABLE_NAME='%s' AND 
COLUMN_NAME NOT IN %s"""
QUERY_ALL_FIELDS="""SELECT COLUMN_NAME FROM information_schema.columns WHERE  
TABLE_SCHEMA='%s' AND 
TABLE_NAME='%s'"""

QUERY_COUNT_RECORDS="SELECT count(*) FROM `%s`.`%s` WHERE %s"
QUERY_ADD_RECORD="INSERT INTO `%s`.`%s` (`%s`) VALUES (%s)"
QUERY_UPDATE_RECORD=u'UPDATE `%s`.`%s` SET %s WHERE `entity_id`=%s'
QUERY_DELETE_RECORD="DELETE FROM `%s`.`%s` WHERE %s"
QUERY_GET_RECORD="SELECT `%s` FROM `%s`.`%s` WHERE %s"

FIELDS_MAP=dict()
FIELDS_MAP['char']='varchar(1)'
FIELDS_MAP['string']='varchar(255)'
FIELDS_MAP['short_string']='varchar(64)'
FIELDS_MAP['long_text']='text'
FIELDS_MAP['raw_text']='text'
FIELDS_MAP['json']='text'
FIELDS_MAP['integer']='int'
FIELDS_MAP['float']='double'
FIELDS_MAP['boolean']='tinyint(1)'
FIELDS_MAP['datetime']='datetime'
FIELDS_MAP['time']='time'
FIELDS_MAP['image']='varchar(255)'

def value_encode_to_query(obj, field_type=None):
    try:
        if field_type:
            if field_type=='varchar(1)':
                return  "'%s'" % MySql_encode(obj)[:1]
            elif field_type=='varchar(255)':
                return  "'%s'" % MySql_encode(obj)[0:254]
            elif field_type=='varchar(64)':
                return  "'%s'" % MySql_encode(obj)[0:63]
            elif field_type=='text':
                return  "'%s'" % MySql_encode(obj)
            elif field_type=='int' or field_type.startswith("int"):
                if obj!=None and obj!="":
                    return "%s" % int(obj)
                else:
                    return "NULL"
            elif field_type=='double':
                if obj!=None and obj!="":
                    return "%s" % float(obj)
                else:
                    return "NULL"
            elif field_type=='tinyint(1)':
                return bool(obj)
            elif field_type=='datetime':
                if not isinstance(obj, datetime.datetime):
                    obj=float(obj)
                    obj=datetime.datetime.fromtimestamp(obj)
                return "'%s'" % obj.strftime('%Y-%m-%d %H:%M:%S')
            elif field_type=='time':
                return  "'%s'" % smart_str(obj)
            else:
                return "'%s'" % MySql_encode(obj)
        else:
            obj_type=type(obj)
            if obj_type==str:
                return "'%s'" % MySql_encode(obj)
            elif obj_type==int or obj_type==float:
                return "%s" % obj
            elif obj_type==datetime:
                return "'%s'" % obj.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return "'%s'" % MySql_encode(obj)
    except Exception, err:
        try:
            raise ApiError(None, 100, "%s converting %s to %s" % (err, obj, field_type))
        except Exception, err:
            raise ApiError(None, 100, "%s - %s" % (err, field_type))

def MySql_encode(s):
    encoded_s=s

    if s:
        try:
            encoded_s = MySQLdb.escape_string(smart_str(s))
        except:
            try:
                encoded_s = s.decode('utf-8', 'replace')#smart_str(s)
            except:
                try:
                    encoded_s = MySQLdb.escape_string(smart_str(s))
                except:
                    encoded_s = MySQLdb.escape_string(unicodedata.normalize('NFKD', smart_str(s).decode('utf-8', 'replace')).encode('ascii', 'ignore'))
    else:
        encoded_s=''
    return encoded_s

class SimpleDbConnector(Connector):
    
    def __init__(self, object_name, fl_create_table=False, fields_desc=None):
        super(SimpleDbConnector, self).__init__(object_name)
        
        try:
            getattr(self, 'fields_desc')
        except:
            self.fields_desc=dict()
        
        kwargs = dict(
            host=DM_DATABASE_HOST, 
            user=DM_DATABASE_USER,
            db=DM_DATABASE_NAME, 
            passwd=DM_DATABASE_PASSWORD,
            charset='utf8', 
            use_unicode=True, 
        )
        self.connection = MySQLdb.connect(**kwargs)
#        atexit.register(self.connection.close)
        self.cursor = self.connection.cursor()
        for statement in INIT_STATEMENTS:
            self.cursor.execute(statement)
        
        if fl_create_table:# and fields_desc and isinstance(fields_desc, dict):
            if not self.table_exists():
                self.create_table(fields_desc)
            else:
                raise ApiError(None, 3600)
    
    def __del__(self):
        self.connection.close()
    
    def do_query(self, query):
        try:
            self.cursor.execute(query)
            #self.connection.commit ()
        except Exception, err:
            if DEBUG_SQL:
                err = "%s (%s)" % (err, query)
            raise Exception(err)

    def transaction_start(self):
        self.cursor.execute('START TRANSACTION;')
#        self.connection.commit ()
        
    def transaction_commit(self):
        self.cursor.execute('COMMIT;')
#        self.connection.commit ()
        
    def transaction_rollback(self):
        self.cursor.execute('ROLLBACK;')
#        self.connection.commit ()
        
    def table_exists(self):
        try:
            self.cursor.execute(QUERY_COUNT_DB % DM_DATABASE_NAME)
            if self.cursor.fetchone()[0]==1:
                self.cursor.execute(QUERY_COUNT_TABLE % (DM_DATABASE_NAME, self.object_name))
                return self.cursor.fetchone()[0]==1
            return False
        except Exception, err:
           raise ApiError(None, 3101, err)
    
    def create_table(self, fields):
        try:
            self.cursor.execute(QUERY_COUNT_DB % DM_DATABASE_NAME)
            if self.cursor.fetchone()[0]==1:
                 if not self.table_exists():
                   #ApiError(None, 3101, QUERY_CREATE_TABLE % (DM_DATABASE_NAME, self.object_name))
    
                   self.do_query(QUERY_CREATE_TABLE % (DM_DATABASE_NAME, self.object_name))
                   #self.connection.commit ()
                   if not self.table_exists():
                       raise ApiError(None, 3201)
                   if fields and len(fields):
                       self.update_fields(fields)
                       self.fields=fields
                 else:
                     raise ApiError(None, 3200)
            else:
                 raise ApiError(None, 3100)
        except Exception, err:
            raise ApiError(None, 3101, err)

    def delete_table(self):
        try:
            if self.table_exists():
                self.do_query(QUERY_DELETE_TABLE % (DM_DATABASE_NAME, self.object_name))
    #            self.connection.commit ()
                if self.table_exists():
                    raise ApiError(None, 3701)
            else:
                raise ApiError(None, 3700)
        except Exception, err:
            raise ApiError(None, 3101, err)

    def update_fields(self, fields):
        try:
            curr_fields=list()
            for key, value in fields.items():
                if not self.field_exists(key):
                    self.add_field(key, value)
                else:
                    self.set_field(key, value)
                curr_fields.append(key)
            if len(curr_fields):
                query=QUERY_EXTRA_FIELDS % (DM_DATABASE_NAME, self.object_name, "('%s')" % "','".join(curr_fields))
                self.cursor.execute(query)
            else:
                self.cursor.execute(QUERY_ALL_FIELDS % (DM_DATABASE_NAME, self.object_name))
            items=self.cursor.fetchall()
            
            for field_name in items:
                if field_name[0]!="entity_id":
                    self.del_field(field_name[0])
        except Exception, err:
            raise ApiError(None, 3101, err)
    
    def get_fields_types(self):
        query=QUERY_GET_FIELDS_TYPES % (DM_DATABASE_NAME, self.object_name)
        self.cursor.execute(query)
        return dict(r for r in self.cursor.fetchall())

    def field_exists(self, field_name):
        try:
            self.cursor.execute(QUERY_COUNT_FIELD % (DM_DATABASE_NAME, self.object_name, field_name))
            return self.cursor.fetchone()[0]==1
        except Exception, err:
           raise ApiError(None, 3101, err)
    
    def add_field(self, field_name, field_desc):
        try:
            if not self.field_exists(field_name):
                self.set_field(field_name, field_desc, QUERY_ADD_FIELD)
                if not self.field_exists(field_name):
                    raise ApiError(None, 3301)
            else:
                raise ApiError(None, 3300)
        except Exception, err:
           raise ApiError(None, 3101, err)
        
    def set_field(self, field_name, field_desc, query=QUERY_MODIFY_FIELD):
        try:
            if self.field_exists(field_name) or query==QUERY_ADD_FIELD:
                kind=field_desc.get('kind', 'string')
                if FIELDS_MAP.has_key(kind):
                    replacements=[DM_DATABASE_NAME, 
                                  self.object_name, 
                                  field_name, 
                                  FIELDS_MAP.get(kind)]
                    
                    options=list()
                    
                    if bool(field_desc.get('null', True)):
                        options.append('NULL')
                    else:
                        options.append('NOT NULL')
                        
                    if bool(field_desc.get('unique', True)):
                        options.append('UNIQUE')
                        
                    if bool(field_desc.get('is_key', True)):
                        options.append('KEY')
                    
                    if not field_desc.has_key('default') and bool(field_desc.get('null', True)):
                        value=None
                    else:
                        if kind=='integer':
                            try:
                                value=int(field_desc.get('default',0))
                            except:
                                value=0
                        elif kind=='float':
                            try:
                                value=float(field_desc.get('default',0))
                            except:
                                value=0
                        elif kind=='datetime':
                            try:
                                time=float(field_desc.get('default',time()))
                                value=datetime.datetime.fromtimestamp(time)
                            except:
                                value=None
                        elif kind=='time':
                            value=field_desc.get('default',"00:00:00")
                        elif kind=='boolean':
                            try:
                                value=bool(field_desc.get('default',False))
                            except:
                                value=False
                        elif kind=='long_text' or kind=='raw_text' or kind=='json':
                             value=None
                        else:
                            value=("'%s'" % field_desc.get('default',""))
                    
                    if value:      
                        options.append("DEFAULT %s" % value)
                    
                    replacements.append(' '.join(options))
                    
                    self.do_query(query % tuple(replacements))
                else:
                    raise ApiError(None, 3402, kind)
            else:
                raise ApiError(None, 3400)
        except Exception, err:
           raise ApiError(None, 3101, err)
        
    def del_field(self, field_name):
        try:
            if self.field_exists(field_name):
                query=QUERY_DELETE_FIELD
                replacements=[DM_DATABASE_NAME, 
                              self.object_name, 
                              field_name]
                
                self.do_query(query % tuple(replacements))
    
                if self.field_exists(field_name):
                    raise ApiError(None, 3501)
        except Exception, err:
           raise ApiError(None, 3101, err)

    def record_exists(self, params_dict):
        try:
            wheres=list()
            fields_types=self.get_fields_types()
            for key, value in params_dict.items():
                wheres.append("%s=%s" % (key, value_encode_to_query(value, fields_types[key])))
            query=QUERY_COUNT_RECORDS % (DM_DATABASE_NAME, self.object_name, " ".join(wheres))
            self.cursor.execute(query)
            cnt=self.cursor.fetchone()[0]
            return cnt>0
        except Exception, err:
            raise ApiError(None, 3101, err)
    
    def add_record(self, entity_id, attributes):
        #raise ApiError(None, 100, entity_id)
        try:
            if entity_id!="":
                if not self.record_exists({"entity_id":entity_id}):
                    fields_types=self.get_fields_types()
                    keys=["entity_id"]
                    values=["%s" % int(entity_id)]
                    for key, value in attributes.items():
                        try:
                            if fields_types.has_key(key):
                                keys.append(key)
                                values.append(smart_unicode(value_encode_to_query(value, fields_types[key])))
                        except Exception, err:
                            raise ApiError(None, 100, "ERROR '%s' normalizing %s" % (err, key))
                    query=smart_unicode(QUERY_ADD_RECORD) % (DM_DATABASE_NAME, self.object_name, "`,`".join(keys),smart_unicode(",".join(values)) )
                    try:
                        self.transaction_start()
                        self.do_query(query)
                        self.transaction_commit()
                    except Exception, err:
                        self.transaction_rollback()
                        raise ApiError(None, 3102, "%s (%s): %s" % (entity_id, err, query))
                    if not self.record_exists({"entity_id":entity_id}):
                        raise ApiError(None, 3802, entity_id)
                else:
                    raise ApiError(None, 3801, entity_id)
            else:
                raise ApiError(None, 3800)
        except Exception, err:
            raise ApiError(None, 3101, err)

    def update_record(self, entity_id, attributes, query=QUERY_UPDATE_RECORD):
        try:
            fields_types=self.get_fields_types()
            if entity_id!="":
                if self.record_exists({"entity_id":entity_id}):# or query==QUERY_ADD_RECORD:
                    set_list=list()
                    for key, value in attributes.items():
                        try:
                            if fields_types.has_key(key):
                                set_list.append("`%s`=%s" % (key, value_encode_to_query(value, fields_types[key])))
                        except Exception, err:
                            pass;
                    
                    if len(set_list):
                        values=smart_unicode(",".join(set_list))
                        query = smart_unicode(query) % (DM_DATABASE_NAME, self.object_name, values, entity_id )
                        try:
                            self.transaction_start()
                            
                            self.do_query(query)

                            #raise ApiError(None, 100, "Artificial error")

                            self.transaction_commit()
                        except Exception, err:
                            self.transaction_rollback()
                            raise ApiError(None, 3102, "%s (%s)" % (entity_id, err))
                else:
                   self.add_record(entity_id, attributes)
                    #raise ApiError(None, 3901, entity_id)
    
            else:
               raise ApiError(None, 3900)
        except Exception, err:
            raise ApiError(None, 3101, err)

    def delete_record(self, entity_id):
        try:
            if entity_id!="":
                if self.record_exists({"entity_id":entity_id}):
                    try:
                        self.transaction_start()
                        self.do_query(QUERY_DELETE_RECORD % (DM_DATABASE_NAME, self.object_name, "entity_id=%s" % entity_id))
                        self.transaction_commit()
                    except Exception, err:
                        self.transaction_rollback()
                        raise ApiError(None, 3102, "%s (%s)" % (entity_id, err))
                    if self.record_exists({"entity_id":entity_id}):
                        raise ApiError(None, 3911, entity_id)
            else:
               raise ApiError(None, 3910)
        except Exception, err:
            raise ApiError(None, 3101, err)
        
    def get_record(self, entity_id, fields_list):
        try:
            if entity_id!="":
                if len(fields_list):
                    if self.record_exists({"entity_id":entity_id}):
                        self.cursor.execute(QUERY_GET_RECORD % ("`,`".join(fields_list), DM_DATABASE_NAME, self.object_name, "entity_id=%s" % entity_id))
                        record=[dict(zip(fields_list, row)) for row in self.cursor.fetchall()]
                        #record=dict(zip(fields_list, row) for row in self.cursor.fetchall())
                        return record[0]
                    else:
                       raise ApiError(None, 3921, entity_id)
                else:
                    return dict()
            else:
               raise ApiError(None, 3920)
        except Exception, err:
           raise ApiError(None, 3101, err)

    def search(self, query, fields_list, entity_id_list=None):
        try:
            where=""
            
            if entity_id_list and len(entity_id_list):
                where="entity_id IN (%s)" % ",".join(entity_id_list)
            
            if where!="" and query!="":
                where = "%s AND " % where
            
            if  query!="":
                 where += query
                 
            if where!="":
                _query=QUERY_GET_RECORD % ("`,`".join(fields_list), DM_DATABASE_NAME, self.object_name, where)
                self.cursor.execute(_query)
                records=[dict(zip(fields_list, row)) for row in self.cursor.fetchall()]
                #record=dict(zip(fields_list, row) for row in self.cursor.fetchall())
                return records
            else:
               raise ApiError(None, 3920)
        except Exception, err:
           raise ApiError(None, 3101, err)
