-- 为 gcsqb（公出申请表）增加公出类型字段，取值：市内公出、境内公出、境外公出
-- 执行前请备份。老数据该列为 NULL 或空时，前端可显示为「境内公出」或「—」。

ALTER TABLE gcsqb
  ADD COLUMN gclx VARCHAR(20) DEFAULT NULL COMMENT '公出类型：市内公出/境内公出/境外公出' AFTER id;
