# 单点登录（SSO）B 系统对接说明

A 系统（本考勤/OA 系统）首页提供「人事档案管理系统」入口，用户点击后携带 **ticket** 跳转到 B 系统（人事档案），B 系统需根据 ticket 校验并建立登录态。

---

## 1. 用户拿到的完整跳转 URL 格式

用户从 A 系统点击「人事档案管理系统」后，浏览器会跳转到 B 系统的如下地址（示例）：

```
https://B系统域名/sso/entry?ticket=<ticket字符串>
```

- **路径**：由 A 系统配置项 `SSO_TARGET_B_ENTRY_PATH` 决定，默认 `/sso/entry`，B 系统需提供该路径的 GET 接口。
- **查询参数**：`ticket`，由 A 系统生成、一次性有效、带 HMAC 签名。

---

## 2. ticket 格式与校验方式

### 2.1 格式

`ticket` 为一段字符串，形如：

```
<base64_payload>.<hmac_sha256_signature>
```

- **前半段（base64_payload）**：Base64URL 编码的 JSON，**解码后**内容示例：
  ```json
  {
    "sub": "110101199001011234",
    "name": "张三",
    "exp": 1736789123
  }
  ```
  - `sub`：员工**身份证号**（唯一标识，与 B 系统员工表对应）。
  - `name`：员工姓名。
  - `exp`：Unix 时间戳（秒），ticket 过期时间。

- **后半段（hmac_sha256_signature）**：对前半段 `base64_payload` 字符串做 **HMAC-SHA256** 的十六进制结果，密钥为 A、B 双方约定的 **SSO_SECRET**。

### 2.2 B 系统校验步骤（推荐）

1. 接收 GET 请求：`/sso/entry?ticket=xxx`
2. 若缺少 `ticket` 或为空，返回 400，引导用户从 A 系统重新进入。
3. 将 `ticket` 按**第一个 `.`** 拆成两段：`payload_b64`、`signature`。
4. 使用与 A 系统**相同的 SSO_SECRET** 对 `payload_b64` 做 HMAC-SHA256，得到十六进制字符串，与 `signature` 比对；不一致则视为篡改，返回 403。
5. 对 `payload_b64` 做 **Base64URL 解码**（缺 padding 的需补全），再 JSON 解析，得到 `sub`（身份证号）、`name`、`exp`。
6. 校验 `exp` 是否大于当前时间（秒）；若已过期，返回 401 或提示“链接已过期，请从 OA 重新进入”。
7. 用 `sub`（身份证号）在 B 系统员工/用户表中查找对应用户，若存在则为其建立登录态（Session/Cookie/JWT 等），并重定向到 B 系统首页或指定页；若不存在则按 B 系统策略处理（例如提示“未在人事档案中开通”或自动创建账号）。

### 2.3 伪代码示例（Python）

```python
import base64
import hmac
import hashlib
import json
import time

def verify_ticket(ticket: str, secret: str) -> dict:
    if not ticket or "." not in ticket:
        return None
    payload_b64, sig = ticket.split(".", 1)
    # Base64URL 补 padding
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    computed = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if computed != sig:
        return None
    raw = base64.urlsafe_b64decode(payload_b64)
    data = json.loads(raw)
    if data.get("exp", 0) < time.time():
        return None  # 已过期
    return data  # {"sub": "身份证号", "name": "姓名", "exp": ...}
```

---

## 3. A 系统侧配置（给运维）

在 A 系统后端配置（环境变量或 `.env`）中需设置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `SSO_TARGET_B_BASE_URL` | B 系统站点根 URL（不含路径） | `https://hr.example.com` |
| `SSO_TARGET_B_ENTRY_PATH` | B 系统接收 ticket 的路径 | `/sso/entry` |
| `SSO_SECRET` | 与 B 系统约定的 HMAC 密钥（需一致） | 由双方协商一长串随机字符串 |
| `SSO_TICKET_EXPIRE_SECONDS` | ticket 有效秒数 | `120` |

---

## 4. 小结

- **B 系统需要提供的接口**：`GET /sso/entry?ticket=xxx`（路径可与 A 配置一致）。
- **B 系统需要与 A 约定**：同一份 `SSO_SECRET`，用于校验 ticket 签名。
- **用户唯一标识**：身份证号 `sub`，两套系统均以身份证号为唯一关联即可完成免登。
