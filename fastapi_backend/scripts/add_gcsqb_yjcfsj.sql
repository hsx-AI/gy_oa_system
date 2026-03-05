-- 为 gcsqb（公出申请表）增加预计出发时间字段 yjcfsj
-- 注意：执行前请先备份数据库。
-- yjcfsj 与 yjfhsj 搭配，用于考勤建议中判断「已处理 / 正在审核」状态，
-- 不再依赖实际返回登记的 gcsj/sjfhtime。

ALTER TABLE gcsqb
  ADD COLUMN yjcfsj DATETIME NULL COMMENT '预计出发时间' AFTER yjfhsj;

