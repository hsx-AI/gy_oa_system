-- 为 webconfig 表增加系统管理员字段 admin1（与 yggl.name 对应，用于数据库管理页权限）
-- 执行后请在 webconfig 中 id=1 的行设置 admin1 = '系统管理员姓名'
ALTER TABLE webconfig ADD COLUMN admin1 VARCHAR(64) DEFAULT NULL COMMENT '系统管理员姓名，对应yggl.name';
