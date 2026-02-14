-- 工艺过程策划表编号表（体系办建账管理）
-- 编号规则：年代(4位) + 工艺部室代码(XXCH) + 顺序号(3位)，如 2015SFCH001
CREATE TABLE IF NOT EXISTS bianhao_gygch (
  id VARCHAR(36) NOT NULL PRIMARY KEY,
  bz VARCHAR(64) DEFAULT NULL COMMENT '所属科室',
  xm VARCHAR(64) DEFAULT NULL COMMENT '编制人',
  bhyear INT NOT NULL COMMENT '年代4位',
  room_code VARCHAR(16) NOT NULL COMMENT '工艺部室代码如SFCH',
  seq INT NOT NULL COMMENT '顺序号',
  bianhao_code VARCHAR(32) NOT NULL COMMENT '完整编号如2015SFCH001',
  neirong VARCHAR(512) DEFAULT NULL COMMENT '编号内容/说明',
  bhtime VARCHAR(32) DEFAULT NULL COMMENT '编号时间'
);
