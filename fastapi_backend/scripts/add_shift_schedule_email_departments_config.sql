ALTER TABLE webconfig
  ADD COLUMN shift_schedule_email_departments MEDIUMTEXT NULL
  COMMENT '启用排班邮件功能的科室JSON数组';
