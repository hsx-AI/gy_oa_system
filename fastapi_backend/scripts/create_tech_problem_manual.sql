-- 工艺技术问题手册
-- 记录工艺技术问题、原因分析与采取措施
-- 图片文件名以 JSON 数组存储，实际文件在 uploads/tech_problem_images/ 目录下

CREATE TABLE IF NOT EXISTS tech_problem_manual (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100) NOT NULL COMMENT '分类',
    department VARCHAR(100) DEFAULT NULL COMMENT '所属专业（对应 yggl.lsys）',
    title VARCHAR(300) NOT NULL COMMENT '主题',
    recorder VARCHAR(100) NOT NULL COMMENT '记录人',
    record_time VARCHAR(20) DEFAULT NULL COMMENT '记录时间（格式：YYYY-MM，精确到月）',
    problem_desc TEXT COMMENT '问题描述',
    problem_images JSON COMMENT '问题描述配图文件名列表（JSON数组）',
    cause_analysis TEXT COMMENT '原因分析',
    cause_images JSON COMMENT '原因分析配图文件名列表（JSON数组）',
    measures TEXT COMMENT '采取措施及效果（非必填，可后期补充）',
    measures_images JSON COMMENT '措施配图文件名列表（JSON数组）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_category (category),
    INDEX idx_department (department),
    FULLTEXT INDEX idx_ft (title, problem_desc, cause_analysis, measures) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工艺技术问题手册';

-- 若表已存在需补加 department 字段，可单独执行：
-- ALTER TABLE tech_problem_manual ADD COLUMN department VARCHAR(100) DEFAULT NULL COMMENT '所属专业（对应 yggl.lsys）' AFTER category;
-- ALTER TABLE tech_problem_manual ADD INDEX idx_department (department);
