# jin10-mcp-market-analysis

> 基于金十数据 MCP 服务的财经市场分析工具
>
> 实时行情 · 分钟级 K 线 · 快讯流 · 深度资讯 · 财经日历 · 多市场方向评分

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
  - [前置条件](#前置条件)
  - [方式一：作为 Hermes Agent Skill 使用（推荐）](#方式一作为-hermes-agent-skill-使用推荐)
  - [方式二：直接使用 Python 脚本](#方式二直接使用-python-脚本)
  - [方式三：在支持 MCP 的客户端中配置](#方式三在支持-mcp-的客户端中配置)
- [API 工具清单](#api-工具清单)
- [使用示例](#使用示例)
  - [获取黄金行情 + K 线](#获取黄金行情--k-线)
  - [搜索特定主题快讯](#搜索特定主题快讯)
  - [获取深度资讯文章](#获取深度资讯文章)
  - [查看今日财经日历](#查看今日财经日历)
  - [完整市场分析（全自动）](#完整市场分析全自动)
- [项目文件结构](#项目文件结构)
- [安全声明](#安全声明)
- [许可证](#许可证)

---

## 项目简介

本项目是一个基于 [金十数据](https://jin10.com) MCP（Model Context Protocol）服务的财经市场分析工具包。它通过标准化的 MCP 协议接口，获取实时金融数据（行情、K 线、快讯、资讯、财经日历），并提供可编程的分析引擎，支持对黄金、原油、美股、港股、A 股、日股、韩股、外汇等 10 个市场方向进行多维度评分。
<img width="2310" height="2808" alt="regime_mode" src="https://github.com/user-attachments/assets/fd56d9be-f4d0-4a15-a572-ec38cf89d6b5" />
**核心价值：** 将零散的财经数据整合为结构化的市场方向分析，帮助投资者快速了解今日市场主线。

---

## 功能特性

| 特性 | 说明 |
|------|------|
| **实时行情** | 获取现货黄金、原油、外汇等品种的实时报价（开盘价、最高/最低、涨跌幅） |
| **分钟级 K 线** | 最近 100 根分钟级 K 线（支持任意品种） |
| **快讯流** | 实时财经快讯检索与翻页，支持关键词搜索 |
| **深度资讯** | 财经文章搜索、详情获取（含全文内容） |
| **财经日历** | 今日及本周经济数据/事件日历，含预期值与星级标记 |
| **多市场评分** | 10 个市场方向 × 5 个维度（宏观/新闻/趋势/资金/事件），合计 100 分 |
| **市场环境判断** | 自动判断 Risk-On / Risk-Off / Inflation Trade / Rate-Cut Trade 等市场 Regime |
| **中文报告** | 自动生成结构化的中文 Markdown 分析报告 |

---

## 快速开始

### 前置条件

- Python 3.10+
- `curl` 命令行工具（用于 MCP 协议传输，比 Python ssl 握手更可靠）
- 金十数据 MCP Bearer Token（已内置，但建议通过环境变量 `JIN10_MCP_TOKEN` 配置）

### 方式一：作为 Hermes Agent Skill 使用（推荐）

如果你使用 [Hermes Agent](https://hermes-agent.nousresearch.com)，本项目可直接作为 Skill 加载：

1. 将本仓库克隆到 Hermes 的 skills 目录：

```bash
git clone https://github.com/echosongg/jin10-mcp-market-analysis.git \
  ~/.hermes/skills/mcp/jin10-market-analysis
```

2. 设置 Token 环境变量：

```bash
export JIN10_MCP_TOKEN="你的Bearer Token"
```

3. 在 Hermes 中加载 Skill：

```bash
hermes skill load jin10-market-analysis
```

4. 使用。例如：

```
> 今天适合关注哪个市场方向？

> 黄金今天怎么看？

> 帮我分析一下今天的财经日历
```

### 方式二：直接使用 Python 脚本

本项目包含完整的 Python 客户端脚本，可在任何 Python 环境中独立使用：

```python
# 导入客户端
exec(open("scripts/jin10_client.py").read())
client = Jin10MCPClient()
client.initialize()
client.initialized()

# 获取黄金行情
quote = get_quote(client, "XAUUSD")
print(f"现货黄金: {quote['close']} ({quote['ups_percent']}%)")

# 获取财经日历
calendar = list_calendar(client)
for event in calendar:
    if event.get("star") == 3:
        print(f"{event['pub_time']} {event['title']}")

# 搜索快讯
items = search_flash(client, "美联储")
for item in items[:5]:
    print(item["content"])
```

完整流水线（采集 → 分析 → 报告）：

```bash
# 采集数据
python3 scripts/jin10_client.py --mode collect --token $JIN10_MCP_TOKEN \
  --output /tmp/market_data.json

# 分析评分
echo '{"quotes": {...}, "flashes": [...], "calendar": [...]}' | \
  python3 scripts/market_analyzer.py > /tmp/analysis.json

# 生成报告
cat /tmp/analysis.json | python3 scripts/report_template.py > /tmp/report.md
```

### 方式三：在支持 MCP 的客户端中配置

本项目基于标准 MCP (Model Context Protocol)。如果你使用支持 MCP 的客户端（如 Claude Desktop、VS Code 等），可配置为 MCP 服务：

```json
{
  "mcpServers": {
    "jin10": {
      "serverUrl": "https://mcp.jin10.com/mcp",
      "headers": {
        "Content-Type": "application/json",
        "Authorization": "Bearer ${JIN10_MCP_TOKEN}"
      }
    }
  }
}
```

然后通过 MCP 客户端直接调用工具：

| 操作 | MCP 调用 |
|------|----------|
| `get_quote({ "code": "XAUUSD" })` | 获取黄金行情 |
| `get_kline({ "code": "XAUUSD" })` | 获取黄金 K 线 |
| `list_flash({})` | 获取最新快讯 |
| `search_flash({ "keyword": "黄金" })` | 搜索黄金相关快讯 |
| `list_calendar({})` | 获取财经日历 |

---

## API 工具清单

| 工具 | 必填参数 | 可选参数 | 返回数据 | 用途 |
|------|---------|---------|---------|------|
| `get_quote` | `code` | — | `data.code, name, close, open, high, low, volume, ups_price, ups_percent` | 实时行情 |
| `get_kline` | `code` | `time`(秒级时间戳), `count`(1-100) | `data.klines[]`，每项含 open/high/low/close/volume/time | 分钟级 K 线 |
| `list_flash` | — | `cursor` | `data.items[], next_cursor, has_more` | 快讯流 |
| `search_flash` | `keyword` | `cursor` | 同上 | 搜索快讯 |
| `list_news` | — | `cursor` | `data.items[], next_cursor, has_more` | 资讯列表 |
| `search_news` | `keyword` | `cursor` | 同上 | 搜索资讯 |
| `get_news` | `id` | — | `data.id, title, introduction, time, url, content` | 文章详情 |
| `list_calendar` | `{}` | — | `data[]`，每项含 pub_time/star/title/previous/consensus/actual/revised/affect_txt | 财经日历 |

**资源：**

| 资源 URI | 说明 |
|----------|------|
| `quote://codes` | 获取所有支持的报价品种代码列表 |

### 常用品种代码

```
XAUUSD    现货黄金         XAGUSD    现货白银
USOIL     WTI 原油         UKOIL     布伦特原油
COPPER    现货铜           EURUSD    欧元/美元
USDJPY    美元/日元         USDCNH    美元/人民币
```

### ⚠️ 重要说明

- **`get_kline` 的 `time` 参数是 Unix 时间戳（秒）**，不是分钟数。传 `time=60` 会得到 1970 年 1 月 1 日的空数据。要获取最近 N 根 K 线，留空 `time` 即可。
- **所有 `content[0].text` 为 JSON 字符串**，需 `json.loads()` 再读取。
- **分页统一使用 `cursor` 参数**，响应中包含 `next_cursor` 和 `has_more`。
- **列表日历返回 `data` 直接为数组**（非 `data.items`）。

---

---

## 市场方向评分体系

### 评分模型

对 10 个市场方向分别从 5 个维度加权评分，**总分 100 分**：
<img width="2310" height="2808" alt="score_jjudge" src="https://github.com/user-attachments/assets/5eb73021-2520-4ecd-bdcc-df0548a394b9" />
| 维度 | 权重 | 说明 |
|------|------|------|
| **宏观环境** | 25% | 当前货币周期、通胀预期、利率方向对该方向的影响 |
| **新闻催化** | 25% | 近期快讯/资讯中的利好/利空关键词匹配 |
| **行情趋势** | 20% | 近期价格走势方向与动能 |
| **资金偏好** | 15% | 资金流向、南向/北向资金、主力资金态度 |
| **事件风险** | 15% | 星级事件未公布时分数低（风险可控度），已公布且利好则加分 |

> 事件风险分代表"风险可控程度"：无重大事件时分数高，高星级事件未公布时分数低。

**评分等级：**
- **80-100** 强关注
- **65-79** 可关注
- **50-64** 中性观察
- **35-49** 谨慎
- **0-34** 暂不关注

### 10 个市场方向

| # | 方向 | 代理品种 | 核心驱动 |
|---|------|---------|---------|
| 1 | **黄金/贵金属** | XAUUSD | 避险、降息、美元、地缘冲突、央行购金 |
| 2 | **原油/能源** | USOIL | 欧佩克、地缘冲突、库存、需求 |
| 3 | **美股科技** | NDX/SPX | AI、半导体、降息、财报 |
| 4 | **港股互联网** | HSI | 南向资金、平台经济、政策刺激 |
| 5 | **A股成长** | — | 政策、新能源、AI、国产替代 |
| 6 | **A股红利/防御** | — | 高股息、红利、避险、防御 |
| 7 | **日股** | USDJPY | 日元、日银政策、出口、回购 |
| 8 | **韩股** | — | 半导体、HBM、AI、出口 |
| 9 | **美元/外汇** | EURUSD | 利率差、美债、避险 |
| 10 | **债券/避险资产** | — | 降息预期、经济放缓、避险 |

### 市场环境判断 (Regime)

系统自动识别 4 种市场 Regime，不同 Regime 下对不同方向的推荐优先级不同：

| Regime | 特征 | 优先关注方向 | 回避方向 |
|--------|------|-------------|---------|
| **Risk-On** 📈 | 风险偏好高、科技股领涨 | 美股科技、韩股、港股、黄金 | 美元、美债 |
| **Risk-Off** 🛡️ | 避险情绪、地缘冲突 | 黄金、美债、美元 | 韩股、港股、原油 |
| **Inflation Trade** 🔥 | 通胀升温、商品涨 | 黄金、原油、商品 | 美债、成长股 |
| **Rate-Cut Trade** 💵 | 降息预期明确 | 黄金、科技股、债券 | 美元、银行股 |
<img width="2310" height="2808" alt="regime_mode" src="https://github.com/user-attachments/assets/811c1573-05a8-4941-beb5-6ab43e147947" />
### 各方向关键词规则

评分引擎通过搜索快讯流中的利好/利空关键词，自动调整新闻催化分。

**黄金方向：**
- 利好：`避险、地缘冲突、降息、美元走弱、美债收益率下行、通胀升温、央行购金`
- 利空：`美元走强、美债收益率上行、加息、风险偏好回升、通胀降温`

**原油方向：**
- 利好：`欧佩克减产、供应中断、地缘冲突、库存下降、需求强劲`
- 利空：`增产、库存增加、需求疲软、经济放缓`

**美股科技方向：**
- 利好：`降息预期、AI、芯片、半导体、财报超预期、流动性宽松`
- 利空：`利率上行、监管、估值过高、财报不及预期`

**港股互联网方向（含南向资金追踪规则）：**
- 南向净买入 > 50 亿且连续多日 → 增量资金入场，利好估值提升
- 南向净买入 > 80 亿 → 强烈信号
- 南向净卖出 > 50 亿 → 获利了结，短期回调压力
- 头部标的分布：腾讯、美团、中芯获买入 → 科技走强；银行、红利ETF → 防御偏好
- 板块轮动：煤炭/能源/银行走强 + AI/半导体回调 → 防御型切换信号
- 关键技术位：恒指 25,500~25,800 阻力区，24,500~24,800 入场区间

**韩股特别规则：**
- AI/HBM/半导体利好 → 加分
- 美元走强/韩元贬值/地缘风险 → 扣分
- 美股科技强势 → 小幅加分

### 港股合规提示（三条红线）

当用户询问港股入场时，必须包含：
1. **港股通**（50万门槛）→ 完全合规
2. **QDII基金**（百元起）→ 最省心，适合小额试水
3. **明确禁止**：地下钱庄、蚂蚁搬家、虚拟货币换汇出境
4. 券商推荐：富途牛牛 → 老虎/华盛 → 银行港股通 → QDII ETF

---

## 使用示例

### 获取黄金行情 + K 线

```python
from jin10_client import Jin10MCPClient

client = Jin10MCPClient()
client.initialize()
client.initialized()

# 实时行情
quote = get_quote(client, "XAUUSD")
print(f"{quote['name']}: {quote['close']} ({quote['ups_percent']}%)")

# 最近 K 线（不传 time 和 count，默认最近 100 根分钟级 K 线）
klines = get_kline(client, "XAUUSD")
for k in klines[-5:]:
    print(f"{k['time']} O={k['open']} H={k['high']} L={k['low']} C={k['close']}")
```

### 搜索特定主题快讯

```python
# 搜索黄金相关快讯
items = search_flash(client, "黄金")
for item in items:
    print(f"[{item['time'][:16]}] {item['content'][:100]}")
```

### 获取深度资讯文章

```python
# 先搜索
articles = search_news(client, "美联储")
for a in articles[:3]:
    print(f"  {a['id']}: {a['title'][:40]}")

# 再获取全文
article = get_news(client, articles[0]["id"])
print(article["content"])
```

### 查看今日财经日历

```python
events = list_calendar(client)
for evt in sorted(events, key=lambda x: x["pub_time"]):
    if evt.get("star") == 3:
        print(f"{evt['pub_time']} {evt['title']}")
        print(f"  前值={evt['previous']} 预期={evt['consensus']} 实际={evt.get('actual','待公布')}")
```

### 完整市场分析（全自动）

参见 [`examples/daily_market_prompt.md`](examples/daily_market_prompt.md)，在 Hermes 中发送预设 Prompt，即可触发完整的 10 方向市场扫描与评分。

---

## 项目文件结构

```
jin10-mcp-market-analysis/
├── SKILL.md                          # Hermes Agent Skill 主描述文件（评分规则、调用流程、关键词）
├── JIN10_API_REFERENCE.md            # API 完整参考（维度表、字段说明、错误处理）
├── .gitignore
├── scripts/
│   ├── jin10_client.py               # MCP 客户端（curl 子进程传输）
│   ├── market_analyzer.py            # 多市场方向评分引擎
│   └── report_template.py            # 中文 Markdown 报告渲染
├── references/
│   ├── get_kline-parameter-guide.md   # get_kline 参数详解
│   └── pipeline-notes.md             # 完整 pipeline 实现参考
└── examples/
    ├── daily_market_prompt.md         # 每日市场总览 Prompt
    ├── fund_direction_prompt.md       # 基金方向分析 Prompt
    └── gold_analysis_prompt.md        # 黄金专项分析 Prompt
```

| 文件 | 说明 |
|------|------|
| `scripts/jin10_client.py` | 底层 MCP 客户端。使用 curl 子进程传输（Python 3.14 + OpenSSL 3.5 与此服务器 SSL 握手间歇性失败，curl 100% 可靠） |
| `scripts/market_analyzer.py` | 多市场方向评分引擎。对 10 个方向分别从 5 个维度（宏观、新闻、趋势、资金、事件）加权评分 |
| `scripts/report_template.py` | 将评分 JSON 渲染为中文 Markdown 市场分析报告 |
| `references/get_kline-parameter-guide.md` | K 线参数详解 |
| `references/pipeline-notes.md` | 完整数据采集 → 分析 → 报告 pipeline 实现参考 |
| `examples/*.md` | 可供直接使用的 Prompt 模板 |

---

## 安全声明

> **本工具只提供财经信息整理和市场方向分析，不构成任何投资建议。**
>
> - 不允许输出确定性买卖建议
> - 不允许承诺收益
> - 不允许建议满仓、重仓、杠杆交易
> - 当数据不足时，应明确说明"数据不足，暂时只能中性观察"
>
> 市场有风险，投资需谨慎。请根据自身风险承受能力独立决策。

### Token 安全

- 建议通过**环境变量** `JIN10_MCP_TOKEN` 传入 Token，不要硬编码在代码或配置文件中
- `.gitignore` 已排除敏感文件，请勿提交 Token

---

## 许可证

MIT License

---

## 相关链接

- [金十数据官网](https://jin10.com)
- [Hermes Agent](https://hermes-agent.nousresearch.com)
- [Model Context Protocol (MCP) 规范](https://modelcontextprotocol.io)
- [GitHub 仓库](https://github.com/echosongg/jin10-mcp-market-analysis)
