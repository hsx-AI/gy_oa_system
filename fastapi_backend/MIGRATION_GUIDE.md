# 数据库迁移指南 (SQLite -> MySQL)

本指南将帮助您将考勤系统的数据库从 SQLite/Access 迁移到 MySQL，并配置后端服务。

## 1. 准备工作

### 1.1 安装 MySQL
确保您的电脑上已安装并启动了 MySQL 服务（推荐版本 5.7 或 8.0+）。
如果您还没有安装，可以从 [MySQL官网](https://dev.mysql.com/downloads/installer/) 下载安装，或者使用 PHPStudy 等集成环境。

### 1.2 创建数据库用户 (可选)
您可以直接使用 `root` 用户，或者创建一个专用的用户：
```sql
CREATE DATABASE modern_daka_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
*注意：我们的迁移脚本会自动尝试创建数据库，但您需要保证连接的用户有创建数据库的权限。*

## 2. 配置连接

打开 `fastapi_backend\config.py` 文件，找到以下配置项并根据您的实际情况进行修改：

```python
    # 数据库配置
    MYSQL_HOST: str = "localhost"  # 数据库地址
    MYSQL_PORT: int = 3306         # 端口
    MYSQL_USER: str = "root"       # 用户名
    MYSQL_PASSWORD: str = "root"   # 密码 (请修改为您设置的密码)
    MYSQL_DB: str = "modern_daka_system" # 数据库名
```

## 3. 执行数据迁移

在 `fastapi_backend` 目录下，运行以下命令：

```bash
python migrate_to_mysql.py
```

脚本将会：
1. 连接到 MySQL 服务器。
2. 自动创建数据库和所需的表结构。
3. 从 `report1.mdb` (Access) 中读取并迁移缺失的表。

**从 Access report1.mdb 迁移缺失表：**
```bash
python migrate_access_to_mysql.py
```
脚本会对比 MySQL 已有表，将 Access 中存在但 MySQL 中不存在的表（含结构+数据）迁移过来。
4. 将所有数据导入到 MySQL 中。

如果看到 **"所有迁移任务完成！"** 的提示，即表示迁移成功。

## 4. 启动服务

数据迁移完成后，您可以正常启动后端服务：

```bash
python main.py
```

现在，系统将完全运行在 MySQL 数据库上，支持高并发访问。

## 常见问题

**Q: 运行迁移脚本时提示 "Can't connect to MySQL server"？**
A: 请检查 MySQL 服务是否已启动，以及 `config.py` 中的主机、端口、用户名和密码是否正确。

**Q: 提示 "ModuleNotFoundError"？**
A: 请确保已安装所有依赖：`pip install -r requirements.txt`。
