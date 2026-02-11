-- ============================================================
-- 为使用 id 的表确保 id 为主键，避免重复 id 导致数据错乱
-- 执行前请先查重：有重复 id 时需先手工去重再执行对应 ALTER
-- 若某表 id 已是主键，ADD PRIMARY KEY 会报 Duplicate key name 'PRIMARY'，可忽略或注释该行
-- 执行方式: mysql -u root -p 数据库名 < ensure_id_primary_key.sql
-- ============================================================

-- ---------- 1. 查重（仅查询，不修改） ----------
-- 以下语句分别执行，有结果则说明该表存在重复 id，需先处理后再执行下方 ALTER
SELECT id, COUNT(*) AS cnt FROM gcsqb GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM qj GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM jiaban GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM hxp GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM gzh GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM bianhao_fl GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM bianhao GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM bianhaogljs GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM bianhaogl GROUP BY id HAVING cnt > 1;
SELECT id, COUNT(*) AS cnt FROM webconfig GROUP BY id HAVING cnt > 1;

-- ---------- 2. gcsqb（公出申请表） ----------
-- 若此前执行过 gcsqb_id_unique.sql 添加了 UNIQUE，请先执行（否则 ADD PRIMARY KEY 可能报错）：
-- ALTER TABLE gcsqb DROP INDEX uk_gcsqb_id;
-- 若 id 为 INT 或短 varchar，先改为可存 32 位 UUID：
-- ALTER TABLE gcsqb MODIFY COLUMN id VARCHAR(36) NOT NULL;ALTER TABLE bianhao_fl MODIFY COLUMN id VARCHAR(36) NOT NULL
ALTER TABLE bwl MODIFY COLUMN id VARCHAR(36) NOT NULL;
SELECT id, CHAR_LENGTH(id) AS len
FROM bianhaogl
WHERE CHAR_LENGTH(id) > 36
ORDER BY len DESC
LIMIT 50;
-- 是否有 NULL / 空串
SELECT
  SUM(id IS NULL) AS null_cnt,
  SUM(id = '') AS empty_cnt
FROM bianhaogl;

-- 是否有重复
SELECT id, COUNT(*) c
FROM bianhaogl
GROUP BY id
HAVING c > 1
LIMIT 50;

ALTER TABLE bwl ADD PRIMARY KEY (ID);

-- ---------- 3. qj（请假表） ----------
-- 若 id 为 INT 且自增，通常已是主键；若未设主键可执行（无重复时）：
ALTER TABLE qj MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE qj ADD PRIMARY KEY (ID);

-- ---------- 4. jiaban（加班表） ----------
ALTER TABLE jiaban MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE jiaban ADD PRIMARY KEY (ID);

-- ---------- 5. hxp（换休票表） ----------
ALTER TABLE hxp MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE hxp ADD PRIMARY KEY (ID);

-- ---------- 6. gzh（工作号表） ----------
ALTER TABLE gzh MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE gzh ADD PRIMARY KEY (ID);

-- ---------- 7. bianhao_fl（技术文件分类） ----------
ALTER TABLE bianhao_fl MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE bianhao_fl ADD PRIMARY KEY (id);

-- ---------- 8. bianhao（编号表） ----------
ALTER TABLE bianhao MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE bianhao ADD PRIMARY KEY (id);

-- ---------- 9. bianhaogljs（编号管理结算？） ----------
ALTER TABLE bianhaogljs MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE bianhaogljs ADD PRIMARY KEY (id);

-- ---------- 10. bianhaogl（编号管理？） ----------
ALTER TABLE bianhaogl MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE bianhaogl ADD PRIMARY KEY (ID);

-- ---------- 11. webconfig（网站配置，通常仅 id=1 一行） ----------
ALTER TABLE webconfig MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE webconfig ADD PRIMARY KEY (ID);

-- ---------- 12. holiday（假期表，若有 id 列） ----------
-- 若表结构为 (date, type) 无 id 则跳过
-- ALTER TABLE holiday ADD PRIMARY KEY (id);

-- ---------- 13. upload_logs（上传日志，若存在该表且有 id） ----------
-- ALTER TABLE upload_logs ADD PRIMARY KEY (id);

-- ---------- 14. attendance_records（考勤记录，若以 id 为主键） ----------
-- 若该表主键为 (employee_id, attendance_date) 等组合则无需对 id 设主键
-- ALTER TABLE attendance_records ADD PRIMARY KEY (id);
ALTER TABLE bianhaogl MODIFY COLUMN id VARCHAR(36) NOT NULL;
ALTER TABLE attendance_records ADD PRIMARY KEY (ID);