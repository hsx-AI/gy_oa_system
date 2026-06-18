# 本地 DeepSeek-V4 大模型 API 接入指南

## 接口信息

- **Base URL**: `http://10.3.26.243:30080`
- **模型名称**: `DeepSeek-V4`
- **接口格式**: 兼容 OpenAI Chat Completions

## 鉴权方式

在请求头中传入 JWT Token：

```
Authorization: Bearer <token>
```

## Chat 接口

```http
POST /prod-api/api_ability/202605212224_v1/v1/chat/completions
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzUxMiJ9...
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 是 | 模型名称，固定 `DeepSeek-V4` |
| messages | array | 是 | 对话消息列表，`[{"role":"user","content":"..."}]` |
| temperature | float | 否 | 温度参数，默认 0.5 |
| top_p | float | 否 | top_p 采样，默认 0.5 |
| max_tokens | int | 否 | 最大输出 token 数，默认 5120 |
| stream | bool | 否 | 是否流式输出，默认 false |

### 请求示例

```json
{
  "model": "DeepSeek-V4",
  "messages": [
    { "role": "user", "content": "你好，请简单介绍一下你自己" }
  ],
  "temperature": 0.5,
  "max_tokens": 5120
}
```

### 返回示例

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
        "content": "你好！有什么可以帮你的吗？"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 11,
    "total_tokens": 16
  }
}
```

## Python 示例

```python
import requests

url = "http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer <你的token>"
}

payload = {
    "model": "DeepSeek-V4",
    "messages": [
        {"role": "user", "content": "你好"}
    ]
}

resp = requests.post(url, headers=headers, json=payload, timeout=30)
print(resp.json())
```

## cURL 示例

```bash
curl -X POST "http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <你的token>" \
  -d '{"model":"DeepSeek-V4","messages":[{"role":"user","content":"你好"}]}'
```

## 注意事项

- 需要在内网环境下访问（例如此地址为 `10.3.x.x` 内网IP）
- 支持标准的 OpenAI 多轮对话格式
- 模型支持超长上下文（1M token）和文件处理
