-- yggl 表增加企业邮箱地址字段
-- 在目标库执行一次即可；若列已存在会报错，可忽略或先删除本语句中的 ADD 段
-- MySQL / MariaDB，字符集 utf8mb4

ALTER TABLE yggl
  ADD COLUMN enterprise_email VARCHAR(255) DEFAULT NULL COMMENT '企业邮箱地址'
  AFTER gh;
