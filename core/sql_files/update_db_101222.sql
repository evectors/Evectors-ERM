-- add series tables
CREATE TABLE IF NOT EXISTS `series_today` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `day` date NOT NULL,
    `name` varchar(512) NULL,
    `json_values` longtext NULL
)
;
CREATE TABLE IF NOT EXISTS `series_history` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `day` date NOT NULL,
    `name` varchar(512) NULL,
    `json_values` longtext NULL
)
;
CREATE TABLE IF NOT EXISTS `series_current` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `day_trimmed` date NOT NULL,
    `length` integer NULL,
    `name` varchar(512) NULL,
    `json_values` longtext NULL
)
;
CREATE TABLE IF NOT EXISTS `series_rule` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(512) NULL,
    `length` integer NULL,
    `creation_date` datetime NOT NULL
)
;

-- Introduction of remote_id field
delimiter '//'

CREATE PROCEDURE add_remote_id() BEGIN
IF NOT EXISTS(
	SELECT * FROM information_schema.COLUMNS
	WHERE COLUMN_NAME='remote_id' AND TABLE_NAME='core_entity' AND TABLE_SCHEMA='erm_db'
	)
	THEN
        ALTER TABLE `erm_db`.`core_entity` ADD remote_id varchar(128);
        ALTER TABLE `erm_db`.`core_entity` ADD UNIQUE (`remote_id`, `type_id`);
        CREATE INDEX `core_entity_remote_id` ON `erm_db`.`core_entity`(`type_id`, `remote_id`);

END IF;
END;
//

delimiter ';'

CALL add_remote_id();

DROP PROCEDURE add_remote_id;

-- drop tag name unicity
ALTER TABLE core_entitytag DROP INDEX name;
ALTER TABLE core_relationshiptag DROP INDEX name;

-- add and index core_entitytagcorrelation.entity_tag_name column

ALTER TABLE `core_entitytagcorrelation` ADD `object_tag_name` varchar(255) NOT NULL;
CREATE INDEX cetc_tagname ON core_entitytagcorrelation(object_tag_schema_id,object_tag_name);
UPDATE core_entitytagcorrelation, core_entitytag SET core_entitytagcorrelation.object_tag_name=core_entitytag.name WHERE core_entitytagcorrelation.object_tag_id=core_entitytag.slug;

-- add and index core_relationshiptagcorrelation.entity_tag_name column

ALTER TABLE `core_relationshiptagcorrelation` ADD `object_tag_name` varchar(255) NOT NULL;
CREATE INDEX crtc_tagname ON core_relationshiptagcorrelation(object_tag_schema_id,object_tag_name);
UPDATE core_relationshiptagcorrelation, core_relationshiptag SET core_relationshiptagcorrelation.object_tag_name=core_relationshiptag.name WHERE core_relationshiptagcorrelation.object_tag_id=core_relationshiptag.slug;

-- add a db updates track table to the db
CREATE TABLE IF NOT EXISTS`db_updates` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `when` timestamp not null default CURRENT_TIMESTAMP,
    `updater_file` varchar(256) not null,
    `comment` varchar(256) not null
    );
    
-- update the db updates table
INSERT INTO db_updates(`updater_file`, `comment`) values ('update_db_101222.sql', 'creation of this table');
INSERT INTO db_updates(`updater_file`, `comment`) values ('update_db_101222.sql', 'add series tables');
INSERT INTO db_updates(`updater_file`, `comment`) values ('update_db_101222.sql', 'add remote_id to core_entity');
INSERT INTO db_updates(`updater_file`, `comment`) values ('update_db_101222.sql', 'unique constraint removal from core_entitytag.name and core_relationshiptag.name');
INSERT INTO db_updates(`updater_file`, `comment`) values ('update_db_101222.sql', 'add and index core_entitytagcorrelation.object_tag_name column');