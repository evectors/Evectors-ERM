from django.conf.urls.defaults import *
from erm.settings import *

urlpatterns = patterns('erm.core.entity_api',
    #dev
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/bounce/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'bounce'),
    #entity_type
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entity_union/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entity_union'),
    #entity_type
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entity_type/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entity_type'),
    #entity_tag_schema
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entity_tag_schema/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entity_tag_schema'),
    #entity_tag
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entity_tag/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entity_tag'),
    #entity
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entity/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entity'),
)

urlpatterns += patterns('erm.core.rel_api',
    #dev
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/rel_bounce/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'bounce'),
    #rel_tag_schema
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/rel_tag_schema/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'rel_tag_schema'),
    #rel_tag
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/rel_tag/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'rel_tag'),
    #rel_type
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/rel_type/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'rel_type'),
     #rel_type_allowed
   (r'^(?P<api_key>[0-9a-zA-Z]{%s})/rel_type_allowed/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'rel_type_allowed'),
     #relationship
   (r'^(?P<api_key>[0-9a-zA-Z]{%s})/relationship/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'relationship'),
)

urlpatterns += patterns('erm.core.manage_api',
    #dev
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/erm_tree/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'erm_tree'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entities_rel/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entities_rel'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/search/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'search'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/get_related_entities/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'get_related_entities'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entity_connector_action/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entity_connector_action'),
)

urlpatterns += patterns('erm.core.activity_api',
    #activity_entry
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/activity/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'activity'),
)

####Dev patterns

urlpatterns += patterns('erm.core.views',
    (r'^core/$', 'index'),
    (r'^xd_receiver\.html$', 'xd_receiver'),
    (r'^test\.html$', 'test'),
#    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/splitter/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'splitter'),
    #(r'(.*)$', 'req_bounce'),
)

