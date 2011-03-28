ALTER TABLE core_entity MODIFY `custom_date` datetime NULL;
ALTER IGNORE TABLE core_entity ADD UNIQUE INDEX(`slug`, `type_id`);
ALTER TABLE core_entity ADD `longitude` double precision NULL;
ALTER TABLE core_entity ADD`latitude` double precision NULL;
ALTER TABLE core_entitytype ADD `do_index` bool NOT NULL;
UPDATE core_entitytype SET do_index=1;
