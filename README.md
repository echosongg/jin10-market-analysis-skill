# jin10-market-analysis

> 基于金十数据 MCP 服务的财经市场分析 Hermes Agent Skill
>
> 实时行情 · 分钟级 K 线 · 快讯流 · 财经日历 · Watchlist 自定义方向评分 · HTML 交互看板

---

## 目录

- [这是什么](#这是什么)
- [快速开始](#快速开始)
- [每日使用流程](#每日使用流程)
- [Watchlist：自定义关注方向](#watchlist自定义关注方向)
- [评分体系](#评分体系)
- [HTML 看板](#html-看板)
- [文件结构](#文件结构)
- [API 速查](#api-速查)
- [已知限制](#已知限制)
- [安全声明](#安全声明)

---

## 这是什么

一个 [Hermes Agent](https://hermes-agent.nousresearch.com) Skill，通过金十数据的 MCP 服务拉取实时金融数据，对你**自定义的关注方向**（存储在 `references/watchlist.md`）进行五维评分，并生成固定结构的 HTML 交互看板。

**核心特点：**
- 关注方向完全由你控制，编辑 `watchlist.md` 即生效
- 看板结构固定（由 `scripts/report_html.py` 渲染，不随 AI 回答变化）
- 评分有依据：每个方向标注命中的利好/利空关键词，Regime 仪表盘显示触发判断的资产信号

---

## 快速开始

### 前置条件

- Python 3.10+（在 Python 3.14 + WSL/Ubuntu 下已验证）
- `curl`（用于 MCP 传输，比 Python httpx 在此服务器上更稳定）
- 金十数据 MCP Bearer Token

### 配置 Token

```bash
# 临时（当前会话）
export JIN10_MCP_TOKEN="your_token_here"

# 永久（写入 shell 配置）
echo 'export JIN10_MCP_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

### 验证连通性

```bash
cd ~/.hermes/skills/mcp/jin10-market-analysis
python3 scripts/jin10_client.py
# 看到黄金价格和最新快讯 = 连通成功
```

---

## 每日使用流程

### 方式一：直接问 Hermes（推荐）

打开 Hermes，说任意一句：

```
今天我的关注方向怎么看？
帮我生成 dashboard
今天适合关注哪些方向？
黄金今天怎么看？
给我今天的市场分析
```

Hermes 会自动：
1. 读取 `references/watchlist.md` 中你的关注方向
2. 调用金十 MCP 拉取快讯、行情、K线、日历
3. 对每个方向评分
4. 输出中文 Markdown 报告
5. 运行 `scripts/run_full_analysis.py` 生成 HTML 看板
6. 将文件复制到 `/mnt/c/Users/Ada39/Desktop/`，提示你打开

### 方式二：一键脚本

```bash
cd ~/.hermes/skills/mcp/jin10-market-analysis
python3 scripts/run_full_analysis.py
```

输出（当前目录）：
- `dashboard_YYYYMMDD_HHMM.html`：HTML 交互看板
- `report_YYYYMMDD_HHMM.md`：中文 Markdown 报告

复制到 Windows 桌面：
```bash
cp dashboard_*.html /mnt/c/Users/Ada39/Desktop/
```

---

## Watchlist：自定义关注方向

编辑 `references/watchlist.md` 即可更新关注方向，**无需改任何代码**。

### 文件格式

```markdown
| # | 方向 | 关键词（用于搜索快讯/新闻） | 代理品种代码 | 关注理由 |
|---:|------|---------------------------|-------------|---------|
| 1 | CPO（共封装光学） | CPO, 共封装光学, 光模块, 800G光模块 | — | AI算力驱动光互联升级 |
| 2 | 半导体 | 半导体, 芯片, HBM, AI芯片, 国产替代 | COPPER | AI算力核心载体 |
```

### 字段说明

| 字段 | 说明 |
|---|---|
| 方向 | 方向名称，显示在报告和看板里 |
| 关键词 | 逗号分隔，每次分析都会搜索这些关键词的快讯，同时作为评分依据 |
| 代理品种代码 | 填 Jin10 支持的代码（如 `COPPER`）则拉该代码的 K 线；填 `—` 则纯新闻驱动 |
| 关注理由 | 备注，不参与评分 |

### 常用代理代码

```
XAUUSD  现货黄金     USOIL   WTI 原油
COPPER  现货铜       USDJPY  美元/日元
USDCNH  美元/人民币  EURUSD  欧元/美元
```

### 添加新方向示例

在表格末尾加一行：
```markdown
| 7 | 储能/固态电池 | 储能, 固态电池, 磷酸铁锂, 宁德时代, 电芯 | — | 能源转型核心赛道 |
```

保存后，下次 Hermes 分析时自动包含这个方向。

---

## 评分体系

### 维度权重

Watchlist 方向多为无直接价格数据的主题方向，使用新闻驱动权重：

| 维度 | 权重 | 说明 |
|---|---|---|
| 新闻催化 | 30% | 关键词在快讯中的命中次数；命中 5+ 个自动标注「消息面活跃」 |
| 宏观环境 | 30% | 当前 Regime 对该方向类型的系统性加分 |
| 事件风险 | 20% | 高星日历事件（star=3）对该方向的影响；事件待公布时分数降低 |
| 行情趋势 | 10% | 有代理代码时用价格数据；否则按新闻强度代理 |
| 资金偏好 | 10% | Regime 对该方向资金偏好的加分 |

### 评分等级

| 分数 | 等级 |
|---|---|
| 80–100 | 强关注 |
| 65–79 | 可关注 |
| 50–64 | 中性观察 |
| 35–49 | 谨慎 |
| 0–34 | 暂不关注 |

### 关键词命中强度

| 命中数 | 信号强度 | 约分 |
|---|---|---|
| 0 | 无信号 | ~50 |
| 1–2 | 弱信号 | ~55–65 |
| 3–4 | 中等信号 | ~65–75 |
| 5+ | 强信号（标注「消息面活跃」） | ~75–90 |

### 市场 Regime

系统通过锚定资产组合自动判断当前 Regime，并在看板中显示判断依据：

| Regime | 判断条件 | 利好方向 |
|---|---|---|
| Risk-On | 黄金/美元弱 + 科技股新闻偏多 | 科技、AI、半导体、机器人 |
| Risk-Off | 黄金/美元同涨 + 科技股承压 | 煤炭/防御、黄金 |
| Inflation Trade | 油金齐涨 | 煤炭、能源、黄金 |
| Rate-Cut Trade | 黄金/科技同涨 + 降息信号 | AI、半导体、机器人、CPO |
| Liquidity Pressure | 美元强 + 科技弱 | 防御方向 |
| Mixed | 信号分散 | 无明显主线 |

---

## HTML 看板

### 看板结构（固定，每次一致）

| 板块 | 内容 |
|---|---|
| Hero 指标 | 当前 Regime · 最高关注方向 · 覆盖方向数 · 高星待发布事件数 |
| 01 数据流水线 | 可视化 MCP→采集→评分→输出全流程 |
| 02 雷达图 | 最高分方向的五维评分 |
| 03 排名条形图 | 所有方向按总分降序，颜色对应等级 |
| 04 Regime 仪表盘 | 当前 Regime 亮灯 + **判断依据**（哪些资产触发）+ 五个锚定资产涨跌 |
| 05 财经日历时间线 | star ≥ 2 事件，含预期 vs 实际对比 |
| 06 K 线图 | 最高分方向的 100 根分钟 K 线 + 成交量 + 压力/支撑位 |

### 固定生成命令

```bash
# 方式一：一键全流程（推荐）
python3 scripts/run_full_analysis.py

# 方式二：已有分析 JSON 时
cat result.json | python3 scripts/report_html.py

# 生成后复制到 Windows 桌面
cp dashboard_*.html /mnt/c/Users/Ada39/Desktop/
```

> ⚠️ **看板由 `scripts/report_html.py` 脚本渲染，结构固定。**
> Hermes 不应自己手写 HTML，否则每次结构不同。

---

## 文件结构

```
jin10-market-analysis/
├── SKILL.md                        # Hermes Skill 主描述文件（评分规则、调用流程）
├── JIN10_API_REFERENCE.md          # 金十 MCP API 完整字段参考
├── README.md                       # 本文件
│
├── scripts/
│   ├── jin10_client.py             # MCP 客户端（curl 子进程，SSE 解析，Session 管理）
│   ├── market_analyzer.py          # 评分引擎（标准10方向 + watchlist方向 + Regime判断）
│   ├── watchlist_loader.py         # 解析 references/watchlist.md
│   ├── report_template.py          # 中文 Markdown 报告渲染
│   ├── report_html.py              # 固定结构 HTML 看板渲染
│   ├── run_full_analysis.py        # 一键全流程脚本
│   └── mcp_integration_test.sh     # MCP 连通性验证脚本
│
├── references/
│   ├── watchlist.md                # ★ 你的关注方向列表（编辑此文件更新方向）
│   ├── JIN10_API_REFERENCE.md      # API 字段维度表
│   ├── get_kline-parameter-guide.md# get_kline 参数说明（time 是 Unix 时间戳秒数）
│   ├── pipeline-notes.md           # 实战 pipeline 记录（SSL问题、curl方案）
│   ├── known-limitations.md        # 已知限制（品种缺失、SSL兼容性等）
│   └── dashboard-rendering-patterns.md
│
└── examples/
    ├── daily_market_prompt.md      # 今日市场总览 Prompt
    ├── gold_analysis_prompt.md     # 黄金专项分析 Prompt
    └── fund_direction_prompt.md    # 基金方向分析 Prompt
```

---

## API 速查

### 工具清单

| 工具 | 必填参数 | 说明 |
|---|---|---|
| `get_quote` | `code` | 实时行情（open/close/high/low/ups_percent） |
| `get_kline` | `code` | 最近100根分钟K线，**不传 time/count**（传了可能返回空） |
| `list_flash` | — | 最新快讯列表，20条/页 |
| `search_flash` | `keyword` | 搜索快讯，最多150条 |
| `list_news` | — | 资讯列表，20条/页 |
| `search_news` | `keyword` | 搜索资讯，最多10条 |
| `get_news` | `id` | 单篇资讯全文 |
| `list_calendar` | `{}` | 财经日历，约260条，`data` 直接是数组 |

### 字段注意事项

```
get_kline:   klines[].open/close/high/low 是 string 类型，需 float() 转换
list_flash:  内容在 content 字段（无 title 字段）
list_calendar: star 最高为 3（非5星制），data 直接是数组（非 data.items）
```

### 常用品种代码

```
XAUUSD 现货黄金   XAGUSD 现货白银   USOIL WTI原油    UKOIL 布伦特原油
COPPER 现货铜     USDJPY 美元/日元  EURUSD 欧元/美元  USDCNH 美元/人民币
```

---

## 已知限制

| 限制 | 说明 |
|---|---|
| SSL 兼容性 | Python 3.14 + OpenSSL 3.5 与金十服务器 TLS 握手间歇性失败（~50%），`jin10_client.py` 使用 curl 子进程规避 |
| 无股票指数代码 | 韩股（KOSPI）、日股（N225）、港股（HSI）、美股（SPX）等股票指数无直接 Jin10 代码，通过快讯关键词间接判断 |
| 无 A 股个股 | 不支持 A股/港股/美股个股代码 |
| K线无参数控制 | `get_kline` 的 `time`/`count` 参数传错可能返回空数组，建议无参调用 |
| 日历最高星为3 | `star` 字段最大值为 3（不是常见的5星制） |

---

## 安全声明

> **本工具只提供财经信息整理和方向性分析，不构成任何投资建议。**
>
> - 不输出确定性买卖建议
> - 不承诺收益
> - 不建议满仓、重仓、杠杆交易
> - 数据不足时说明「中性观察」

Token 通过环境变量 `JIN10_MCP_TOKEN` 传入，不要硬编码在代码中。

---

## 相关链接

- [金十数据官网](https://jin10.com)
- [Hermes Agent](https://hermes-agent.nousresearch.com)
- [Model Context Protocol 规范](https://modelcontextprotocol.io)
