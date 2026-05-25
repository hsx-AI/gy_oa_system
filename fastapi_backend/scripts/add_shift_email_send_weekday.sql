-- 各科室排班邮件自动发送星期几（0=周一 … 6=周日），发送时间固定 17:00
ALTER TABLE shift_config
  ADD COLUMN email_send_weekday INT NOT NULL DEFAULT 4
  COMMENT '排班邮件自动发送星期几(0=周一…6=周日)，固定17:00发送'
  AFTER email_recipients;
