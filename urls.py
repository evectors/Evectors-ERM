from django.conf.urls.defaults import *
from django.conf import settings
import os

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
    (r'^core/api/', include('erm.core.urls')),
    (r'^dm/api/', include('erm.datamanager.urls')),
	)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(.*)$', 'django.views.static.serve', {'document_root': os.path.join(settings.PROJECT_PATH , 'media')}),
    )

