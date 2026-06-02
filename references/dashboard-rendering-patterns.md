# HTML Dashboard Rendering Patterns

本文件记录了 `report_html.py` 生成的交互式 HTML 看板 (dashboard) 的渲染模式、常见陷阱和修复记录。

## 核心结构

看板是单页 HTML，所有数据通过一个全局 JS 对象 `D` (或 `window.DATA`) 注入。模板使用 EJS 风格的内嵌 JS 渲染：`<%= D.field %>`。

## 常见陷阱

### 陷阱 1: JS 变量名与 JSON 实际结构不匹配

**现象：** 看板打开为空白（浏览器无报错但内容不渲染）。

**根因：** HTML 模板中硬编码了 `D.timestamp`、`D.radar`、`D.quotes`、`D.calendar`、`D.kline_code`、`D.klines`，但实际 JSON 数据对象结构是 `D.regime`(string) 和 `D.directions`(数组，每项含 name/total/macro/news/trend/fund/event_risk/bullish_factors/bearish_factors)。

**修复方案：** 在 HTML 模板中从 `D.directions` 动态提取 / 计算所有缺失字段的值：
- 雷达图 → 从最高分方向提取五维数据 (`directions[0].macro, .news, .trend, .fund, .event_risk`)
- 行情数据 → 如果有 `D.quotes` 就用，否则设为空 `{}`
- K线数据 → 从 `D.klines` 取，没有就用模拟数据
- 日历 → 从 `D.calendar` 取，没有就用空数组

### 陷阱 2: 日历数据为空的初始渲染

**现象：** 看板日历时间线显示"暂无数据"。

**原因：** 日历数据需要在运行时通过 `list_calendar({})` 实时获取后嵌入 HTML，不能使用模拟数据。

**正确做法：** 在生成看板前调用 `list_calendar`，将返回的 events 数组序列化到 HTML 的 `D.calendar` 字段中。

### 陷阱 3: `list_calendar` 返回结构特殊

`list_calendar` 的 `data` 是数组（不是 `data.items`），且 star 范围是 1-5（不是 1-3），非农等重大事件 star=5。

## 字节码注入日历数据的方式

在 `render_html_dashboard()` 或 `gen_dashboard.py` 中：

```python
# 将 raw JSON 序列化到 HTML
calendar_json = json.dumps(calendar_events, ensure_ascii=False)
html = html.replace(
    '"calendar": []',
    '"calendar": ' + calendar_json
)
```

或者直接在模板的 `<script>` 块中用 `<%= JSON.stringify(D.calendar) %>` 注入。

## 日历时间线 JS 渲染模式

```javascript
// 标准 renderCalendar 函数
function renderCalendar(events) {
  const pending = events.filter(e => (e.actual === null || e.actual === ''))
    .sort((a,b) => a.pub_time.localeCompare(b.pub_time));
  const published = events.filter(e => e.actual !== null && e.actual !== '')
    .sort((a,b) => b.pub_time.localeCompare(a.pub_time));
  
  // 待发布事件块 (升序)
  // 每个事件渲染: 星级(★重复) + 时间 + 标题 + 前值/预期 + 影响标签
  // 今日事件标记"今日"标签
  // 星标颜色: 5→红, 4→红, 3→黄, 2→蓝
  
  // 已发布关键事件块 (降序, 取 star>=2 的近8条)
  // 每个事件渲染: 星级 + 时间 + 标题 + 实际值/前值对比
  // 影响文本颜色: 利多→绿, 利空→红, 影响较小→灰
}
```

## 看板更新策略（用户偏好） — 方案三

用户倾向：**日常文字问答，只在关键时机更新看板**。

更新触发条件：
1. **用户主动要求**（如"更新看板"、"帮我刷新一下看板"）
2. **重大行情突破**（黄金破 4500/4470，原油突破关键位等）
3. **新的关键日历事件公布**（非农、利率决议等）

不更新看板的场景：
- 日常行情咨询（如"黄金今天怎么样"）→ 文字回答 + 表格即可
- 常规快讯/新闻摘要 → 文字回答

**看板文件命名规则：** 固定文件名 `jin10_dashboard.html`，每次更新直接覆盖，不生成时间戳版本。
**路径：** 同步到 `桌面/jin10_dashboard.html`（Windows 用户可见路径）。

## 单品种快速看板模式

当用户仅查询单一品种（如黄金）并要求更新看板时，可以使用**简化看板**替代完整的多方向评分看板：

**结构（4个卡片）：**
1. **报价卡片** — 品种代码 + 当前价 + 涨跌幅 + 开/高/低/量
2. **技术指标卡片** — VWAP + MA5 + MA10 + 日振幅 + 多空判断
3. **K线图卡片** — 1分钟K线图（60根）+ VWAP 线 + 关键价格标签
4. **今日日历卡片** — 当日 star>=2 的所有日历事件

**K线图渲染要点（Canvas 原生）：**
- 不使用外部图表库，纯 Canvas 2D API
- 阳线绿色（`#22c55e`），阴线红色（`#ef4444`）
- VWAP 线用虚线（`#f0b90b66`）
- 保留左右边距用于价格标签和时间标签
- 最后一条K线收盘价在右上角标注

**生成方式：** 用 Python `execute_code` 直接拼写 HTML 字符串（比调用 Python 脚本更快，减少跨进程开销），然后 `terminal cp` 到桌面。

## 看板文件的部署路径

WSL 环境下生成的 HTML 文件默认在 skill 的 `scripts/` 目录下，需要手动复制到用户可见位置：
```bash
cp dashboard_*.html /mnt/c/Users/<用户名>/Desktop/
```
并告知用户桌面上的 Windows 路径，不要只说"已生成"。
