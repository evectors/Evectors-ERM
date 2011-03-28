ALTER TABLE datamanager_field ADD `searchable` bool NOT NULL;
UPDATE datamanager_field SET searchable=1;

--Denormalization of core_entitytagcorrelation, add and update a new object_type_id column
ALTER TABLE `core_entitytagcorrelation` ADD `object_type_id` integer NOT NULL;
UPDATE `core_entitytagcorrelation` SET `object_type_id`=(SELECT type_id from core_entity where core_entity.id=core_entitytagcorrelation.object_id);
ALTER TABLE `core_entitytagcorrelation` ADD CONSTRAINT object_type_id_refs_id_32f0fc59 FOREIGN KEY (`object_type_id`) REFERENCES `core_entitytype` (`id`);
CREATE INDEX `core_entitytagcorrelation_object_type_id` ON `core_entitytagcorrelation` (`object_type_id`);

--New multi column indexes, for performance, added also to core/sql/ so they will be created when building new installations
CREATE INDEX ce_type_creationdate ON core_entity(type_id,creation_date);
CREATE INDEX ce_type_modificationdate ON core_entity(type_id,modification_date);
CREATE INDEX ce_type_customdate ON core_entity(type_id,custom_date);

CREATE INDEX cetc_tagschemaweight ON core_entitytagcorrelation(object_tag_id,object_tag_schema_id,weight);

--core_entitytagrelatedtag removal, going to use a different (and hopefully better) approach
DROP TABLE `core_entitytagrelatedtag`;

--add the new entityschemedtag table
CREATE TABLE `core_entityschemedtag` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `object_type_id` integer NOT NULL,
    `tag_id` varchar(255) NOT NULL,
    `schema_id` integer NULL,
    `items_count` integer NOT NULL,
    `related` longtext NOT NULL
)
;
ALTER TABLE `core_entityschemedtag` ADD CONSTRAINT tag_id_refs_slug_153c6c51 FOREIGN KEY (`tag_id`) REFERENCES `core_entitytag` (`slug`);
ALTER TABLE `core_entityschemedtag` ADD CONSTRAINT schema_id_refs_id_13f45020 FOREIGN KEY (`schema_id`) REFERENCES `core_entitytagschema` (`id`);
ALTER TABLE `core_entityschemedtag` ADD CONSTRAINT object_type_id_refs_id_20c1adec FOREIGN KEY (`object_type_id`) REFERENCES `core_entitytype` (`id`);

CREATE INDEX `core_entityschemedtag_object_type_id` ON `core_entityschemedtag` (`object_type_id`);
CREATE INDEX cest_items_entitytype_schema ON core_entityschemedtag(items_count,object_type_id, schema_id);

--Denormalization of core_relationshiptagcorrelation, add and update a new object_type_id column
ALTER TABLE `core_relationshiptagcorrelation` ADD `object_type_id` integer NOT NULL;
UPDATE `core_relationshiptagcorrelation` SET `object_type_id`=(SELECT rel_type_id from core_relationship where core_relationship.id=core_relationshiptagcorrelation.object_id);
ALTER TABLE `core_relationshiptagcorrelation` ADD CONSTRAINT object_type_id_refs_id_be999b5 FOREIGN KEY (`object_type_id`) REFERENCES `core_relationshiptype` (`id`);
CREATE INDEX `core_relationshiptagcorrelation_object_type_id` ON `core_relationshiptagcorrelation` (`object_type_id`);

--core_relationshiptagrelatedtag removal, going to use a different (and hopefully better) approach
DROP TABLE `core_relationshiptagrelatedtag`;

--add the new relationshipschemedtag table
CREATE TABLE `core_relationshipschemedtag` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `object_type_id` integer NOT NULL,
    `tag_id` varchar(255) NOT NULL,
    `schema_id` integer NULL,
    `items_count` integer NOT NULL,
    `related` longtext NOT NULL
)
;
ALTER TABLE `core_relationshipschemedtag` ADD CONSTRAINT schema_id_refs_id_5c0ed198 FOREIGN KEY (`schema_id`) REFERENCES `core_relationshiptagschema` (`id`);
ALTER TABLE `core_relationshipschemedtag` ADD CONSTRAINT tag_id_refs_slug_567f5e89 FOREIGN KEY (`tag_id`) REFERENCES `core_relationshiptag` (`slug`);
ALTER TABLE `core_relationshipschemedtag` ADD CONSTRAINT object_type_id_refs_id_3726286a FOREIGN KEY (`object_type_id`) REFERENCES `core_relationshiptype` (`id`);

CREATE INDEX `core_relationshipschemedtag_object_type_id` ON `core_relationshipschemedtag` (`object_type_id`);
CREATE INDEX crst_items_reltype_schema ON core_relationshipschemedtag(items_count,object_type_id, schema_id);

