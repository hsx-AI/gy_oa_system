-- 生产数字化编号表
-- 编号规则：生产数字化（项目缩写）纪字【年份】xx号
-- 如：生产数字化（线）纪字【2026】1号
-- 项目缩写：线(线圈数字化车间)、冲(冲剪数字化车间)、金(金工数字化车间)、焊(焊接数字化车间)

CREATE TABLE IF NOT EXISTS bianhao_scszh (
    id INT AUTO_INCREMENT PRIMARY KEY,
    xm VARCHAR(100) DEFAULT NULL COMMENT '编制人',
    bz VARCHAR(200) DEFAULT NULL COMMENT '所属科室',
    fenlei VARCHAR(50) NOT NULL COMMENT '项目缩写：线/冲/金/焊',
    neirong TEXT DEFAULT NULL COMMENT '编号内容',
    content VARCHAR(500) DEFAULT NULL COMMENT '备注',
    bhtime VARCHAR(50) DEFAULT NULL COMMENT '编号时间',
    bhyear INT DEFAULT NULL COMMENT '编号年份',
    bianhao1 VARCHAR(50) DEFAULT NULL COMMENT '项目缩写（同fenlei）',
    bianhao2 INT DEFAULT NULL COMMENT '顺序号（数字）',
    bianhao3 VARCHAR(10) DEFAULT NULL COMMENT '顺序号（字符串）',
    yj VARCHAR(10) DEFAULT '0' COMMENT '是否已结',
    INDEX idx_fenlei_year (bianhao1, bhyear)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产数字化编号';
