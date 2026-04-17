-- 共用邮箱收件箱：配置字段 + 邮件存储表
-- 说明：
-- 1) webconfig 新增共用邮箱配置字段（地址、授权码）
-- 2) 新建 inbox_emails 用于存储收件箱同步的邮件内容

-- webconfig 配置字段（仅首次执行时新增）
ALTER TABLE webconfig
  ADD COLUMN IF NOT EXISTS inbox_email_address VARCHAR(200) DEFAULT '' COMMENT '共用邮箱地址';

ALTER TABLE webconfig
  ADD COLUMN IF NOT EXISTS inbox_email_auth_code VARCHAR(200) DEFAULT '' COMMENT '共用邮箱IMAP授权码';

-- 共用邮箱邮件存储表
CREATE TABLE IF NOT EXISTS inbox_emails (
  id INT AUTO_INCREMENT PRIMARY KEY,
  message_id VARCHAR(500) DEFAULT NULL COMMENT '邮件 Message-ID（用于去重）',
  uid VARCHAR(64) DEFAULT NULL COMMENT 'IMAP 中的 UID',
  subject VARCHAR(500) DEFAULT '' COMMENT '主题',
  from_addr VARCHAR(500) DEFAULT '' COMMENT '发件人（含姓名 <地址>）',
  to_addrs TEXT COMMENT '收件人（逗号分隔）',
  cc_addrs TEXT COMMENT '抄送人（逗号分隔）',
  email_date DATETIME DEFAULT NULL COMMENT '发件时间（邮件头 Date）',
  body_text LONGTEXT COMMENT '纯文本正文',
  body_html LONGTEXT COMMENT 'HTML 正文',
  received_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  UNIQUE KEY uk_message_id (message_id),
  INDEX idx_email_date (email_date),
  INDEX idx_received_at (received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='共用邮箱收件箱';
