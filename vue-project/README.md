# 考勤系统前端 (Vue 3)

现代化的考勤系统前端，使用 Vue 3 + Vite 构建，对接 FastAPI 后端。

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问：http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
```

## 配置说明

### 后端地址

编辑 `vite.config.js` 修改后端地址：

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',  // FastAPI后端地址
  }
}
```

## API接口

| 接口 | 地址 | 说明 |
|------|------|------|
| 打卡数据 | GET /api/daka | 参数：name, dept |
| 智能建议 | GET /api/suggestions | 参数：name, dept |
| 假期数据 | GET /api/holiday | 参数：year |

## 技术栈

- Vue 3 - 渐进式 JavaScript 框架
- Vite - 下一代前端构建工具
- Vue Router - 路由管理
- Axios - HTTP 客户端

## 项目结构

```
src/
├── api/              # API接口定义
├── assets/           # 静态资源
├── components/       # 组件
├── router/           # 路由配置
├── utils/            # 工具函数
└── views/            # 页面
```

## 环境要求

- Node.js 16+
- npm 或 yarn

## 注意事项

- 确保 FastAPI 后端已启动（http://localhost:8000）
- 首次运行需要执行 `npm install`
- 开发环境使用代理转发API请求

## 内网正式部署方式（Nginx + dist）

正式给用户访问时，不建议使用 `npm run dev`。`npm run dev` 是 Vite 开发服务器，会产生大量开发模式请求，早高峰多人访问时容易卡顿。

推荐方式：

- 用户访问 `http://10.42.60.230/`，由 Nginx 读取 `vue-project/dist` 静态文件。
- FastAPI 后端继续运行在 `127.0.0.1:8000`。
- Nginx 将 `/api/` 反向代理到 FastAPI。
- `npm run dev` 只用于个人调试，例如访问 `http://10.42.60.230:3000/`。

### 手动发布前端

前端代码修改后，在 Ubuntu 服务器执行：

```bash
cd /home/zns/gy_oa_system/vue-project
npm run deploy:linux
```

`deploy:linux` 会执行生产构建并修正 `dist` 权限：

```bash
vite build && chmod -R o+rX dist
```

只修改前端代码并重新生成 `dist` 时，通常不需要重载 Nginx，刷新浏览器即可生效。只有修改 Nginx 配置时才需要：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 自动监听打包

如果希望前端文件修改后自动重新打包，可以在服务器前端目录运行：

```bash
cd /home/zns/gy_oa_system/vue-project
npm run build:watch
```

该命令会持续监听源码变化并自动更新 `dist`。终端关闭后监听会停止；需要长期运行时可使用 `tmux`、`screen` 或 systemd 托管。

### Nginx 关键配置

`/etc/nginx/sites-available/default` 中 80 端口站点应指向构建产物：

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 200M;

    root /home/zns/gy_oa_system/vue-project/dist;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location = /index.html {
        add_header Cache-Control "no-cache";
        try_files /index.html =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

如果项目目录变化，需要同步修改 `root` 路径，并确认 Nginx 用户有权限读取新的 `dist` 目录。
