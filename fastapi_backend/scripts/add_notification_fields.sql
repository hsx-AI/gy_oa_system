-- 通知历史表
CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  content TEXT NOT NULL COMMENT '通知内容',
  publish_time DATETIME NOT NULL COMMENT '发布时间',
  publisher VARCHAR(50) NOT NULL COMMENT '发布人姓名'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- yggl.gx_gt 用于存储最后已读通知的 ID（整数），NULL/0 表示未读过任何通知
-- ALTER TABLE yggl ADD COLUMN gx_gt VARCHAR(10) DEFAULT '0' COMMENT '最后已读通知ID';

-- webconfig 之前的 gx_content/gx_time 字段已废弃，可保留不影响
