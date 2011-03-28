DROP TABLE `core_relationshiptagcorrelation`;
CREATE TABLE `core_relationshiptagcorrelation` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `object_id` integer NOT NULL,
    `object_tag_id` varchar(255) NOT NULL,
    `object_tag_schema_id` integer NULL,
    `weight` integer NULL
)
;
ALTER TABLE `core_relationshiptagcorrelation` ADD CONSTRAINT object_tag_id_refs_slug_1795db88 FOREIGN KEY (`object_tag_id`) REFERENCES `core_relationshiptag` (`slug`);
ALTER TABLE `core_relationshiptagcorrelation` ADD CONSTRAINT object_tag_schema_id_refs_id_5d922457 FOREIGN KEY (`object_tag_schema_id`) REFERENCES `core_relationshiptagschema` (`id`);
ALTER TABLE `core_relationshiptagcorrelation` ADD CONSTRAINT object_id_refs_id_3f6e9121 FOREIGN KEY (`object_id`) REFERENCES `core_relationship` (`id`);
