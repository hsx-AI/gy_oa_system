-- 为 webconfig 表增加大模型配置字段，用于假期通知解析：优先本地推理，不可用时走公网 API
-- 执行后可在 webconfig 中 id=1 的行设置：
--   llm_base_url = 'http://10.42.60.250:11434/v1'  （本地 Ollama/OpenAI 兼容接口根地址）
--   llm_model     = 'qwen3:8b'                      （本地模型名）
-- 留空时后端使用上述默认值；公网兜底仍依赖 deepseek_api_key 或环境变量 DEEPSEEK_API_KEY

ALTER TABLE webconfig ADD COLUMN llm_base_url VARCHAR(512) DEFAULT NULL COMMENT '大模型接口根URL，如 http://10.42.60.250:11434/v1，优先用于假期解析';
ALTER TABLE webconfig ADD COLUMN llm_model VARCHAR(128) DEFAULT NULL COMMENT '大模型名称，如 qwen3:8b';
