# 实战 Pipeline 记录（2026-06-01）

本文件记录了在 Python 3.14 + OpenSSL 3.5 + WSL 环境下运行
`jin10-market-analysis` skill 的完整 pipeline 经验和修复。

## 1. 发现的问题

### 1.1 SSL 兼容性

- `requests` / `httpx` 到 `https://mcp.jin10.com/mcp` 的 SSL 握手间歇性失败
- curl 100% 正常
- 原因：Python 3.14 + OpenSSL 3.5.5 与此服务器的 TLS 实现在某些连接上有兼容问题
- 解决方案：`jin10_client.py` 改用 `subprocess.run(["curl", ...])` 替代 requests/httpx

### 1.2 curl 响应头解析

第一次 `initialize` 的 `Mcp-Session-Id` 在 HTTP 响应头中返回。

```python
# 用 -D- 输出响应头到 stdout
cmd = ["curl", "-s", "-X", "POST", URL,
       "-H", f"Authorization: Bearer {TOKEN}",
       "-H", "Content-Type: application/json",
       "-H", "Accept: text/event-stream, application/json",
       "-D-",  # ★ 关键：输出 HTTP 响应头
       "-d", json.dumps(payload),
       "--max-time", "30"]

# 解析响应头 + SSE body
stdout = result.stdout
if "\r\n\r\n" in stdout:
    headers_text, body = stdout.split("\r\n\r\n", 1)
elif "\n\n" in stdout:
    headers_text, body = stdout.split("\n\n", 1)
```

### 1.3 Python 3.14 `@dataclass` + `importlib` 问题

`market_analyzer.py` 中使用了 `@dataclass`，通过 `importlib.spec_from_file_location()` 动态加载时
触发 `AttributeError: 'NoneType' object has no attribute '__dict__'`。

**不要用**：
```python
spec = importlib.util.spec_from_file_location("mod", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
```

**要用**（通过 subprocess 独立进程运行）：
```python
proc = subprocess.run(["python3", "-c", f"""
exec(open('{path}').read())
result = analyze_market_directions(...)
print(json.dumps(result))
"""], ...)
```

### 1.4 report_template.py 引号嵌套

第 138 行使用了中文双引号：
```python
lines.append("> 不建议满仓、重仓或使用杠杆。数据不足时请以\"中性观察\"为默认立场。")
```
这在 f-string 或 exec 中会触发 SyntaxError。已改为 `「中性观察」`。

### 1.5 report_template.py 的 __main__ 演示数据

```python
if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    if raw:
        data = json.loads(raw)
    else:
        # ⚠️ 演示数据：当没有 stdin 输入时使用
        data = {"regime": "rate_cut_trade", ...}
```

这意味着 `echo '{}' | python report_template.py` 才能用真实数据。
空 stdin 时会用演示数据（黄金82分、债券75分、韩股70分），**不要误以为这是真实分析结果**。

## 2. 完整 Pipeline 流程

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  collect_data   │    │  market_analyzer │    │ report_template  │
│                 │    │                  │    │                  │
│ jin10_client.py │───→│ analyze_market_  │───→│ render_market_   │
│ get_quote()     │    │ directions()     │    │ report(result)   │
│ list_flash()    │    │                  │    │                  │
│ list_calendar() │    │ 输出: JSON结果    │    │ 输出: Markdown   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 步骤说明

1. **数据采集**：通过 `exec(open("jin10_client.py").read())` 获取半自动函数
   - 采集报价（8个主要品种）
   - 采集快讯（最新 + 12个关键词搜索）
   - 采集资讯（5个关键词）
   - 采集日历
   - 保存为 `/tmp/xxx_input.json`

2. **市场分析**：通过 subprocess 运行 `market_analyzer.py`
   - 读取 `/tmp/xxx_input.json`
   - 调用 `analyze_market_directions(news_items, quotes, kline_map, calendar)`
   - 保存分析结果到 `/tmp/xxx_result.json`

3. **报告生成**：通过 subprocess 运行 `report_template.py`
   - 读取 `/tmp/xxx_result.json`
   - 调用 `render_market_report(data)`
   - 输出标准 Markdown 报告

### 关键数据量参考

- 一次完整分析约 10-15 秒（含 20 次 MCP API 调用 + 2 次 subprocess）
- 快讯/资讯合计约 2000 条（含关键词搜索去重）
- 日历事件约 260 条
- Session 在此过程中保持有效，不需要重新 initialize
