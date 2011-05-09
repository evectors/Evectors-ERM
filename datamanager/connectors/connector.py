from erm.lib.logger import *

class Connector(object):
    
    def __init__(self, object_name=None):
        self.object_name=object_name
        self.fields=dict()
        self.logger=Logger()
        
    def table_exists(self):
        return True
    
    def create_table(self, fields):
        return True
    
    def get_fields(self, fields):
        return self.fields
    
    def get_default_attributes(self):
        return list()

    def get_remote_attributes(self):
        return list()

    def update_fields(self, fields):
        return self.fields
    
    def get_records_count(self):
        return 0
            
    def query(self, query_fields, query_wheres):
        return list()
    
    def get_record(self, entity_id, attributes):
        pass
    
    def add_record(self, entity_id, attributes):
        pass
    
    def set_record(self, entity_id, attributes):
        pass
    
    def delete_record(self, entity_id):
        pass
    
    #example action
#    def eat(self, entity_id, parameters):
#        return {"entity_id":entity_id, "parameters":parameters}