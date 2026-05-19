ALTER TABLE shift_config
  ADD COLUMN email_recipients TEXT NULL COMMENT '排班邮件收件人JSON [{name,email}]' AFTER weekend_night;
