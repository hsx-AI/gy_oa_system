-- 部门制度表增加发行时间字段（若已存在则需先删除或跳过）
ALTER TABLE dept_policy ADD COLUMN issue_time VARCHAR(32) DEFAULT NULL COMMENT '发行时间';
