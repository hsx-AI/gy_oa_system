-- 人事管理员：管理驾驶舱权限等同综合技术室主任/副主任（可选全员或任意科室）
ALTER TABLE webconfig
  ADD COLUMN admin2 VARCHAR(64) NULL COMMENT '人事管理员(yggl.name)，管理驾驶舱等同综合技术室主任';
