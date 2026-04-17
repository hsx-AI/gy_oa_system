-- 共用邮箱：基于本地大模型的任务抽取字段
-- 说明：在 inbox_emails 表新增任务抽取相关字段，
-- 每封邮件对应唯一一条记录，用于前端看板滚动展示。

ALTER TABLE inbox_emails
  ADD COLUMN IF NOT EXISTS has_task TINYINT(1) DEFAULT 0 COMMENT '是否包含待办任务（0/1）';

ALTER TABLE inbox_emails
  ADD COLUMN IF NOT EXISTS task_summary TEXT COMMENT '任务摘要（大模型抽取）';

ALTER TABLE inbox_emails
  ADD COLUMN IF NOT EXISTS task_deadline VARCHAR(50) DEFAULT '' COMMENT '任务截止时间（文本，YYYY-MM-DD 或 YYYY-MM-DD HH:mm）';

ALTER TABLE inbox_emails
  ADD COLUMN IF NOT EXISTS task_analysis_status VARCHAR(20) DEFAULT 'pending' COMMENT '分析状态：pending/success/no_task/failed';

ALTER TABLE inbox_emails
  ADD COLUMN IF NOT EXISTS task_analyzed_at DATETIME DEFAULT NULL COMMENT '最近一次分析时间';

ALTER TABLE inbox_emails
  ADD COLUMN IF NOT EXISTS task_analysis_error TEXT COMMENT '最近一次分析的错误信息（若失败）';
