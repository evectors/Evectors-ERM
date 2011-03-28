from erm.datamanager.models import *

from django.contrib import admin

class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("slug","name","status","kind","entity_type","creation_date","modification_date")
admin.site.register(Repository, RepositoryAdmin)

class FieldAdmin(admin.ModelAdmin):
    list_display = ("slug","name","status","kind","blank","null","editable","unique","is_key","default","searchable","repository")
admin.site.register(Field, FieldAdmin)
