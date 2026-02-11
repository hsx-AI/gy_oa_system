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
