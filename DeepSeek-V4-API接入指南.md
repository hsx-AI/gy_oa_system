# 本地 DeepSeek-V4 大模型 API 接入规范

> 供内网业务系统对接参考。  
> 网关地址、能力 ID、Token 请向平台管理员申请；本文不提供真实密钥。

---

## 1. 概述

| 项 | 说明 |
|----|------|
| 服务形态 | OpenAI 兼容 Chat Completions 网关 |
| 部署环境 | 公司内网（需能访问 `10.3.x.x`） |
| 模型名称 | `DeepSeek-V4`（请求体 `model` 字段必须与此一致） |
| 协议 | HTTP / JSON |
| 鉴权 | JWT，请求头 `Authorization: Bearer <token>` |

**OpenAI SDK 使用的 `base_url`（推荐）：**

```text
http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1
```

实际对话接口完整路径为：

```text
{base_url}/chat/completions
```

即：

```http
POST http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1/chat/completions
```

> 说明：能力路径中的 `202605212224_v1` 为平台能力标识，若平台调整能力版本，需同步更新 `base_url`。

---

## 2. 鉴权

### 2.1 方式

所有调用必须携带有效 JWT：

```http
Authorization: Bearer <JWT>
Content-Type: application/json
```

- Token 由平台侧签发（通常为 JWT，算法以平台实际为准）。
- **禁止**把 Token 写进前端公开代码、Git 仓库或对外文档。
- Token 过期或无效时，网关通常返回 `401` / `403`，需重新向管理员申请。

### 2.2 与 OpenAI SDK 的对应关系

使用官方 `openai` Python SDK 时，把 JWT 填入 `api_key` 即可；SDK 会自动组装为 `Authorization: Bearer ...`：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1",
    api_key="<你的JWT>",   # 必须是有效 Token，不要用占位字符串
)
```

---

## 3. Chat Completions 接口

### 3.1 请求

```http
POST /prod-api/api_ability/202605212224_v1/v1/chat/completions
Host: 10.3.26.243:30080
Content-Type: application/json
Authorization: Bearer <JWT>
```

### 3.2 请求体字段

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 固定填 `DeepSeek-V4` |
| `messages` | array | 是 | 对话消息列表，见下表 |
| `temperature` | number | 否 | 采样温度，建议 `0.2`～`0.7`，常用 `0.5` |
| `top_p` | number | 否 | nucleus 采样，常用 `0.5` |
| `max_tokens` | integer | 否 | 单次最大生成 token；过大可能超时，建议按业务控制 |
| `stream` | boolean | 否 | `true` 开启 SSE 流式；默认 `false` |
| `stream_options` | object | 否 | 流式时可选 `{"include_usage": true}`（部分网关可能不支持） |

**`messages[]` 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | string | `system` / `user` / `assistant` |
| `content` | string | 文本内容 |

### 3.3 非流式请求示例

```json
{
  "model": "DeepSeek-V4",
  "messages": [
    { "role": "system", "content": "你是公司内网助手，回答简洁准确。" },
    { "role": "user", "content": "用一句话介绍你自己。" }
  ],
  "temperature": 0.5,
  "max_tokens": 1024,
  "stream": false
}
```

### 3.4 非流式响应示例

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "DeepSeek-V4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好，我是 DeepSeek-V4，可以协助处理文本理解与生成任务。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 28,
    "completion_tokens": 24,
    "total_tokens": 52
  }
}
```

业务侧取结果：`choices[0].message.content`。

### 3.5 流式响应

请求体设 `"stream": true`。响应为 `text/event-stream`，每行形如：

```text
data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"你好"},"finish_reason":null}]}

data: [DONE]
```

客户端应：

1. 按行解析 `data: ` 后的 JSON；
2. 累加 `choices[0].delta.content`；
3. 收到 `data: [DONE]` 结束。

---

## 4. 错误与排查

| 现象 | 常见原因 | 处理建议 |
|------|----------|----------|
| 连接超时 / 无法访问 | 不在内网或网关宕机 | 确认 VPN/内网路由；检查 `10.3.26.243:30080` |
| HTTP 401 / 403 | Token 缺失、过期、错误 | 重新申请 JWT；检查 `Bearer ` 前缀与空格 |
| HTTP 404 | `base_url` / 能力 ID 错误 | 核对完整路径是否含 `/v1/chat/completions` |
| HTTP 400 / 模型报错 | `model` 名称不对 | 必须为 `DeepSeek-V4`（大小写一致） |
| 空回复或极慢 | 上下文过长、`max_tokens` 过大 | 缩短输入；降低 `max_tokens`；增加超时 |

---

## 5. 调用示例

### 5.1 cURL

```bash
curl -X POST "http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <你的JWT>" \
  -d "{\"model\":\"DeepSeek-V4\",\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}],\"temperature\":0.5}"
```

### 5.2 Python（requests）

```python
import requests

URL = "http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1/chat/completions"
TOKEN = "<你的JWT>"  # 从环境变量或密钥管理读取，勿硬编码

resp = requests.post(
    URL,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    },
    json={
        "model": "DeepSeek-V4",
        "messages": [{"role": "user", "content": "你好"}],
        "temperature": 0.5,
        "max_tokens": 1024,
    },
    timeout=60,
)
resp.raise_for_status()
print(resp.json()["choices"][0]["message"]["content"])
```

### 5.3 Python（openai SDK）

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1",
    api_key="<你的JWT>",
    timeout=60.0,
)

completion = client.chat.completions.create(
    model="DeepSeek-V4",
    messages=[{"role": "user", "content": "你好"}],
    temperature=0.5,
    max_tokens=1024,
)
print(completion.choices[0].message.content)
```

### 5.4 流式（openai SDK）

```python
stream = client.chat.completions.create(
    model="DeepSeek-V4",
    messages=[{"role": "user", "content": "请用三句话介绍你自己"}],
    stream=True,
    temperature=0.5,
)
for event in stream:
    if not event.choices:
        continue
    piece = event.choices[0].delta.content or ""
    if piece:
        print(piece, end="", flush=True)
```

---

## 6. 安全与使用约定

1. **仅限内网业务系统**调用；禁止暴露到公网。
2. JWT 按系统/环境隔离保管（密钥库、环境变量、配置中心），定期轮换。
3. 生产调用建议设置合理超时（如 30～120 秒）与重试上限，避免打满网关。
4. 日志中不要打印完整 Token；如需排障可只记录前后各 6 位。
5. 多轮对话自行维护 `messages` 历史；注意上下文长度，超长应截断或摘要。

---

## 7. 对接检查清单

- [ ] 内网可访问 `http://10.3.26.243:30080`
- [ ] 已获得有效 JWT
- [ ] `base_url` 填到 `/v1`（不要漏段，也不要多写 `/chat/completions` 给 SDK）
- [ ] `model` = `DeepSeek-V4`
- [ ] 请求头含 `Authorization: Bearer ...`
- [ ] 用一句短对话完成连通性验证

---

## 8. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-03 | 初版：整理 Chat Completions + Bearer JWT 接入方式 |
| 2026-09 | 补全 base_url、SDK 示例、流式与排障说明 |

如网关地址、能力 ID 或鉴权策略发生变更，以平台管理员最新通知为准，并同步更新本文档第 1、2 节。
