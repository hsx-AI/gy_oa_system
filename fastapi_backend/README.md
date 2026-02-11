# 现代化考勤系统后端

本系统是基于 FastAPI 的现代化考勤管理后端服务，已全面升级支持 MySQL 数据库，提供高性能的考勤数据管理、报表统计和智能建议功能。

## 功能特性

*   **RESTful API**: 提供标准的 HTTP 接口。
*   **MySQL 支持**: 数据完全存储于 MySQL 数据库，支持高并发。
*   **考勤管理**: 支持 Excel 考勤数据上传、查询和统计。
*   **SSO 集成**: 支持与旧系统通过 Token 进行单点登录。
*   **智能建议**: 自动分析缺勤、迟到、早退和加班情况。
*   **报表统计**: 提供月度加班和请假统计报表。

## 环境要求

*   Python 3.8+
*   MySQL 5.7 或 8.0+

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

打开 `config.py` 文件，根据实际情况修改 MySQL 连接配置：

```python
    # 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "your_password"
    MYSQL_DB: str = "GY_OA_system"
```

### 3. 启动服务

```bash
python main.py
```

服务启动后，可以通过浏览器访问 API 文档：
*   Swagger UI: http://localhost:8000/docs
*   ReDoc: http://localhost:8000/redoc

## 项目结构

```
fastapi_backend/
├── main.py            # 应用入口
├── config.py          # 配置文件
├── database.py        # MySQL 数据库连接池
├── attendance_db.py   # 考勤数据库操作封装
├── models.py          # Pydantic 数据模型
├── routers/           # API 路由模块
│   ├── auth.py        # 登录认证
│   ├── sso_auth.py    # SSO 单点登录
│   ├── attendance.py  # 考勤数据管理
│   ├── report.py      # 报表统计
│   ├── suggestions.py # 智能建议
│   └── holiday.py     # 假期数据
└── utils/             # 工具函数
```

## API 接口概览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | `/api/auth` | 用户登录、Token 验证 |
| 考勤 | `/api/attendance` | 考勤数据上传、查询 |
| 报表 | `/api/report` | 加班、请假统计报表 |
| 建议 | `/api/suggestions` | 考勤异常智能分析 |
| 假期 | `/api/holiday` | 节假日配置查询 |
