-- 月度绩效：每位员工每月一条记录。执行一次即可。
CREATE TABLE IF NOT EXISTS performance_records (
  id BIGINT NOT NULL AUTO_INCREMENT,
  performance_month DATE NOT NULL COMMENT '月份，统一保存为当月1日',
  department VARCHAR(100) NOT NULL COMMENT '班组/科室（yggl.lsys）',
  employee_name VARCHAR(64) NOT NULL,
  job_level VARCHAR(100) NULL COMMENT '来自 demo.employee_info.job_level 的快照',
  score DECIMAL(10,2) NULL,
  marker VARCHAR(20) NULL COMMENT '总师、新入职；有标记不参与排名',
  rank_no INT NULL,
  rank_percent DECIMAL(10,6) NULL,
  performance_grade VARCHAR(4) NULL COMMENT '自动绩效等级：A、B+、B、C；不参与排名时为空',
  created_by VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_performance_month_employee (performance_month, employee_name),
  KEY idx_performance_dept_month (department, performance_month),
  KEY idx_performance_employee_month (employee_name, performance_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工月度绩效';
