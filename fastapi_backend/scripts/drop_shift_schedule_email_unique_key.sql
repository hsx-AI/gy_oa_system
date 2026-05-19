ALTER TABLE shift_schedule_email_log DROP INDEX uk_shift_mail_week;
ALTER TABLE shift_schedule_email_log ADD INDEX idx_shift_mail_week (department, week_start, status);
