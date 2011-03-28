from erm.core.models import *

from django.contrib import admin

# ACTIVITIES
class EntityActivityAdmin(admin.ModelAdmin):
    save_on_top=True
    search_fields = ['subject_uri', 'verb_uri', 'object_uri']
admin.site.register(Activity, EntityActivityAdmin)

#ENTITIES

class EntityTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'name', 'items_count')
admin.site.register(EntityType, EntityTypeAdmin)

class EntityTagSchemaAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'name', 'status')
    list_filter=('status',)
    save_as=True
    save_on_top=True
admin.site.register(EntityTagSchema, EntityTagSchemaAdmin)

class EntityTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'slug', 'status', 'items_count')
    list_filter=('status',)
admin.site.register(EntityTag, EntityTagAdmin)

class EntityTagCorrelationInLine(admin.TabularInline):
    model = EntityTagCorrelation
    extra = 1

class EntityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'type', 'uri', 'creation_date', 'modification_date')
    list_filter=('type',)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ['slug', 'name','uri']
    save_as=True
    save_on_top=True
    inlines=(EntityTagCorrelationInLine,)
admin.site.register(Entity, EntityAdmin)

class EntitySchemedTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'items_count', 'object_type', 'tag', 'schema', 'related')
admin.site.register(EntitySchemedTag, EntitySchemedTagAdmin)

#RELATIONSHIPS

class RelationshipTagSchemaAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'name', 'status')
    list_filter=('status',)
    save_as=True
    save_on_top=True
admin.site.register(RelationshipTagSchema, RelationshipTagSchemaAdmin)

class RelationshipTagAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'slug', 'status', 'items_count')
    list_filter=('status',)
admin.site.register(RelationshipTag, RelationshipTagAdmin)

class RelationshipTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'name', 'relationship_count', 'reciprocated')
admin.site.register(RelationshipType, RelationshipTypeAdmin)

class RelationshipTypeAllowedAdmin(admin.ModelAdmin):
    list_display = ('rel_type_name', 'entity_type_from', 'rel_type', 'entity_type_to')
    list_filter=('rel_type', 'entity_type_from', 'entity_type_to')
admin.site.register(RelationshipTypeAllowed, RelationshipTypeAllowedAdmin) 

admin.site.register(Relationship)

class RelationshipSchemedTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'items_count', 'object_type', 'tag', 'schema', 'related')
admin.site.register(RelationshipSchemedTag, RelationshipSchemedTagAdmin)
   
