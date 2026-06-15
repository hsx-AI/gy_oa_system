-- yggl 表在 name 字段后增加「真实姓名」，并将现有 name 数据复制过去
-- 在目标库执行一次即可；MySQL / MariaDB，字符集 utf8mb4
-- 若列已存在，第 1 步会报错，可跳过第 1 步，只执行第 2 步 UPDATE

-- 第 1 步：新建字段（紧跟在 name 后面）
ALTER TABLE yggl
  ADD COLUMN `真实姓名` VARCHAR(100) DEFAULT NULL COMMENT '真实姓名'
  AFTER name;

-- 第 2 步：把 name 复制到真实姓名
UPDATE yggl
SET `真实姓名` = name
WHERE name IS NOT NULL
  AND TRIM(name) <> ''
  AND (`真实姓名` IS NULL OR TRIM(`真实姓名`) = '');
