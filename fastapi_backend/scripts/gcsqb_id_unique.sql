-- gcsqb 表 id 唯一性修复
-- 问题：id 非主键且无唯一约束，易重复导致数据错乱。
-- 处理：1) 保证 id 列可存 32 位新 id；2) 为 id 添加唯一约束。
-- 执行前若有重复 id，请先查重并处理后再执行步骤 2。
-- 执行方式: mysql -u root -p 数据库名 < gcsqb_id_unique.sql

-- 1) 查重（仅查询，不修改）：有结果说明存在重复 id，需先手工去重或更新再执行下面 ALTER
-- SELECT id, COUNT(*) AS cnt FROM gcsqb GROUP BY id HAVING cnt > 1;

-- 2) 将 id 改为足够长度并添加唯一约束（新 id 为 32 位 hex）
-- 若当前为 INT 或较短 varchar，先改类型（按需取消注释）：
-- ALTER TABLE gcsqb MODIFY COLUMN id VARCHAR(36) NOT NULL;

ALTER TABLE gcsqb ADD UNIQUE KEY uk_gcsqb_id (id);
