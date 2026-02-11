-- 公出表 gcsqb 增加审批状态字段
-- bldzt: 部领导批示状态 (1=待审批 2=通过 22=驳回)
-- szrzt: 室主任批示状态 (1=待审批 2=通过 22=驳回)
-- 执行方式: mysql -u root -p 数据库名 < add_gcsqb_approval_columns.sql

ALTER TABLE gcsqb ADD COLUMN bldzt INT DEFAULT 1 COMMENT '部领导批示状态 1待审批 2通过 22驳回';
ALTER TABLE gcsqb ADD COLUMN szrzt INT DEFAULT 1 COMMENT '室主任批示状态 1待审批 2通过 22驳回';

-- 可选：审批时间戳（室主任/部领导审批通过或驳回时写入）
ALTER TABLE gcsqb ADD COLUMN szrpztime DATETIME NULL COMMENT '室主任批示时间';
ALTER TABLE gcsqb ADD COLUMN bldpztime DATETIME NULL COMMENT '部领导批示时间';

-- 已有记录若为 NULL，可统一设为待室主任审批
UPDATE gcsqb SET bldzt = 1, szrzt = 1 WHERE bldzt IS NULL AND szrzt IS NULL;
