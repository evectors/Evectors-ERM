drop database erm_dm_simpledb;
create database erm_dm_simpledb character set utf8 collate utf8_general_ci;
grant all on erm_dm_simpledb.* to 'erm_user'@'localhost' identified by 'erm_pass';