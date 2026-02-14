-- 部门制度表（制度上传、制度查询、关键词搜索）
-- 支持 PDF、Word(.doc/.docx)、Excel(.xls/.xlsx)
CREATE TABLE IF NOT EXISTS dept_policy (
  id VARCHAR(36) NOT NULL PRIMARY KEY,
  title VARCHAR(256) DEFAULT NULL COMMENT '制度标题',
  keywords VARCHAR(512) DEFAULT NULL COMMENT '关键词，用于搜索，多个用逗号分隔',
  file_name VARCHAR(256) NOT NULL COMMENT '原始文件名',
  file_path VARCHAR(512) NOT NULL COMMENT '存储相对路径，如 policy_files/xxx.pdf',
  file_type VARCHAR(32) NOT NULL COMMENT '文件类型：pdf/doc/docx/xls/xlsx',
  uploader VARCHAR(64) DEFAULT NULL COMMENT '上传人',
  upload_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  issue_time VARCHAR(32) DEFAULT NULL COMMENT '发行时间',
  remark VARCHAR(512) DEFAULT NULL COMMENT '备注'
);
CREATE INDEX IF NOT EXISTS idx_dept_policy_keywords ON dept_policy(keywords(255));
CREATE INDEX IF NOT EXISTS idx_dept_policy_title ON dept_policy(title(128));
CREATE INDEX IF NOT EXISTS idx_dept_policy_upload_time ON dept_policy(upload_time);
