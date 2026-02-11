-- 考勤记录表去重并添加唯一约束，避免同一文件多次上传产生重复数据
-- 运行前请备份 attendance_records 表。在 MySQL 中执行本脚本。

-- 1. 去重：保留每个 (employee_id, attendance_date) 中 id 最小的一条，删除其余
DELETE t1 FROM attendance_records t1
INNER JOIN attendance_records t2
ON t1.employee_id = t2.employee_id AND t1.attendance_date = t2.attendance_date AND t1.id > t2.id;

-- 2. 添加唯一约束
-- 步骤 2.1：检查索引是否存在（可选，仅查询）
SHOW INDEX FROM attendance_records WHERE Key_name = 'uk_employee_date';

-- 步骤 2.2：如果索引已存在，先删除（若不存在会报错，可忽略或跳过）
-- 请根据步骤 2.1 的结果决定是否执行下面这行：
ALTER TABLE attendance_records DROP INDEX uk_employee_date;

-- 步骤 2.3：添加唯一约束。employee_id 若为 TEXT 需前缀长度，如 (employee_id(100), attendance_date)
ALTER TABLE attendance_records ADD UNIQUE KEY uk_employee_date (employee_id(100), attendance_date(20));
ALTER TABLE holiday
  ADD COLUMN festival VARCHAR(50) NULL COMMENT '节日名称：元旦/春节/清明/五一/端午/中秋/国庆等';