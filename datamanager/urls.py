from django.conf.urls.defaults import *
from erm.settings import *

urlpatterns = patterns('erm.datamanager.dm_api',
    #dev
    (r'^(?P<api_key>[0-9a-zA-Z]{%s})/bounce/(?:(?P<params>[^/]+))?' % SECRET_KEY_LENGTH, 'bounce'),
    #dev
)