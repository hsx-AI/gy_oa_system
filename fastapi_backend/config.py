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
    MYSQL_DB: str = "GY_oa_system"
    
    # CORS配置
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # API配置
    API_PREFIX: str = "/api"

    # 上传文件存储路径（相对于项目根目录）
    UPLOAD_DIR: str = "uploads"

    # 单点登录（跳转人事档案等外部系统）
    # 目标系统 B 的入口地址（不含路径，如 https://hr.example.com）
    SSO_TARGET_B_BASE_URL: str = ""
    # B 系统接收 ticket 的路径（如 /sso/entry），完整跳转 URL = BASE_URL + 该路径 + ?ticket=xxx
    SSO_TARGET_B_ENTRY_PATH: str = "/sso/entry"
    # 与 B 系统约定的签名密钥（用于生成 ticket，B 端用同一密钥校验）
    SSO_SECRET: str = ""
    # ticket 有效秒数
    SSO_TICKET_EXPIRE_SECONDS: int = 120

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

