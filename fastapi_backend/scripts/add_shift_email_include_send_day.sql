-- 排班邮件区间是否包含发送当天（0=否：次日始；1=是：发送日至下周同日前一天）
ALTER TABLE shift_config
  ADD COLUMN email_include_send_day TINYINT(1) NOT NULL DEFAULT 0
  COMMENT '排班邮件区间是否含发送当天(0=否,次日始;1=是,发送日至下周同日前一天)'
  AFTER email_send_weekday;
