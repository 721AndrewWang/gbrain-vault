# Mige API

Mige API 是 Claude 模型的代理API端点。

## 配置
- 端点: `https://api.migeapi.com`
- 协议: Anthropic Messages API (`/v1/messages`)
- 认证: `x-api-key` header
- 版本: `anthropic-version: 2023-06-01`

## 已知问题
- Claude Code CLI v2.1.170 在非Anthropic端点下hang
- 绕过方案: Python `urllib` 直接调用API
- `claude-sonnet-4-6` 有 ~3000字符阈值
- `claude-opus-4-7` 无已知限制

## 在MOYAG中的角色
- [[Hermes Agent]] → 直接调用Mige API生成代码
- [[Claude Code]] → 通过Mige API执行编码任务
- TDD管线: Hermes写RED测试 → Mige API调Claude生成GREEN代码

## 关键代码
```python
import urllib.request, json
payload = json.dumps({
    "model": "claude-opus-4-7",
    "max_tokens": 2500,
    "messages": [{"role": "user", "content": prompt}]
}).encode()
req = urllib.request.Request(
    f"{base_url}/v1/messages", data=payload,
    headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
)
```

## 关联
- [[Claude Code]]
- [[Hermes Agent]]
- [[05-AI模型]]
