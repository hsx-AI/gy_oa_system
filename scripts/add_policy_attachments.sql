-- ============================================================
-- 部门制度表(dept_policy)增加附件字段
-- 执行方式: 在 MySQL 中手动执行本脚本
-- ============================================================

ALTER TABLE dept_policy
  ADD COLUMN attachment_files TEXT NULL COMMENT '附件文件列表(JSON)，格式: [{"name":"存储文件名","original":"原始文件名"},...]'
  AFTER remark;
