# 金十数据 MCP API 完整维度参考

> 本文件由实际调用结果整理，是 SKILL.md 的精确补充。
> 开发和调试时以本文件为准，SKILL.md 提供分析流程和评分规则。

---

## 一、数据源维度

| 维度 | 说明 |
|---|---|
| 协议 | MCP (Model Context Protocol)，SSE + `Mcp-Session-Id` |
| 服务端点 | `https://mcp.jin10.com/mcp` |
| 协议版本 | `2025-11-25` |
| 认证方式 | Bearer Token（环境变量 `JIN10_MCP_TOKEN`） |
| 会话机制 | 首次 POST `initialize` 后，从响应头获取 `Mcp-Session-Id`，后续请求携带该头维持会话 |
| Session 有效期 | 约数小时；过期时服务端返回 `-32603 Internal error`，需重新 `initialize` 建立新会话 |

---

## 二、工具维度（共 7 个）

| 工具 | 必填参数 | 可选参数 | 响应结构 | 说明 |
|---|---|---|---|---|
| `get_quote` | `code` | — | `data` dict | 实时行情报价 |
| `get_kline` | `code` | `time`(分钟字符串), `count` | `data.klines[]` | K线数据（⚠️ 见注意事项） |
| `list_flash` | — | `cursor` | `data.items[]` + `next_cursor` + `has_more` | 快讯流，20条/页 |
| `search_flash` | `keyword` | `cursor` | 同上 | 搜索快讯，上限 150 条（一次拉满） |
| `list_news` | — | `cursor` | `data.items[]` + `next_cursor` + `has_more` | 资讯流，20条/页 |
| `search_news` | `keyword` | `cursor` | 同上 | 搜索资讯，上限 10 条 |
| `get_news` | `id` | — | `data` dict | 单篇资讯完整内容 |
| `list_calendar` | `{}` (空对象) | — | `data[]`（直接数组，非嵌套） | 财经日历，一次拉满约 260 条 |

### ⚠️ get_kline 注意事项

- 传入 `time` / `count` 参数时可能返回**空数组**，属于已知问题。
- **推荐调用方式**：不传任何可选参数，默认返回最近 100 根**分钟级** K线。
- 若需更长周期，通过时间戳过滤本地处理，不要依赖 `time` 参数。

```python
# 推荐
get_kline(client, "XAUUSD")              # 返回最近100根分钟K线

# 可能返回空数组，慎用
get_kline(client, "XAUUSD", time="1h", count=24)
```

---

## 三、字段维度

### `get_quote` — 实时行情

| 字段 | 类型 | 描述 | 示例 |
|---|---|---|---|
| `code` | string | 品种代码 | `XAUUSD` |
| `name` | string | 品种名称 | `现货黄金` |
| `time` | string (ISO 8601) | 报价时间 | `2026-06-01T14:00:36+08:00` |
| `open` | number | 开盘价 | `4522.43` |
| `close` | number | 当前价 | `4516.57` |
| `high` | number | 日内最高 | `4545.95` |
| `low` | number | 日内最低 | `4508.64` |
| `volume` | number | 成交量 | `49855` |
| `ups_price` | number | 涨跌额 | `-23.36` |
| `ups_percent` | number | 涨跌幅 (%) | `-0.51` |

> `open/close/high/low/ups_price/ups_percent` 均为 **number 类型**，可直接做数值运算。

---

### `get_kline` — K线数据

外层：

| 字段 | 类型 | 描述 |
|---|---|---|
| `code` | string | 品种代码 |
| `name` | string | 品种名称 |
| `klines` | array | K线数组 |

`klines[]` 每项：

| 字段 | 类型 | 描述 | 示例 |
|---|---|---|---|
| `time` | integer | Unix 秒时间戳 | `1780293660` |
| `open` | **string** | 开盘价 | `"4517.33"` |
| `close` | **string** | 收盘价 | `"4516.10"` |
| `high` | **string** | 最高价 | `"4517.33"` |
| `low` | **string** | 最低价 | `"4516.10"` |
| `volume` | integer | 成交量 | `11` |

> ⚠️ **K线价格字段为 string 类型**，计算前必须 `float(k["close"])` 转换。

---

### `list_flash` / `search_flash` — 快讯

`data.items[]` 每项：

| 字段 | 类型 | 描述 | 示例 |
|---|---|---|---|
| `content` | string | 快讯正文 | `"英国5月...于十分钟后公布"` |
| `time` | string (ISO 8601) | 时间 | `"2026-06-01T13:50:00+08:00"` |
| `url` | string | 原文链接 | `"https://flash.jin10.com/detail/..."` |

分页字段（`data` 层级）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `next_cursor` | string | 下一页游标，如 `"1780290921585"` |
| `has_more` | boolean | 是否还有更多 |

> 快讯无 `title` 字段，内容在 `content` 字段。

---

### `list_news` / `search_news` — 资讯列表

`data.items[]` 每项：

| 字段 | 类型 | 描述 | 示例 |
|---|---|---|---|
| `id` | integer | 文章 ID | `220845` |
| `title` | string | 标题 | `"特朗普推动强制绑定..."` |
| `introduction` | string | 摘要/导语 | `"随着美伊谈判持续..."` |
| `time` | string (ISO 8601) | 发布时间 | `"2026-06-01T13:50:23+08:00"` |
| `url` | string | 链接 | `"https://xnews.jin10.com/details/..."` |

分页字段同快讯（`next_cursor` / `has_more`）。

---

### `get_news` — 资讯详情

| 字段 | 类型 | 描述 | 示例 |
|---|---|---|---|
| `id` | integer | 文章 ID | `220845` |
| `title` | string | 标题 | — |
| `introduction` | string | 摘要 | — |
| `time` | string (ISO 8601) | 发布时间 | — |
| `url` | string | 链接 | — |
| `content` | string | 完整正文（纯文本） | 约 5000+ 字符 |

---

### `list_calendar` — 财经日历

> ⚠️ `data` 直接是**数组**，不是 `data.items`，不需要 `.get("items")`。

每项：

| 字段 | 类型 | 描述 | 示例 |
|---|---|---|---|
| `pub_time` | string | 公布时间 | `"2026-06-01 07:00"` |
| `star` | **int** (1-3) | 重要度（非 string） | `2` |
| `title` | string | 事件名称 | `"澳大利亚5月标普全球制造业PMI终值"` |
| `previous` | string \| null | 前值 | `"50.2"` |
| `consensus` | string \| null | 预期值 | `null` |
| `actual` | string \| null | 实际值（未公布为 null） | `"50.7"` |
| `revised` | string \| null | 修正值 | `null` |
| `affect_txt` | string | 影响判断文字 | `"利多"` |

> ⚠️ `star` 是 **int**，比较时用 `int(event["star"]) >= 3`，不要用字符串比较。
> ⚠️ 金十日历 `star` 最高为 **3**（非 5 星制），`star == 3` 即为最高重要级别。

---

## 四、品种维度（共 97 个）

### 贵金属（19个）

```
XAUUSD    现货黄金（美元）
XAGUSD    现货白银（美元）
XPTUSD    现货铂金（美元）
XPDUSD    现货钯金（美元）
XAUXUSD   黄金（延伸品种）
XAGXUSD   白银（延伸品种）
XPTXUSD   铂金（延伸品种）
XPDXUSD   钯金（延伸品种）
ICNYXAU   人民币黄金（工行系列）
ICNYXAG   人民币白银
ICNYXPT   人民币铂金
ICNYXPD   人民币钯金
IUSDXAU   美元黄金（工行系列）
IUSDXAG   美元白银
IUSDXPT   美元铂金
IUSDXPD   美元钯金
ACNYXAU   人民币黄金（农行系列）
ACNYXAG   人民币白银（农行系列）
AUSDXAU   美元黄金（农行系列）
AUSDXAG   美元白银（农行系列）
```

### 能源（5个）

```
USOIL     WTI 原油
UKOIL     布伦特原油
USOILX    WTI 原油（延伸）
UKOILX    布伦特原油（延伸）
NGAS      天然气
```

### 外汇（9个）

```
EURUSD    欧元/美元
USDJPY    美元/日元
GBPUSD    英镑/美元
USDCHF    美元/瑞郎
USDCAD    美元/加元
AUDUSD    澳元/美元
NZDUSD    纽元/美元
USDCNH    美元/人民币（离岸）
USDHKD    美元/港元
```

### A 股指数（5个）

```
000001    上证综指
399001    深证成指
399006    创业板指
000300    沪深300
899050    北证50
```

### 全球指数（12个）

```
DJI       道琼斯工业
SPX       标普500
N225      日经225
HSI       恒生指数
KS11      韩国综合指数（KOSPI）
FCHI      法国 CAC40
GDAXI     德国 DAX
FTSE      英国富时100
AEX       荷兰 AEX
IBEX      西班牙 IBEX35
FTMIB     意大利 FTMIB
IRTS      俄罗斯 RTS
```

### 银行积存金（5个）

```
ICBCJCJ   工行积存金
CMBCJCJ   招行积存金
ZHJCJ     中行积存金
CZBJCJ    建行积存金
ICBCRYJCJ 工行人民币积存金
```

### 大宗商品（1个）

```
COPPER    现货铜
```

### 其他（约 41 个）

包括：工行账户系列（`ICHF`、`IJPY`、`IUSDCHF` 等）、暗盘参考价（`COPPERXUSD`、`PAXGUSD` 等）、各国指数（`BVSP`、`TASI`、`XU100`、`JKSE` 等）。

**不支持：** A股个股、港股个股、美股个股、加密货币。

---

## 五、分页维度

| 工具 | 请求分页参数 | 响应游标字段 | 有更多标志 | 每页条数 |
|---|---|---|---|---|
| `list_flash` | `cursor` | `data.next_cursor` | `data.has_more` | 20 |
| `search_flash` | `cursor`（可选） | `data.next_cursor` | `data.has_more` | 150（通常一次拉满） |
| `list_news` | `cursor` | `data.next_cursor` | `data.has_more` | 20 |
| `search_news` | `cursor`（可选） | `data.next_cursor` | `data.has_more` | 10 |
| `list_calendar` | 无 | 无 | 无 | 约 260（一次拉满） |
| `get_quote` | 无分页 | — | — | — |
| `get_kline` | 无分页 | — | — | 默认 100 根 |

---

## 六、错误维度

| 错误类型 | 表现 | 处理方式 |
|---|---|---|
| Session 过期 | JSON-RPC error `-32603 Internal error` | 重新调用 `initialize` → `initialized` 获取新 Session |
| 工具业务错误 | `isError: true` | 检查 `code` 是否在支持列表；个股/加密货币不支持 |
| 参数错误 | JSON-RPC `error` 字段 | 不要传未声明参数（如 `offset`、`page`、`limit`） |
| K线参数异常 | 传 `time`/`count` 返回空数组 | 改用无参调用，获取默认 100 根分钟 K线 |
| Token 无效 | HTTP 401 | 检查 `JIN10_MCP_TOKEN` 环境变量是否正确 |

---

## 七、关键使用规则速查

```python
# ✅ 日历：data 直接是数组
events = result["data"]                    # 正确
events = result["data"]["items"]           # ❌ 错误

# ✅ 日历 star：int 类型，最高为 3
if int(event["star"]) >= 3: ...            # 正确（不是 >= 4 或 >= 5）

# ✅ K线价格：string 类型需转换
price = float(kline["close"])              # 正确
price = kline["close"] + 1                # ❌ 类型错误

# ✅ 快讯内容字段是 content，无 title
text = flash_item["content"]               # 正确
text = flash_item["title"]                 # ❌ 无此字段

# ✅ K线推荐无参调用
result = client.call_tool("get_kline", {"code": "XAUUSD"})   # ✅
result = client.call_tool("get_kline", {"code": "XAUUSD",    # ⚠️ 可能返回空
                           "time": "1h", "count": 24})

# ✅ Session 过期重建
try:
    result = client.call_tool("get_quote", {"code": "XAUUSD"})
except MCPError as e:
    if e.code == -32603:                   # Session 过期
        client.initialize()
        client.initialized()
        result = client.call_tool("get_quote", {"code": "XAUUSD"})
```

---

## 八、推荐品种速查表（市场分析常用）

| 方向 | 推荐代码 | 备注 |
|---|---|---|
| 黄金 | `XAUUSD` | 最流动的贵金属 |
| 白银 | `XAGUSD` | 贵金属+工业属性 |
| WTI 原油 | `USOIL` | 美国基准油价 |
| 布伦特原油 | `UKOIL` | 国际基准油价 |
| 铜 | `COPPER` | 全球经济景气代理 |
| 天然气 | `NGAS` | 欧洲能源危机敏感品 |
| 美元/日元 | `USDJPY` | 日股/日元方向代理 |
| 欧元/美元 | `EURUSD` | 欧洲经济/美元强弱 |
| 美元/人民币 | `USDCNH` | A股/港股外资信号 |
| 韩国综合 | `KS11` | 韩股大盘（KOSPI） |
| 日经 225 | `N225` | 日股大盘 |
| 标普 500 | `SPX` | 美股大盘 |
| 道琼斯 | `DJI` | 美股蓝筹 |
| 恒生指数 | `HSI` | 港股大盘 |
| 上证综指 | `000001` | A股大盘 |
| 创业板 | `399006` | A股成长方向 |
