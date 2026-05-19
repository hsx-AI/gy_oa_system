-- 排班配置表：每个科室的排班规则
CREATE TABLE IF NOT EXISTS shift_config (
  id INT AUTO_INCREMENT PRIMARY KEY,
  department VARCHAR(100) NOT NULL COMMENT '科室名称（yggl.lsys）',
  workday_day INT NOT NULL DEFAULT 2 COMMENT '工作日白班安排人数',
  workday_night INT NOT NULL DEFAULT 2 COMMENT '工作日夜班安排人数',
  weekend_day INT NOT NULL DEFAULT 2 COMMENT '周末白班安排人数',
  weekend_night INT NOT NULL DEFAULT 2 COMMENT '周末夜班安排人数',
  email_recipients TEXT NULL COMMENT '排班邮件收件人JSON [{name,email}]',
  updated_by VARCHAR(50) NULL COMMENT '最后修改人',
  updated_at DATETIME NULL COMMENT '最后修改时间',
  UNIQUE KEY uk_dept (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排班配置';

-- 排班记录表：每人每天的班次
CREATE TABLE IF NOT EXISTS shift_schedule (
  id INT AUTO_INCREMENT PRIMARY KEY,
  department VARCHAR(100) NOT NULL COMMENT '科室',
  employee_name VARCHAR(50) NOT NULL COMMENT '员工姓名',
  shift_date DATE NOT NULL COMMENT '日期',
  shift_type VARCHAR(10) NOT NULL DEFAULT '' COMMENT '班次：白班/夜班/休息/空',
  shift_location VARCHAR(20) NOT NULL DEFAULT '' COMMENT '值班位置：准备组/服务组',
  year INT NOT NULL COMMENT '年',
  month INT NOT NULL COMMENT '月',
  updated_by VARCHAR(50) NULL COMMENT '操作人',
  updated_at DATETIME NULL COMMENT '最后修改时间',
  UNIQUE KEY uk_emp_date (employee_name, shift_date),
  INDEX idx_dept_ym (department, year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排班记录';

CREATE TABLE IF NOT EXISTS shift_day_plan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  department VARCHAR(100) NOT NULL,
  plan_date DATE NOT NULL,
  content TEXT NULL,
  updated_by VARCHAR(50) NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uk_dept_plan_date (department, plan_date),
  INDEX idx_dept_date (department, plan_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排班日工作计划';

CREATE TABLE IF NOT EXISTS shift_day_lock (
  id INT AUTO_INCREMENT PRIMARY KEY,
  department VARCHAR(100) NOT NULL,
  lock_date DATE NOT NULL,
  is_open TINYINT(1) NOT NULL DEFAULT 0,
  opened_by VARCHAR(50) NULL,
  opened_at DATETIME NULL,
  UNIQUE KEY uk_dept_lock_date (department, lock_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排班日期开放配置';

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
  INDEX idx_shift_mail_week (department, week_start, status),
  INDEX idx_shift_mail_sent_at (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='周排班自动邮件发送日志';
