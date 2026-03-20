-- 排班配置表：每个科室的排班规则
CREATE TABLE IF NOT EXISTS shift_config (
  id INT AUTO_INCREMENT PRIMARY KEY,
  department VARCHAR(100) NOT NULL COMMENT '科室名称（yggl.lsys）',
  workday_night INT NOT NULL DEFAULT 2 COMMENT '工作日夜班安排人数',
  weekend_day INT NOT NULL DEFAULT 2 COMMENT '周末白班安排人数',
  weekend_night INT NOT NULL DEFAULT 2 COMMENT '周末夜班安排人数',
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
  year INT NOT NULL COMMENT '年',
  month INT NOT NULL COMMENT '月',
  updated_by VARCHAR(50) NULL COMMENT '操作人',
  updated_at DATETIME NULL COMMENT '最后修改时间',
  UNIQUE KEY uk_emp_date (employee_name, shift_date),
  INDEX idx_dept_ym (department, year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排班记录';
