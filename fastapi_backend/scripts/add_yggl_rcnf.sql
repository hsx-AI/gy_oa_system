-- 为 yggl 表增加入职时间字段 rcnf（入厂时间）
-- 执行后再运行 import_employee_rcnf_from_excel.py 导入数据
ALTER TABLE yggl ADD COLUMN rcnf DATE DEFAULT NULL COMMENT '入职/入厂时间';
