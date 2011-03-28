/*ALTER TABLE core_entity DROP label;*/
/*ALTER TABLE core_entitytype ADD slug varchar(255) UNIQUE;*/
/*ALTER TABLE core_entitytype DROP INDEX name;*/
/*UPDATE core_entitytype SET slug = name;*/
/*UPDATE core_entitytype SET name = label;*/
/*ALTER TABLE core_entitytype DROP label;*/
/**/
/*ALTER TABLE core_entitytagschema ADD slug varchar(255) UNIQUE;*/
/*ALTER TABLE core_entitytagschema DROP INDEX name;*/
/*UPDATE core_entitytagschema SET slug = name;*/
/*UPDATE core_entitytagschema SET name = label;*/
/*ALTER TABLE core_entitytagschema DROP label;*/
/**/
/*ALTER TABLE core_relationshiptagschema ADD slug varchar(255) UNIQUE;*/
/*ALTER TABLE core_relationshiptagschema DROP INDEX name;*/
/*UPDATE core_relationshiptagschema SET slug = name;*/
/*UPDATE core_relationshiptagschema SET name = label;*/
/*ALTER TABLE core_relationshiptagschema DROP label;*/
/**/
/*ALTER TABLE datamanager_repository ADD slug varchar(255) UNIQUE;*/
/*ALTER TABLE datamanager_repository DROP INDEX name;*/
/*UPDATE datamanager_repository SET slug = name;*/
/*UPDATE datamanager_repository SET name = label;*/
/*ALTER TABLE datamanager_repository DROP label;*/
/**/
/*ALTER TABLE core_relationshiptype DROP INDEX name;*/
/*ALTER TABLE core_relationshiptype ADD name_reverse varchar(255);*/
/*UPDATE core_relationshiptype SET slug = name;*/
/*UPDATE core_relationshiptype SET name = label;*/
/*UPDATE core_relationshiptype SET name_reverse = label_reverse;*/
/*ALTER TABLE core_relationshiptype DROP label;*/
/*ALTER TABLE core_relationshiptype DROP label_reverse;*/
/**/
/*ALTER TABLE `core_entityunion` MODIFY `slug` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `core_entityunion` MODIFY `name` varchar(255) NULL;*/
/*ALTER TABLE `core_entityunion` MODIFY `status` varchar(1) NOT NULL;*/
/**/
/*ALTER TABLE `core_entitytagschema` MODIFY `slug` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `core_entitytagschema` MODIFY `name` varchar(255) NULL;*/
/*ALTER TABLE `core_entitytagschema` MODIFY `status` varchar(1) NOT NULL;*/
/**/
/*ALTER TABLE `core_entitytag` MODIFY `name` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `core_entitytag` MODIFY `slug` varchar(255) NOT NULL PRIMARY KEY;*/
/*ALTER TABLE `core_entitytag` MODIFY `status` varchar(1) NOT NULL;*/
/*ALTER TABLE `core_entitytag` MODIFY `kind` varchar(10) NULL;*/
/*ALTER TABLE `core_entitytag` MODIFY `items_count` integer NOT NULL;*/
/**/
/*ALTER TABLE `core_entitytagrelatedtag` MODIFY `tag_a_id` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_entitytagrelatedtag` MODIFY `tag_b_id` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_entitytagrelatedtag` MODIFY `rel_count` integer NOT NULL;*/
/**/
/*ALTER TABLE `core_entitytype` MODIFY `slug` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `core_entitytype` MODIFY `name` varchar(255) NULL;*/
/*ALTER TABLE `core_entitytype` MODIFY `items_count` integer NOT NULL;*/
/*ALTER TABLE `core_entitytype` MODIFY `status` varchar(1) NOT NULL;*/
/**/
/*ALTER TABLE `core_entity` MODIFY `name` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_entity` MODIFY `slug` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_entity` MODIFY `uri` varchar(255) NULL;*/
/*ALTER TABLE `core_entity` MODIFY `type_id` integer NOT NULL;*/
/*ALTER TABLE `core_entity` MODIFY `creation_date` datetime NOT NULL;*/
/*ALTER TABLE `core_entity` MODIFY `modification_date` datetime NOT NULL;*/
/*ALTER TABLE `core_entity` MODIFY `status` varchar(1) NOT NULL;*/
/*ALTER TABLE `core_entity` MODIFY `entity_union_id` integer NULL;*/
/**/
/*ALTER TABLE `core_entitytagcorrelation` MODIFY `object_id` integer NOT NULL;*/
/*ALTER TABLE `core_entitytagcorrelation` MODIFY `object_tag_id` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_entitytagcorrelation` MODIFY `object_tag_schema_id` integer NULL;*/
/*ALTER TABLE `core_entitytagcorrelation` MODIFY `weight` integer NULL;*/
/**/
/*ALTER TABLE `core_relationshiptagschema` MODIFY `slug` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `core_relationshiptagschema` MODIFY `name` varchar(32) NULL;*/
/*ALTER TABLE `core_relationshiptagschema` MODIFY `status` varchar(1) NOT NULL;*/
/**/
/*ALTER TABLE `core_relationshiptag` MODIFY `name` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `core_relationshiptag` MODIFY `slug` varchar(255) NOT NULL PRIMARY KEY;*/
/*ALTER TABLE `core_relationshiptag` MODIFY `status` varchar(1) NOT NULL;*/
/*ALTER TABLE `core_relationshiptag` MODIFY `kind` varchar(10) NULL;*/
/*ALTER TABLE `core_relationshiptag` MODIFY `items_count` integer NOT NULL;*/
/**/
/*ALTER TABLE `core_relationshiptagrelatedtag` MODIFY `tag_a_id` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_relationshiptagrelatedtag` MODIFY `tag_b_id` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_relationshiptagrelatedtag` MODIFY `rel_count` integer NOT NULL;*/
/**/
/*ALTER TABLE `core_relationshiptype` MODIFY `slug` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `core_relationshiptype` MODIFY `name` varchar(255) NULL;*/
/*ALTER TABLE `core_relationshiptype` MODIFY `name_reverse` varchar(255) NULL;*/
/*ALTER TABLE `core_relationshiptype` MODIFY `relationship_count` integer NOT NULL;*/
/*ALTER TABLE `core_relationshiptype` MODIFY `status` varchar(1) NOT NULL;*/
/*ALTER TABLE `core_relationshiptype` MODIFY `reciprocated` bool NOT NULL;*/
/**/
/*ALTER TABLE `core_relationshiptypeallowed` MODIFY `rel_type_id` integer NOT NULL;*/
/*ALTER TABLE `core_relationshiptypeallowed` MODIFY `entity_type_from_id` integer NOT NULL;*/
/*ALTER TABLE `core_relationshiptypeallowed` MODIFY `entity_type_to_id` integer NOT NULL;*/
/**/
/*ALTER TABLE `core_relationship` MODIFY `rel_type_id` integer NOT NULL;*/
/*ALTER TABLE `core_relationship` MODIFY `entity_from_id` integer NOT NULL;*/
/*ALTER TABLE `core_relationship` MODIFY `entity_to_id` integer NOT NULL;*/
/*ALTER TABLE `core_relationship` MODIFY `creation_date` datetime NOT NULL;*/
/*ALTER TABLE `core_relationship` MODIFY `modification_date` datetime NOT NULL;*/
/*ALTER TABLE `core_relationship` MODIFY `status` varchar(1) NOT NULL;*/
/**/
/*ALTER TABLE `core_relationshiptagcorrelation` MODIFY `relationship_id` integer NOT NULL;*/
/*ALTER TABLE `core_relationshiptagcorrelation` MODIFY `rel_tag_id` varchar(255) NOT NULL;*/
/*ALTER TABLE `core_relationshiptagcorrelation` MODIFY `rel_tag_schema_id` integer NULL;*/
/*ALTER TABLE `core_relationshiptagcorrelation` MODIFY `weight` integer NULL;*/
/**/
/*ALTER TABLE `core_activity` MODIFY `activity_id` integer NULL;*/
/*ALTER TABLE `core_activity` MODIFY `title` varchar(512) NOT NULL;*/
/*ALTER TABLE `core_activity` MODIFY `creation_date` datetime NOT NULL;*/
/*ALTER TABLE `core_activity` MODIFY `published` datetime NOT NULL;*/
/*ALTER TABLE `core_activity` MODIFY `url` varchar(200) NOT NULL;*/
/*ALTER TABLE `core_activity` MODIFY `content` longtext NOT NULL;*/
/*ALTER TABLE `core_activity` MODIFY `subject_uri` varchar(512) NOT NULL;*/
/*ALTER TABLE `core_activity` MODIFY `subject_description` longtext NULL;*/
/*ALTER TABLE `core_activity` MODIFY `verb_uri` varchar(512) NOT NULL;*/
/*ALTER TABLE `core_activity` MODIFY `verb_description` longtext NULL;*/
/*ALTER TABLE `core_activity` MODIFY `object_uri` varchar(512) NULL;*/
/*ALTER TABLE `core_activity` MODIFY `object_description` longtext NULL;*/
/**/
/*ALTER TABLE `datamanager_repository` MODIFY `slug` varchar(255) NOT NULL UNIQUE;*/
/*ALTER TABLE `datamanager_repository` MODIFY `name` varchar(255) NULL;*/
/*ALTER TABLE `datamanager_repository` MODIFY `status` varchar(1) NOT NULL;*/
/*ALTER TABLE `datamanager_repository` MODIFY `kind` varchar(64) NOT NULL;*/
/*ALTER TABLE `datamanager_repository` MODIFY `entity_type_id` integer NOT NULL UNIQUE;*/
/*ALTER TABLE `datamanager_repository` MODIFY `creation_date` datetime NOT NULL;*/
/*ALTER TABLE `datamanager_repository` MODIFY `modification_date` datetime NOT NULL;*/
/**/
/*ALTER TABLE datamanager_field ADD slug varchar(255);*/
/*UPDATE datamanager_field SET slug = name;*/
/*UPDATE datamanager_field SET name = label;*/
/*ALTER TABLE datamanager_field DROP label;*/
/**/
/*ALTER TABLE `datamanager_field` MODIFY `slug` varchar(255) NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `name` varchar(255) NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `status` varchar(1) NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `kind` varchar(255) NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `blank` bool NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `null` bool NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `editable` bool NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `unique` bool NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `is_key` bool NOT NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `default` varchar(255) NULL;*/
/*ALTER TABLE `datamanager_field` MODIFY `repository_id` integer NOT NULL;*/
/**/
/*