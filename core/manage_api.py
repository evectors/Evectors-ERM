import erm.core.manage_manager as mm
#import erm.lib.api as api

from erm.core.models import *
from erm.lib.api import *

from erm.settings import *

from erm.lib.api import ApiError, ERROR_CODES

ERROR_CODES["105"]="Method not supported"


class ErmTree(API):
    def get(self):
        return mm.get_erm_tree(self.params)
def erm_tree(request, api_key, **params):
    responder=ErmTree(request, api_key, params)
    return responder.respond()

class ErmEntityRelationships(API):
    def get(self):
        return mm.get_entities_rel(self.params)
def entities_rel(request, api_key, **params):
    responder=ErmEntityRelationships(request, api_key, params)
    return responder.respond()

class ErmSearch(API):
    def get(self):
        return mm.search(self.params)
def search(request, api_key, **params):
    responder=ErmSearch(request, api_key, params)
    return responder.respond()


class ErmRelatedEntities(API):
    def get(self):
        return mm.get_related_entities(self.params)
def get_related_entities(request, api_key, **params):
    responder=ErmRelatedEntities(request, api_key, params)
    return responder.respond()

class EntityConnectorAction(API):
    def add(self):
        return mm.entity_connector_action(self.raw_data)
    def get(self):
        return mm.entity_connector_action(self.params)
    def set(self):
        raise ApiError(None, 105, "PUT")
    def delete(self):
        raise ApiError(None, 105, "DELETE")
def entity_connector_action(request, api_key, **params):
#    return 100
    responder=EntityConnectorAction(request, api_key, params)
    return responder.respond()

class EntityExport(API):
    def add(self):
        return mm.entity_export(self.raw_data)
    def get(self):
        return mm.entity_export(self.params)
    def set(self):
        raise ApiError(None, 105, "PUT")
    def delete(self):
        raise ApiError(None, 105, "DELETE")
def entity_export(request, api_key, **params):
    responder=EntityExport(request, api_key, params)
    return responder.respond()

class TagName(API):
    def get(self):
        return mm.get_tag(self.params)
def get_tag_name(request, api_key, **params):
    responder=TagName(request, api_key, params)
    return responder.respond()

