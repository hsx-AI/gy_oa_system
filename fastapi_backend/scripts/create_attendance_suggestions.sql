-- 智能建议表：上传打卡数据后预生成，按月份读取
-- 执行一次即可创建表（无 suggestion_date，start_time/end_time 为 DATETIME(0) 带日期）

CREATE TABLE IF NOT EXISTS attendance_suggestions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  employee_name VARCHAR(100) NOT NULL COMMENT '员工姓名',
  department VARCHAR(200) NOT NULL COMMENT '部门',
  year INT NOT NULL COMMENT '年份',
  month INT NOT NULL COMMENT '月份 1-12',
  day_type VARCHAR(50) DEFAULT NULL COMMENT '工作日/周末/假期日',
  message TEXT NOT NULL COMMENT '建议内容',
  start_time DATETIME(0) NULL DEFAULT NULL COMMENT '建议时间段开始 YYYY-MM-DD HH:MM:SS',
  end_time DATETIME(0) NULL DEFAULT NULL COMMENT '建议时间段结束 YYYY-MM-DD HH:MM:SS',
  status TINYINT DEFAULT 0 COMMENT '状态码 0=加班 1=缺勤',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lookup (employee_name(50), department(100), year, month)
) COMMENT '考勤智能建议（按人按月存储，上传打卡后生成）';
