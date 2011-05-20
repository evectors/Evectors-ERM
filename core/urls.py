from django.conf.urls.defaults import *
from django.conf import settings
from erm.settings import *

urlpatterns = patterns('erm.core.entity_api',
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
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/tag/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'get_tag_name'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/entity_export/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'entity_export'),
)

urlpatterns += patterns('erm.core.activity_api',
    #activity_entry
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/activity/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'activity'),
)

urlpatterns += patterns('erm.core.series_api',
    #activity_entry
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/series_today/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'series_today'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/series_history/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'series_history'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/series_current/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'series_current'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/series_rule/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'series_rule'),
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/series_keys/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'series_keys'),
)

