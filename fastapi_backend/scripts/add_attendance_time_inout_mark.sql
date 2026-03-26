-- attendance_records：为 time_1～time_10 各增加「进出」标记列
-- 取值：0=进（进入公司） 1=出（离开公司）；上传时无字面量则按与前一条交替推断，仅写入 0/1
-- 执行前请确认当前库（USE 你的库名;），建议在维护窗口执行。
-- 若某列已存在，对应 ALTER 会报错，可单独注释掉该行后重试。

ALTER TABLE attendance_records
  ADD COLUMN time_1_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_1,
  ADD COLUMN time_2_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_2,
  ADD COLUMN time_3_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_3,
  ADD COLUMN time_4_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_4,
  ADD COLUMN time_5_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_5,
  ADD COLUMN time_6_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_6,
  ADD COLUMN time_7_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_7,
  ADD COLUMN time_8_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_8,
  ADD COLUMN time_9_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_9,
  ADD COLUMN time_10_mark TINYINT NULL DEFAULT NULL COMMENT '进出:0进1出' AFTER time_10;
