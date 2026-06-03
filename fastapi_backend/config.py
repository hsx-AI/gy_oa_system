# -*- coding: utf-8 -*-
"""
配置文件
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "考勤系统API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_DB: str = "GY_OA_system"
    MYSQL_DB_DEMO: str = "demo"
    # 每个后端进程、每个数据库实例的 MySQL 连接池大小。
    # 如果使用多 uvicorn worker，总连接数约等于 MYSQL_POOL_SIZE * 数据库实例数 * worker 数。
    MYSQL_POOL_SIZE: int = 10
    # 高峰期获取数据库连接的最长等待秒数；超过后快速失败，避免请求无限堆积。
    MYSQL_POOL_ACQUIRE_TIMEOUT: float = 3.0
    # SQL 执行超过该毫秒数会记录 warning，便于定位慢查询。0 表示关闭。
    MYSQL_SLOW_QUERY_MS: int = 800
    MYSQL_CONNECT_TIMEOUT: int = 5
    MYSQL_READ_TIMEOUT: int = 30
    MYSQL_WRITE_TIMEOUT: int = 30
    
    # CORS配置
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # API配置
    API_PREFIX: str = "/api"

    # 上传文件存储路径（相对于项目根目录）
    UPLOAD_DIR: str = "uploads"

    # 打卡服务器报表拉取：GET 请求 URL，返回当天报表；远端可能很慢（数分钟或更久），超时见 attendance 路由 httpx 配置
    ATTENDANCE_REPORT_FETCH_URL: str = "http://10.42.60.250:6648/run?token=18400021209"
    # 打卡数据自动获取服务健康检查 URL（GET 返回 {"status":"ok"} 表示正常）
    ATTENDANCE_FETCH_HEALTH_URL: str = "http://10.42.60.250:6648/health?token=18400021209"

    # LibreOffice 可执行路径，用于 Word/Excel 转 PDF 预览。留空则自动查找 libreoffice/soffice
    LIBREOFFICE_CMD: str = ""

    # Embedding 模型路径，用于制度 AI 深度搜索。留空则使用 BAAI/bge-small-zh-v1.5（首次自动下载）
    # 若已手动下载模型，可设置为本地路径，如: models/bge-small-zh-v1.5
    #
    # 【无公网服务器迁移】默认下载缓存位置（未设置 EMBEDDING_MODEL_PATH 且未设置 HF_HOME 时）：
    #   Windows: C:\Users\<用户名>\.cache\huggingface\hub\
    #   Linux:   ~/.cache/huggingface/hub\
    # 模型目录名类似: models--BAAI--bge-small-zh-v1.5。迁移时将有网机器上整个 .cache/huggingface
    # 拷到服务器相同路径，或下载到某目录后在此填写该目录路径（如 /data/models/bge-small-zh-v1.5）。
    EMBEDDING_MODEL_PATH: str = "/home/zns/model/bge-small-zh-v1.5"

    # 向量切片参数：每块字符数、块间重叠字符数。切片越小，匹配越精准，匹配切片越易展示
    VECTOR_CHUNK_SIZE: int = 100
    VECTOR_CHUNK_OVERLAP: int = 30

    # 人事档案管理系统入口地址（独立密码，不再免登；前端首页「人事档案管理系统」卡片跳转此链接）
    PERSONNEL_ARCHIVE_URL: str = "http://10.42.60.223:8088/user/userinfouser"

    # 单点登录（跳转其他外部系统，人事档案已改为独立密码见上）
    # 目标系统 B 的入口地址（不含路径，如 https://hr.example.com）
    SSO_TARGET_B_BASE_URL: str = ""
    # B 系统接收 ticket 的路径（如 /sso/entry），完整跳转 URL = BASE_URL + 该路径 + ?ticket=xxx
    SSO_TARGET_B_ENTRY_PATH: str = "/sso/entry"
    # 与 B 系统约定的签名密钥（用于生成 ticket，B 端用同一密钥校验）
    SSO_SECRET: str = "18400021209"
    # ticket 有效秒数
    SSO_TICKET_EXPIRE_SECONDS: int = 120

    # 思想汇报管理子系统单点登录（与主系统用户名一致，通过用户名映射登录）
    # 【重要】必须填思想汇报的【后端】地址（FastAPI 端口 8173），不是前端 5173。用户先访问此后端换 ticket，后端再 302 到前端
    SSO_SIXIANGHUIBAO_BASE_URL: str = "http://10.42.60.223:8173"
    # 思想汇报后端接收 ticket 的路径（需与子系统路由一致，默认 /api/sso/entry）
    SSO_SIXIANGHUIBAO_ENTRY_PATH: str = "/api/sso/entry"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
