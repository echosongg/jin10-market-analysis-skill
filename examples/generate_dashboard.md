# 生成 Dashboard：完整调用流程

本文件记录每次生成看板时，从用户说话到文件落地的**完整代码和 Prompt 调用过程**。

---

## 第一步：你对 Hermes 说的话（固定触发词）

任选其一：

```
帮我生成 dashboard
今天我的关注方向怎么看，给我看板
刷新看板
```

---

## 第二步：Hermes 读取 Watchlist

```python
# Hermes 内部执行
exec(open("scripts/watchlist_loader.py").read())

watchlist  = load_watchlist()          # 读 references/watchlist.md
all_kws    = get_all_keywords(watchlist)
all_codes  = get_all_codes(watchlist)

# 当前 watchlist（2026-06）
# all_kws = ["CPO", "共封装光学", "光模块", "机器人", "人形机器人",
#             "半导体", "芯片", "HBM", "卫星互联网", "低轨卫星", "煤炭", ...]
# all_codes = []   ← 全部为 —，纯新闻驱动
```

---

## 第三步：MCP 初始化（curl 子进程）

```python
import subprocess, json

# Token 写入临时文件（避免 shell 特殊字符被拦截）
with open("/tmp/jin10_token", "w") as f:
    f.write(JIN10_MCP_TOKEN)

JIN10_URL = "https://mcp.jin10.com/mcp"

# Step 3a: initialize → 获取 Mcp-Session-Id
cmd = (
    f'curl -s -D /tmp/jin10_headers.txt -X POST "{JIN10_URL}" '
    f'-H "Content-Type: application/json" '
    f'-H "Authorization: Bearer $(cat /tmp/jin10_token)" '
    f'-d \'{{"jsonrpc":"2.0","id":1,"method":"initialize",'
    f'"params":{{"protocolVersion":"2025-11-25","capabilities":{{}},'
    f'"clientInfo":{{"name":"hermes","version":"1.0"}}}}}}\''
)
subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

# Step 3b: 提取 Session ID
sess_line = subprocess.run(
    "grep -i 'mcp-session-id' /tmp/jin10_headers.txt",
    shell=True, capture_output=True, text=True
).stdout.strip()
SESSION_ID = sess_line.split(":")[-1].strip()

# Step 3c: notifications/initialized（通知服务端就绪）
# 后续所有请求携带 -H "Mcp-Session-Id: {SESSION_ID}"
```

---

## 第四步：数据采集（MCP 工具调用）

每次调用的标准封装：

```python
def call_tool(name, arguments):
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments}
    })
    cmd = (
        f'curl -s -X POST "{JIN10_URL}" '
        f'-H "Mcp-Session-Id: {SESSION_ID}" '
        f'-H "Content-Type: application/json" '
        f'-H "Authorization: Bearer $(cat /tmp/jin10_token)" '
        f"-d '{body}'"
    )
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    # SSE 响应格式：每行 "data: {...}"
    for line in r.stdout.strip().split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])
    return {}
```

### 4-1. 财经日历

```python
result = call_tool("list_calendar", {})
# result["result"]["structuredContent"]["data"] → 约260条事件列表
# 重点过滤 star == 3（金十最高重要度）
calendar_items = result["result"]["structuredContent"]["data"]
high_star = [e for e in calendar_items if int(e.get("star", 0)) == 3]
```

### 4-2. 最新快讯

```python
result = call_tool("list_flash", {})
flash_items = result["result"]["structuredContent"]["data"]["items"]
# → 最新20条快讯，内容在 item["content"]（无 title 字段）
```

### 4-3. Watchlist 关键词搜索（逐个关键词调用）

```python
all_news = list(flash_items)   # 初始化，加入最新快讯
seen_urls = set(i.get("url","") for i in flash_items)

for kw in all_kws:   # 来自 watchlist 的全部关键词
    result = call_tool("search_flash", {"keyword": kw})
    items = result["result"]["structuredContent"]["data"]["items"]
    for item in items:
        url = item.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            all_news.append(item)

# 当前 watchlist 约 30 个关键词
# 搜索完成后 all_news 约 300-800 条去重快讯
```

### 4-4. 市场上下文行情（用于 Regime 判断）

```python
CONTEXT_CODES = ["XAUUSD", "USOIL", "USDJPY", "EURUSD", "USDCNH"]
quote_map = {}

for code in CONTEXT_CODES:
    result = call_tool("get_quote", {"code": code})
    quote_map[code] = result["result"]["structuredContent"]["data"]
    # 字段：close, open, high, low, ups_percent（number 类型）

# 示例：
# quote_map["XAUUSD"] = {"name":"现货黄金","close":3320.5,"ups_percent":0.82,...}
```

### 4-5. K 线（有代理代码的方向）

```python
kline_map = {}

# watchlist 中有代理代码的方向（如 "半导体" 配了 COPPER）
for code in all_codes:
    result = call_tool("get_kline", {"code": code})
    # ⚠️ 不传 time/count，默认最近100根分钟K线
    kline_map[code] = result["result"]["structuredContent"]["data"]
    # klines[].open/close/high/low 是 string，需 float() 转换

# 同时获取 XAUUSD K线用于看板图表展示
result = call_tool("get_kline", {"code": "XAUUSD"})
kline_map["XAUUSD"] = result["result"]["structuredContent"]["data"]
```

---

## 第五步：评分

```python
exec(open("scripts/market_analyzer.py").read())

# Watchlist 模式（优先）
result = analyze_watchlist_directions(
    watchlist      = watchlist,
    news_items     = all_news,
    quote_map      = quote_map,
    kline_map      = kline_map,
    calendar_items = calendar_items,
)

# result 结构：
# {
#   "regime": "risk-on",
#   "regime_reasons": ["黄金 +0.82%↑", "科技股新闻偏多", "→ 风险偏好高涨"],
#   "watchlist_mode": True,
#   "directions": [
#     {
#       "name": "半导体",
#       "total": 78.5,
#       "level": "可关注",
#       "macro": 82, "news": 80, "trend": 60, "fund": 75, "event_risk": 68,
#       "bullish_factors": ["消息面活跃（6个关键词命中）", "AI", "HBM", "先进封装"],
#       "bearish_factors": [],
#       "watch_list": ["美国ISM制造业PMI（待公布，预期49.0）"]
#     },
#     ...
#   ]
# }
```

---

## 第六步：生成 Markdown 报告（输出给用户）

```python
exec(open("scripts/report_template.py").read())
markdown_report = render_market_report(result)
# Hermes 将 markdown_report 输出到对话窗口
print(markdown_report)
```

输出格式（固定）：
```markdown
# 金十数据市场方向分析报告
> 生成时间：2026-06-09 10:03

## 一、今日结论
当前市场处于 Risk-On 风险偏好高涨 环境，今日相对更值得关注的方向为：**半导体、CPO、机器人**。

## 二、市场环境判断
...

## 三、多市场方向评分表
| 排名 | 市场方向 | 总分 | 等级 | 核心利好 | 主要风险 |
...

## 四、Top 3 重点方向详情
...

---
> 免责声明...
```

---

## 第七步：生成 HTML 看板

```python
# ⚠️ 必须调用脚本，不允许自己写 HTML
import subprocess, json, os
from datetime import datetime

ts = datetime.now().strftime("%Y%m%d_%H%M")
html_path = f"/home/ada39/.hermes/skills/mcp/jin10-market-analysis/dashboard_{ts}.html"

# 构建扩展 JSON（分析结果 + 原始数据）
extended = {
    **result,                      # regime, regime_reasons, directions
    "quotes":   quote_map,         # 行情数据
    "klines":   kline_map,         # K线数据
    "calendar": calendar_items,    # 日历事件
}

# 调用 report_html.py
exec(open("scripts/report_html.py").read())
render_html_dashboard(extended, html_path)

# 复制到 Windows 桌面
desktop = "/mnt/c/Users/Ada39/Desktop"
subprocess.run(f"cp {html_path} {desktop}/", shell=True)

print(f"✅ HTML 看板已生成：{desktop}/dashboard_{ts}.html")
print(f"   用浏览器打开查看")
```

---

## 第八步：Hermes 告知用户

```
分析完成！

[中文报告内容已输出到对话]

✅ HTML 看板已复制到桌面：dashboard_20260609_1003.html
   双击用浏览器打开即可看到交互式看板。
```

---

## 完整时序图

```
用户: "帮我生成 dashboard"
  │
  ▼
Hermes 读取 references/watchlist.md
  │  → 提取 6 个方向，约 30 个关键词
  ▼
MCP initialize → 获取 Session ID
  │
  ├── list_calendar({})          → 约260条日历事件
  ├── list_flash({})             → 最新20条快讯
  ├── search_flash × ~30次       → 关键词快讯（去重后约300-800条）
  ├── get_quote × 5次            → XAUUSD/USOIL/USDJPY/EURUSD/USDCNH 行情
  └── get_kline × 1-N次          → K线（有代理代码的方向 + XAUUSD）
  │
  ▼
analyze_watchlist_directions()   → JSON 评分结果（含 regime_reasons）
  │
  ├── render_market_report()     → Markdown → 输出到对话
  └── render_html_dashboard()    → HTML 文件 → 复制到桌面
  │
  ▼
用户: 双击桌面 dashboard_YYYYMMDD_HHMM.html 查看
```

---

## 常见问题

**Q：每次看板结构都一样吗？**
A：是的，结构由 `report_html.py` 的固定模板决定，只有数据会变。6个板块顺序和布局不会变。

**Q：想加一个新的关注方向怎么做？**
A：只编辑 `references/watchlist.md`，在表格加一行，下次分析自动包含。

**Q：某个方向想拉 K 线怎么做？**
A：在 `watchlist.md` 的"代理品种代码"列填写对应的 Jin10 代码（如 `COPPER`），下次就会自动拉 K 线并显示在看板上。

**Q：看板生成很慢怎么办？**
A：主要耗时在 MCP 调用（约 30 次）。整体约 15-25 秒正常。如果超时报错，检查 `JIN10_MCP_TOKEN` 是否有效。
