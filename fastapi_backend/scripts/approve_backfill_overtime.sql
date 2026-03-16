-- 将补齐脚本插入的加班记录批量设为已通过（jiabanzt=4）
-- 范围：2025-01 ~ 2026-02，仅匹配脚本插入特征（补报 + 平时加班 + 不要换休票 + 待审批）

UPDATE jiaban
SET jiabanzt = 4
WHERE timedate >= '2025-01-01'
  AND timedate <= '2026-02-28'
  AND jiabanzt = 0
  AND jiabanfs = '补报'
  AND jb = '平时加班'
  AND hx = '否';

-- 执行后查看受影响行数确认结果
SELECT
  COUNT(*) AS total_approved
FROM jiaban
WHERE timedate >= '2025-01-01'
  AND timedate <= '2026-02-28'
  AND jiabanzt = 4
  AND jiabanfs = '补报'
  AND jb = '平时加班'
  AND hx = '否';
