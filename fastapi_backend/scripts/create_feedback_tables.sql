-- 意见与建议模块建表脚本
-- 1. 部门吐槽墙（匿名）
-- 2. 领导匿名信箱
-- 3. 系统功能建议（实名）

CREATE TABLE IF NOT EXISTS feedback_wall (
    id VARCHAR(36) PRIMARY KEY,
    content TEXT NOT NULL,
    status TINYINT DEFAULT 0 COMMENT '0=待审核 1=已通过 2=已拒绝',
    resolved TINYINT DEFAULT 0 COMMENT '0=未处理 1=处理中 2=已回复 3=已解决',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    reviewed_by VARCHAR(50) NULL,
    assignee VARCHAR(50) NULL COMMENT '吐槽问题负责人',
    assigned_by VARCHAR(50) NULL COMMENT '指派人',
    assigned_at DATETIME NULL COMMENT '指派时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS feedback_leader_inbox (
    id VARCHAR(36) PRIMARY KEY,
    target_leader VARCHAR(50) NOT NULL COMMENT '目标领导姓名',
    content TEXT NOT NULL,
    reply TEXT NULL,
    reply_at DATETIME NULL,
    status TINYINT DEFAULT 0 COMMENT '0=未回复 1=已回复',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS feedback_system (
    id VARCHAR(36) PRIMARY KEY,
    submitter VARCHAR(50) NOT NULL COMMENT '提交人姓名',
    department VARCHAR(100) NULL,
    content TEXT NOT NULL,
    reply TEXT NULL,
    reply_at DATETIME NULL,
    reply_by VARCHAR(50) NULL,
    status TINYINT DEFAULT 0 COMMENT '0=未回复 1=已回复',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
