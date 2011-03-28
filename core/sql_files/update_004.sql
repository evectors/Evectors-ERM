ALTER table core_entity ADD `password` varchar(255) NULL;
ALTER table core_entity ADD `custom_date` datetime NOT NULL;
UPDATE core_entity SET custom_date=creation_date;