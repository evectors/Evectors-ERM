drop database erm_db;
create database erm_db character set utf8 collate utf8_general_ci;
grant all on erm_db.* to 'erm_user'@'localhost' identified by 'erm_pass';