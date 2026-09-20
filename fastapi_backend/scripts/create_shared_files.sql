-- ���Ź����ĵ���Phase 2��
-- Ӧ������ʱҲ�� CREATE TABLE IF NOT EXISTS�����ű������ֹ�ִ��/���ݡ�

CREATE TABLE IF NOT EXISTS shared_files (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(500) NOT NULL,
  file_type VARCHAR(50) NOT NULL DEFAULT '',
  mime_type VARCHAR(200) NOT NULL DEFAULT '',
  parent_id BIGINT NULL,
  storage_path VARCHAR(1000) NOT NULL DEFAULT '',
  size BIGINT NOT NULL DEFAULT 0,
  owner_id VARCHAR(100) NOT NULL DEFAULT '',
  created_by VARCHAR(100) NOT NULL DEFAULT '',
  updated_by VARCHAR(100) NOT NULL DEFAULT '',
  version INT NOT NULL DEFAULT 1,
  is_folder TINYINT NOT NULL DEFAULT 0,
  is_deleted TINYINT NOT NULL DEFAULT 0,
  last_saved_key VARCHAR(100) NOT NULL DEFAULT '' COMMENT '�ϴγɹ����ձ���� document.key',
  last_saved_url VARCHAR(2000) NOT NULL DEFAULT '' COMMENT '�ϴγɹ����ص� callback url���ݵȣ�',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_parent_deleted (parent_id, is_deleted),
  KEY idx_owner (owner_id),
  KEY idx_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='���Ź����ĵ�';
