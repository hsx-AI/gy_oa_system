CREATE TABLE IF NOT EXISTS shift_schedule_email_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  department VARCHAR(100) NOT NULL,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  trigger_label VARCHAR(100) NULL,
  recipient_count INT NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'ok',
  message VARCHAR(500) NULL,
  sent_at DATETIME NOT NULL,
  UNIQUE KEY uk_shift_mail_week (department, week_start, status),
  INDEX idx_shift_mail_sent_at (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='周排班自动邮件发送日志';
