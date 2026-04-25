-- yggl 表增加企业邮箱与 IMAP 授权码字段
-- 在目标库执行一次即可；若列已存在可忽略报错
-- MySQL / MariaDB，字符集 utf8mb4

ALTER TABLE yggl
  ADD COLUMN IF NOT EXISTS enterprise_email VARCHAR(255) DEFAULT NULL COMMENT '企业邮箱地址'
  AFTER gh;

ALTER TABLE yggl
  ADD COLUMN IF NOT EXISTS email_auth_code VARCHAR(200) DEFAULT '' COMMENT '企业邮箱IMAP授权码'
  AFTER enterprise_email;
