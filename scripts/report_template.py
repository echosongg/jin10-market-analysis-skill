"""
report_template.py — 将评分 JSON 渲染为中文 Markdown 市场分析报告
"""
from __future__ import annotations
import json, sys
from datetime import datetime

REGIME_LABELS = {
    "risk-on":           "风险偏好主导（Risk-On）",
    "risk-off":          "避险情绪主导（Risk-Off）",
    "inflation_trade":   "通胀交易主导",
    "rate_cut_trade":    "降息交易主导",
    "liquidity_pressure":"美元流动性收紧",
    "mixed":             "混合市场，无明显主线",
}

REGIME_DESC = {
    "risk-on":           "股票、科技、新兴市场资产占优，避险资产承压。",
    "risk-off":          "黄金、美债、美元走强，股市和新兴市场承压。",
    "inflation_trade":   "原油、黄金等实物资产受追捧，通胀保值需求主导。",
    "rate_cut_trade":    "降息预期推升黄金、科技股和债券，流动性宽松逻辑主导。",
    "liquidity_pressure":"美元走强压制新兴市场，资金回流美元资产。",
    "mixed":             "市场缺乏明显主线，各方向逻辑分散，需精选催化剂。",
}


def render_market_report(analysis_result: dict) -> str:
    regime = analysis_result.get("regime", "mixed")
    directions = analysis_result.get("directions", [])
    today = datetime.now().strftime("%Y年%m月%d日")

    lines = []

    # ── 标题 ─────────────────────────────────────────────────
    lines.append(f"# 金十数据市场方向分析报告")
    lines.append(f"> 生成时间：{today}  |  数据来源：金十数据 MCP")
    lines.append("")

    # ── 1. 今日结论 ──────────────────────────────────────────
    lines.append("## 一、今日结论")
    top3 = directions[:3]
    if top3:
        top_names = "、".join(d["name"] for d in top3)
        lines.append(
            f"当前市场处于 **{REGIME_LABELS.get(regime, regime)}** 环境，"
            f"今日相对更值得关注的方向为：**{top_names}**。"
        )
    else:
        lines.append("数据不足，暂时只能中性观察，请等待更多市场信号。")
    lines.append("")

    # ── 2. 市场环境判断 ───────────────────────────────────────
    lines.append("## 二、市场环境判断")
    lines.append(f"**当前 Regime：{REGIME_LABELS.get(regime, regime)}**")
    lines.append("")
    lines.append(REGIME_DESC.get(regime, ""))
    lines.append("")

    # ── 3. 多市场方向评分表 ────────────────────────────────────
    lines.append("## 三、多市场方向评分表")
    lines.append("")
    lines.append("| 排名 | 市场方向 | 总分 | 等级 | 核心利好 | 主要风险 |")
    lines.append("|---:|---|---:|:---:|---|---|")
    for i, d in enumerate(directions, 1):
        bulls = "、".join(d["bullish_factors"][:2]) if d["bullish_factors"] else "—"
        bears = "、".join(d["bearish_factors"][:2]) if d["bearish_factors"] else "—"
        lines.append(
            f"| {i} | {d['name']} | {d['total']} | {d['level']} | {bulls} | {bears} |"
        )
    lines.append("")

    # ── 4. Top 3 方向详情 ─────────────────────────────────────
    lines.append("## 四、Top 3 重点方向详情")
    lines.append("")
    for d in top3:
        lines.append(f"### {d['name']}：{d['total']}/100，{d['level']}")
        lines.append("")
        lines.append(f"| 维度 | 分数 |")
        lines.append(f"|---|---:|")
        lines.append(f"| 宏观环境（25%） | {d['macro']} |")
        lines.append(f"| 新闻催化（25%） | {d['news']} |")
        lines.append(f"| 行情趋势（20%） | {d['trend']} |")
        lines.append(f"| 资金偏好（15%） | {d['fund']} |")
        lines.append(f"| 事件风险（15%） | {d['event_risk']} |")
        lines.append("")

        if d["bullish_factors"]:
            lines.append("**利好因素：**")
            for f_ in d["bullish_factors"]:
                lines.append(f"- {f_}")
            lines.append("")

        if d["bearish_factors"]:
            lines.append("**风险因素：**")
            for f_ in d["bearish_factors"]:
                lines.append(f"- {f_}")
            lines.append("")

        if d["watch_list"]:
            lines.append("**需继续观察：**")
            for w in d["watch_list"]:
                lines.append(f"- {w}")
            lines.append("")

    # ── 5. 其余方向简评 ───────────────────────────────────────
    if len(directions) > 3:
        lines.append("## 五、其余方向简评")
        lines.append("")
        for d in directions[3:]:
            bulls = "、".join(d["bullish_factors"][:1]) if d["bullish_factors"] else "暂无明显催化"
            bears = "、".join(d["bearish_factors"][:1]) if d["bearish_factors"] else "暂无明显压力"
            lines.append(
                f"- **{d['name']}**（{d['total']}分，{d['level']}）：利好 {bulls}；风险 {bears}"
            )
        lines.append("")

    # ── 6. 重要待公布事件 ─────────────────────────────────────
    all_watches = []
    for d in directions:
        for w in d["watch_list"]:
            if w not in all_watches:
                all_watches.append(w)

    if all_watches:
        lines.append("## 六、今日重要待观察事件")
        lines.append("")
        for w in all_watches:
            lines.append(f"- {w}")
        lines.append("")

    # ── 7. 免责声明 ───────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("> **免责声明**")
    lines.append("> ")
    lines.append("> 以上内容仅为财经信息整合与方向性参考分析，**不构成任何投资建议**。")
    lines.append("> 市场存在不确定性，过去表现不代表未来收益，请根据自身风险承受能力独立决策。")
    lines.append("> 不建议满仓、重仓或使用杠杆。数据不足时请以「中性观察」为默认立场。")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    if raw:
        data = json.loads(raw)
    else:
        # 演示数据
        data = {
            "regime": "rate_cut_trade",
            "directions": [
                {"name": "黄金/贵金属", "total": 82.0, "level": "强关注",
                 "macro": 85, "news": 80, "trend": 78, "fund": 85, "event_risk": 70,
                 "bullish_factors": ["避险", "降息预期"], "bearish_factors": ["美元走强"],
                 "watch_list": ["CPI（待公布，预期 3.1%）"]},
                {"name": "债券/避险资产", "total": 75.0, "level": "可关注",
                 "macro": 78, "news": 74, "trend": 70, "fund": 80, "event_risk": 75,
                 "bullish_factors": ["降息预期"], "bearish_factors": [], "watch_list": []},
                {"name": "韩股", "total": 70.0, "level": "可关注",
                 "macro": 72, "news": 75, "trend": 65, "fund": 65, "event_risk": 68,
                 "bullish_factors": ["AI", "HBM", "半导体"], "bearish_factors": ["韩元贬值"],
                 "watch_list": []},
            ],
        }
    print(render_market_report(data))
