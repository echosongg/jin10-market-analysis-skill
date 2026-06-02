# 黄金方向分析 Prompt

## 使用场景

当用户问"黄金今天怎么看"、"XAUUSD 走势分析"、"黄金现在值得关注吗"时使用。

---

## Prompt

```
请使用 jin10-market-analysis skill，对黄金/贵金属方向做深度分析。

调用步骤：
1. resources/read quote://codes  确认 XAUUSD / XAGUSD 可用
2. get_quote({ code: "XAUUSD" })  获取实时行情
3. get_quote({ code: "XAGUSD" })  获取白银行情作为参照
4. get_kline({ code: "XAUUSD", time: "1h", count: 24 })  获取近 24 小时 K 线
5. search_flash({ keyword: "黄金" })
6. search_flash({ keyword: "美联储" })
7. search_flash({ keyword: "美元" })
8. search_flash({ keyword: "美债收益率" })
9. search_flash({ keyword: "避险" })
10. search_flash({ keyword: "通胀" })
11. search_flash({ keyword: "央行购金" })
12. list_calendar({})  关注 CPI/PPI/非农/美联储相关高星事件

评分维度：
- 宏观环境：美元走向、美债收益率、货币政策预期
- 新闻催化：避险情绪、地缘冲突、通胀数据、央行动向
- 行情趋势：XAUUSD 涨跌幅、K 线形态（连续上涨/下跌、接近日内高低点）
- 资金偏好：当前 Regime 是否利好黄金（risk-off / rate_cut_trade / inflation_trade）
- 事件风险：今日是否有未公布的高星级数据

输出内容：
- 黄金方向综合评分（/100）和等级
- 利好因素列表
- 风险因素列表
- 技术面简析（基于 K 线和当前价格位置）
- 重点观察条件（哪些数据公布后会改变判断）
- 免责声明
```

---

## 典型触发问题

- "黄金今天怎么看？"
- "现在黄金值得买吗？"
- "XAUUSD 今天走势如何？"
- "黄金 ETF 今天方向怎么判断？"

---

## 注意事项

- 不得输出"黄金一定会涨/跌"的确定性表述
- 若 CPI / 非农 / 美联储决议今日待公布，必须在风险因素中明确提示"数据公布前波动放大风险"
- 若数据不足，说明"数据有限，黄金方向暂时中性观察"
