"""
market_analyzer.py — 多市场方向评分引擎
输出结构化 JSON，供 report_template.py 渲染为中文报告。
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any

# ── 方向定义 ────────────────────────────────────────────────
DIRECTIONS = [
    "黄金/贵金属", "原油/能源", "美股科技", "港股互联网",
    "A股成长", "A股红利/防御", "日股", "韩股", "美元/外汇", "债券/避险资产"
]

# 关键词规则：(利好词列表, 利空词列表)
KEYWORD_RULES: dict[str, tuple[list[str], list[str]]] = {
    "黄金/贵金属": (
        ["避险", "地缘冲突", "战争", "冲突升级", "降息", "美元走弱",
         "美债收益率下行", "通胀升温", "央行购金"],
        ["美元走强", "美债收益率上行", "加息", "风险偏好回升", "通胀降温"],
    ),
    "原油/能源": (
        ["欧佩克减产", "OPEC减产", "供应中断", "地缘冲突", "库存下降",
         "需求强劲", "中东局势", "制裁"],
        ["增产", "库存增加", "需求疲软", "经济放缓", "原油需求下调"],
    ),
    "美股科技": (
        ["降息预期", "AI", "芯片", "半导体", "科技股", "纳斯达克",
         "财报超预期", "美债收益率下行", "流动性宽松"],
        ["利率上行", "美债收益率上行", "监管", "估值过高",
         "财报不及预期", "美元流动性收紧"],
    ),
    "港股互联网": (
        ["政策刺激", "流动性宽松", "平台经济", "互联网", "消费复苏",
         "美联储降息", "人民币企稳", "南向资金流入"],
        ["地产风险", "外资流出", "人民币贬值", "中美摩擦", "监管压力", "消费疲弱"],
    ),
    "A股成长": (
        ["政策刺激", "流动性宽松", "新能源", "半导体", "AI", "机器人",
         "消费电子", "国产替代", "科技创新"],
        ["风险偏好下降", "外资流出", "人民币贬值", "经济数据不及预期", "监管压力"],
    ),
    "A股红利/防御": (
        ["风险偏好下降", "高股息", "红利", "央企", "银行", "防御", "低波", "避险", "市场震荡"],
        ["成长风格占优", "风险偏好回升", "科技股大涨", "市场全面反弹"],
    ),
    "日股": (
        ["日元贬值", "日本央行宽松", "企业盈利改善", "回购", "外资流入",
         "通胀温和", "出口改善"],
        ["日元升值", "日本央行加息", "收益率上行", "消费疲弱", "外资流出", "避险情绪升温"],
    ),
    "韩股": (
        ["半导体", "存储芯片", "AI", "HBM", "三星电子", "SK海力士",
         "出口增长", "韩元企稳", "美元走弱", "外资流入", "全球科技股上涨", "风险偏好回升"],
        ["半导体需求疲软", "出口下滑", "韩元贬值", "美元走强", "外资流出",
         "地缘风险", "朝鲜", "韩国央行加息", "全球科技股回调"],
    ),
    "美元/外汇": (
        ["加息", "高利率", "美债收益率上行", "美国经济强劲", "避险", "美元走强", "通胀粘性"],
        ["降息", "经济放缓", "美债收益率下行", "美元走弱", "风险偏好回升"],
    ),
    "债券/避险资产": (
        ["降息预期", "经济放缓", "避险", "通胀降温", "美债收益率下行", "风险偏好下降"],
        ["通胀升温", "加息预期", "美债收益率上行", "经济强劲", "风险偏好回升"],
    ),
}

# 各方向对应的报价代码
DIRECTION_CODES: dict[str, list[str]] = {
    "黄金/贵金属":  ["XAUUSD", "XAGUSD"],
    "原油/能源":    ["USOIL", "UKOIL"],
    "美股科技":     [],
    "港股互联网":   [],
    "A股成长":      [],
    "A股红利/防御": [],
    "日股":         ["USDJPY"],
    "韩股":         [],
    "美元/外汇":    ["USDJPY", "EURUSD", "USDCNH"],
    "债券/避险资产":["XAUUSD"],
}

# regime 对方向的加分
REGIME_BONUS: dict[str, dict[str, int]] = {
    "risk-on": {
        "美股科技": 8, "港股互联网": 8, "A股成长": 7, "日股": 6, "韩股": 7,
    },
    "risk-off": {
        "黄金/贵金属": 9, "美元/外汇": 6, "债券/避险资产": 8, "A股红利/防御": 7,
    },
    "inflation_trade": {
        "原油/能源": 9, "黄金/贵金属": 7,
    },
    "rate_cut_trade": {
        "黄金/贵金属": 8, "美股科技": 7, "债券/避险资产": 7, "港股互联网": 6,
    },
    "liquidity_pressure": {
        "美元/外汇": 6, "债券/避险资产": 5, "A股红利/防御": 5,
    },
    "mixed": {},
}

# 重要日历事件关键词 → 影响方向
CALENDAR_RISK_MAP: dict[str, list[str]] = {
    "CPI":      ["黄金/贵金属", "美元/外汇", "债券/避险资产", "美股科技"],
    "PPI":      ["黄金/贵金属", "美元/外汇"],
    "非农":     ["黄金/贵金属", "美元/外汇", "债券/避险资产", "美股科技"],
    "失业率":   ["黄金/贵金属", "美元/外汇", "债券/避险资产"],
    "美联储":   ["黄金/贵金属", "美元/外汇", "债券/避险资产", "美股科技",
                  "港股互联网", "A股成长"],
    "EIA":      ["原油/能源"],
    "OPEC":     ["原油/能源"],
    "GDP":      ["美元/外汇", "债券/避险资产"],
    "零售销售": ["美元/外汇", "美股科技"],
    "PMI":      ["A股成长", "原油/能源"],
    "日本央行": ["日股", "美元/外汇"],
    "韩国央行": ["韩股"],
}


@dataclass
class DirectionScore:
    name: str
    macro: float = 50.0       # 宏观环境分 (0-100)
    news: float = 50.0        # 新闻催化分 (0-100)
    trend: float = 50.0       # 行情趋势分 (0-100)
    fund: float = 50.0        # 资金偏好分 (0-100)
    event_risk: float = 70.0  # 事件风险分/风险可控程度 (0-100)
    bullish_factors: list[str] = field(default_factory=list)
    bearish_factors: list[str] = field(default_factory=list)
    watch_list: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return (self.macro * 0.25 + self.news * 0.25 +
                self.trend * 0.20 + self.fund * 0.15 + self.event_risk * 0.15)

    @property
    def level(self) -> str:
        t = self.total
        if t >= 80: return "强关注"
        if t >= 65: return "可关注"
        if t >= 50: return "中性观察"
        if t >= 35: return "谨慎"
        return "暂不关注"


def _collect_news_text(news_items: list[dict]) -> str:
    """
    聚合新闻文本。
    快讯字段：content（无 title）
    资讯列表字段：title + introduction
    资讯详情字段：title + content
    """
    texts = []
    for item in news_items:
        # 快讯优先取 content，资讯优先取 title+introduction
        parts = []
        for key in ("content", "title", "introduction"):
            if item.get(key):
                parts.append(str(item[key]))
        if parts:
            texts.append(" ".join(parts))
    return " ".join(texts)


def _score_keywords(text: str, bullish_kws: list[str], bearish_kws: list[str]) -> tuple[float, list[str], list[str]]:
    """返回 (分数0-100, 命中利好词, 命中利空词)"""
    hits_bull = [kw for kw in bullish_kws if kw in text]
    hits_bear = [kw for kw in bearish_kws if kw in text]
    score = 50.0 + len(hits_bull) * 6 - len(hits_bear) * 6
    score = max(0.0, min(100.0, score))
    return score, hits_bull, hits_bear


def _score_trend(code: str, quote_map: dict[str, dict], kline_map: dict[str, dict]) -> float:
    """行情趋势评分，满分100（映射自原始+/-规则）"""
    score = 50.0  # 中性基准

    quote = quote_map.get(code, {})
    if quote:
        try:
            pct = float(quote.get("ups_percent", 0))
            if pct > 1:     score += 20
            elif pct > 0.3: score += 10
            elif pct < -1:  score -= 20
            elif pct < -0.3:score -= 10

            close = float(quote.get("close", 0))
            high  = float(quote.get("high", close))
            low   = float(quote.get("low", close))
            rng   = high - low
            if rng > 0:
                pos = (close - low) / rng
                if pos >= 0.95: score += 10
                elif pos <= 0.05: score -= 10
        except (TypeError, ValueError):
            pass

    kline = kline_map.get(code, {})
    klines = kline.get("klines", []) if kline else []
    if len(klines) >= 3:
        last3 = klines[-3:]
        try:
            # K线价格为 string，统一用 float() 转换
            if all(float(k["close"]) > float(k["open"]) for k in last3):
                score += 15
            elif all(float(k["close"]) < float(k["open"]) for k in last3):
                score -= 15
        except (KeyError, TypeError, ValueError):
            pass

    return max(0.0, min(100.0, score))


def _detect_regime(quote_map: dict[str, dict], news_text: str) -> str:
    gold  = quote_map.get("XAUUSD", {})
    oil   = quote_map.get("USOIL", {})
    usdcnh = quote_map.get("USDCNH", {})

    def pct(q): 
        try: return float(q.get("ups_percent", 0))
        except: return 0.0

    gold_up  = pct(gold) > 0.3
    gold_dn  = pct(gold) < -0.3
    usd_up   = pct(usdcnh) > 0.2
    oil_up   = pct(oil) > 0.5

    tech_up  = "科技" in news_text and "上涨" in news_text
    tech_dn  = "科技" in news_text and "下跌" in news_text

    if gold_up and usd_up and tech_dn: return "risk-off"
    if not gold_up and not usd_up and tech_up: return "risk-on"
    if oil_up and gold_up: return "inflation_trade"
    if gold_up and tech_up and "降息" in news_text: return "rate_cut_trade"
    if usd_up and tech_dn: return "liquidity_pressure"
    return "mixed"


def _detect_regime_with_reason(
    quote_map: dict[str, dict], news_text: str
) -> tuple[str, list[str]]:
    """
    同 _detect_regime()，但额外返回触发该判断的证据列表。
    返回：(regime_str, [reason1, reason2, ...])
    """
    gold   = quote_map.get("XAUUSD", {})
    oil    = quote_map.get("USOIL",  {})
    usdcnh = quote_map.get("USDCNH", {})

    def pct(q):
        try: return float(q.get("ups_percent", 0))
        except: return 0.0

    gp = pct(gold)
    op = pct(oil)
    up = pct(usdcnh)

    gold_up  = gp  >  0.3
    gold_dn  = gp  < -0.3
    usd_up   = up  >  0.2
    oil_up   = op  >  0.5
    tech_up  = "科技" in news_text and "上涨" in news_text
    tech_dn  = "科技" in news_text and "下跌" in news_text

    signals: list[str] = []
    if gold_up:   signals.append(f"黄金 +{gp:.2f}%↑")
    if gold_dn:   signals.append(f"黄金 {gp:.2f}%↓")
    if usd_up:    signals.append(f"美元/人民币 +{up:.2f}%↑（美元偏强）")
    if not usd_up and up < -0.2: signals.append(f"美元/人民币 {up:.2f}%↓（美元偏弱）")
    if oil_up:    signals.append(f"原油 +{op:.2f}%↑")
    if tech_up:   signals.append("科技股新闻偏多")
    if tech_dn:   signals.append("科技股新闻偏空")
    if "降息" in news_text: signals.append("新闻含降息信号")

    if gold_up and usd_up and tech_dn:
        return "risk-off", signals + ["→ 黄金/美元同涨+科技承压 = 避险主导"]
    if not gold_up and not usd_up and tech_up:
        return "risk-on", signals + ["→ 黄金/美元弱+科技强 = 风险偏好高涨"]
    if oil_up and gold_up:
        return "inflation_trade", signals + ["→ 油金齐涨 = 通胀交易主导"]
    if gold_up and tech_up and "降息" in news_text:
        return "rate_cut_trade", signals + ["→ 黄金/科技同涨+降息信号 = 降息交易主导"]
    if usd_up and tech_dn:
        return "liquidity_pressure", signals + ["→ 美元强+科技弱 = 流动性收紧"]
    return "mixed", signals + ["→ 信号分散，无明显主线"]


def _score_event_risk(direction: str, calendar_items: list[dict]) -> tuple[float, list[str]]:
    """
    事件风险分（越可控越高），返回 (分, 观察事件列表)。
    star 最高为 3（金十日历为1-3制，非1-5制）。
    """
    score = 75.0
    watches = []
    for event in calendar_items:
        try:
            star = int(event.get("star", 0))
        except (TypeError, ValueError):
            star = 0
        if star < 3:  # 金十最高星为3，此处 star==3 即最高重要级
            continue
        title = str(event.get("title", ""))
        actual = event.get("actual")
        for kw, dirs in CALENDAR_RISK_MAP.items():
            if kw in title and direction in dirs:
                if actual is None or actual == "":
                    score -= 15
                    watches.append(f"{title}（待公布，预期 {event.get('consensus','?')}）")
                else:
                    watches.append(f"{title} 实际={actual} 预期={event.get('consensus','?')}")
    return max(10.0, min(100.0, score)), watches


def analyze_market_directions(
    news_items: list[dict],
    quote_map: dict[str, dict],
    kline_map: dict[str, dict],
    calendar_items: list[dict],
) -> dict[str, Any]:
    """
    核心评分函数。

    参数：
        news_items      快讯/资讯列表（每项含 title/content/text 等字段）
        quote_map       {code: quote_data} 实时行情映射
        kline_map       {code: kline_data} K线数据映射
        calendar_items  财经日历事件列表

    返回：
        {
          "regime": str,
          "directions": [DirectionScore.as_dict(), ...],  # 按 total 降序
        }
    """
    all_text = _collect_news_text(news_items)
    regime, regime_reasons = _detect_regime_with_reason(quote_map, all_text)

    scores: list[DirectionScore] = []
    for name in DIRECTIONS:
        ds = DirectionScore(name=name)

        # 1. 新闻催化分
        bull_kws, bear_kws = KEYWORD_RULES[name]
        news_score, hits_bull, hits_bear = _score_keywords(all_text, bull_kws, bear_kws)
        ds.news = news_score
        ds.bullish_factors.extend(hits_bull)
        ds.bearish_factors.extend(hits_bear)

        # 2. 宏观环境分（与新闻分同源但权重独立，加入 regime 修正）
        ds.macro = min(100.0, news_score + REGIME_BONUS.get(regime, {}).get(name, 0))

        # 3. 行情趋势分
        codes = DIRECTION_CODES.get(name, [])
        if codes:
            trend_scores = [_score_trend(c, quote_map, kline_map) for c in codes if c in quote_map or c in kline_map]
            ds.trend = sum(trend_scores) / len(trend_scores) if trend_scores else 50.0
        else:
            ds.trend = 50.0 + (news_score - 50) * 0.3

        # 4. 资金偏好分
        bonus = REGIME_BONUS.get(regime, {}).get(name, 0)
        ds.fund = min(100.0, 50.0 + bonus * 2.5)

        # 5. 事件风险分
        ds.event_risk, watches = _score_event_risk(name, calendar_items)
        ds.watch_list.extend(watches)

        # 额外：韩股 AI/HBM 特别规则
        if name == "韩股":
            ai_kws = ["AI", "HBM", "半导体", "存储芯片"]
            if any(kw in all_text for kw in ai_kws):
                tech_score = sum(1 for kw in ai_kws if kw in all_text) * 4
                ds.news = min(100.0, ds.news + tech_score)
                ds.macro = min(100.0, ds.macro + tech_score)
            if "朝鲜" in all_text or "地缘风险" in all_text:
                ds.event_risk = max(10.0, ds.event_risk - 15)
                ds.bearish_factors.append("地缘/朝鲜风险")
            tech_up_signal = quote_map.get("美股科技代理", {})
            if "美股科技" in all_text and "上涨" in all_text:
                ds.news = min(100.0, ds.news + 5)

        scores.append(ds)

    scores.sort(key=lambda d: d.total, reverse=True)

    return {
        "regime": regime,
        "regime_reasons": regime_reasons,
        "directions": [
            {
                "name": d.name,
                "total": round(d.total, 1),
                "level": d.level,
                "macro": round(d.macro, 1),
                "news": round(d.news, 1),
                "trend": round(d.trend, 1),
                "fund": round(d.fund, 1),
                "event_risk": round(d.event_risk, 1),
                "bullish_factors": list(dict.fromkeys(d.bullish_factors)),
                "bearish_factors": list(dict.fromkeys(d.bearish_factors)),
                "watch_list": list(dict.fromkeys(d.watch_list)),
            }
            for d in scores
        ],
    }


# ══════════════════════════════════════════════════════════════
# Watchlist 专用评分引擎
# ══════════════════════════════════════════════════════════════

# 宏观 Regime 对各类主题方向的通用加分映射
_REGIME_THEME_BONUS: dict[str, dict[str, float]] = {
    "risk-on": {
        "科技": 8, "AI": 8, "半导体": 8, "机器人": 7,
        "CPO": 7, "光模块": 6, "卫星": 5, "星链": 5,
    },
    "risk-off": {
        "煤炭": 6, "防御": 5,
    },
    "inflation_trade": {
        "煤炭": 7, "能源": 6,
    },
    "rate_cut_trade": {
        "科技": 8, "AI": 8, "半导体": 7, "机器人": 7, "CPO": 6,
    },
    "liquidity_pressure": {},
    "mixed": {},
}

# 财经日历事件对主题方向的影响关键词
_WATCHLIST_CALENDAR_MAP: dict[str, list[str]] = {
    "半导体": ["半导体", "芯片", "科技", "AI"],
    "机器人": ["科技", "AI", "制造业", "PMI"],
    "CPO": ["科技", "AI", "芯片", "光模块"],
    "商用卫星": ["航天", "卫星", "科技"],
    "星链": ["航天", "卫星", "SpaceX", "科技"],
    "煤炭": ["煤炭", "能源", "电力", "PMI"],
}


def _regime_bonus_for_direction(direction_name: str, keywords: list[str], regime: str) -> float:
    """根据 regime 和方向关键词估算资金偏好加分。"""
    bonus_map = _REGIME_THEME_BONUS.get(regime, {})
    if not bonus_map:
        return 0.0
    # 取方向名称 + 关键词中命中 bonus_map 最高的一项
    candidates = [direction_name] + keywords
    return max((bonus_map.get(c, 0.0) for c in candidates), default=0.0)


def _event_risk_for_watchlist(direction_name: str, keywords: list[str],
                               calendar_items: list[dict]) -> tuple[float, list[str]]:
    """
    针对 watchlist 方向的事件风险分。
    匹配逻辑：日历事件标题包含方向名称 / 关键词 / 已知映射词。
    """
    score = 75.0
    watches = []

    # 确定本方向关联的日历关键词
    cal_kws: set[str] = set()
    for cal_direction, cal_words in _WATCHLIST_CALENDAR_MAP.items():
        if cal_direction in direction_name or any(cal_direction in kw for kw in keywords):
            cal_kws.update(cal_words)
    # 直接用方向关键词的前5个也参与匹配
    cal_kws.update(keywords[:5])

    for event in calendar_items:
        try:
            star = int(event.get("star", 0))
        except (TypeError, ValueError):
            star = 0
        if star < 3:
            continue
        title = str(event.get("title", ""))
        actual = event.get("actual")
        if any(kw in title for kw in cal_kws):
            if actual is None or actual == "":
                score -= 12
                watches.append(f"{title}（待公布，预期 {event.get('consensus','?')}）")
            else:
                watches.append(f"{title} 实际={actual} 预期={event.get('consensus','?')}")

    return max(10.0, min(100.0, score)), watches


def analyze_watchlist_directions(
    watchlist: list[dict],
    news_items: list[dict],
    quote_map: dict[str, dict],
    kline_map: dict[str, dict],
    calendar_items: list[dict],
) -> dict:
    """
    基于用户 watchlist 的方向评分。

    参数：
        watchlist       watchlist_loader.load_watchlist() 的返回值
        news_items      快讯/资讯列表（content / title / introduction 字段）
        quote_map       {code: quote_data} 实时行情（用于 regime 判断和趋势评分）
        kline_map       {code: kline_data} K线（用于趋势评分）
        calendar_items  财经日历

    返回结构与 analyze_market_directions() 完全一致：
    {
        "regime": str,
        "directions": [...],
        "watchlist_mode": True,   # 标记本次为 watchlist 模式
    }

    评分权重（watchlist 方向无直接价格数据，新闻权重更高）：
        新闻催化分   30%
        宏观环境分   30%
        事件风险分   20%
        行情趋势分   10%   （有代理代码时使用价格，否则 50 中性）
        资金偏好分   10%
    """
    all_text = _collect_news_text(news_items)
    regime, regime_reasons = _detect_regime_with_reason(quote_map, all_text)

    scores: list[DirectionScore] = []

    for d_cfg in watchlist:
        name     = d_cfg["name"]
        keywords = d_cfg["keywords"]
        codes    = d_cfg["codes"]

        ds = DirectionScore(name=name)

        # ── 1. 新闻催化分（关键词命中）─────────────────────────
        hits_bull = [kw for kw in keywords if kw in all_text]
        # 利空词：暂无方向专属利空，使用通用负向词
        generic_bearish = ["监管打压", "需求疲软", "订单取消", "产能过剩", "价格下跌",
                           "业绩下滑", "亏损", "暂停", "调查"]
        hits_bear = [kw for kw in generic_bearish if kw in all_text]

        hit_score = min(100.0, 50.0 + len(hits_bull) * 7 - len(hits_bear) * 6)
        ds.news = hit_score
        ds.bullish_factors.extend(hits_bull[:6])
        ds.bearish_factors.extend(hits_bear[:3])

        # 命中关键词越多，说明近期消息面越活跃，做特别提示
        if len(hits_bull) >= 4:
            ds.bullish_factors.insert(0, f"消息面活跃（{len(hits_bull)}个关键词命中）")

        # ── 2. 宏观环境分（regime 偏好 + 新闻）────────────────
        regime_bonus = _regime_bonus_for_direction(name, keywords, regime)
        ds.macro = min(100.0, hit_score * 0.7 + 15 + regime_bonus)

        # ── 3. 行情趋势分─────────────────────────────────────
        if codes:
            trend_scores = [
                _score_trend(c, quote_map, kline_map)
                for c in codes if c in quote_map or c in kline_map
            ]
            ds.trend = sum(trend_scores) / len(trend_scores) if trend_scores else 50.0
        else:
            # 无代码：用新闻强度估算趋势代理
            ds.trend = 50.0 + (hit_score - 50) * 0.25

        # ── 4. 资金偏好分─────────────────────────────────────
        ds.fund = min(100.0, 50.0 + regime_bonus * 2.5)

        # ── 5. 事件风险分─────────────────────────────────────
        ds.event_risk, watches = _event_risk_for_watchlist(name, keywords, calendar_items)
        ds.watch_list.extend(watches)

        # ── 总分（watchlist 权重）────────────────────────────
        # 覆写 total 属性所用的权重 → 通过调整各维度实现等效
        # 实际总分 = news*30% + macro*30% + event*20% + trend*10% + fund*10%
        # DirectionScore.total 默认是 25/25/20/15/15，
        # 这里通过缩放使得效果接近 watchlist 权重
        ds.news  = min(100.0, ds.news  * 1.10)
        ds.macro = min(100.0, ds.macro * 1.10)
        ds.event_risk = min(100.0, ds.event_risk * 1.15)

        scores.append(ds)

    scores.sort(key=lambda d: d.total, reverse=True)

    return {
        "regime": regime,
        "regime_reasons": regime_reasons,
        "watchlist_mode": True,
        "directions": [
            {
                "name":            d.name,
                "total":           round(d.total, 1),
                "level":           d.level,
                "macro":           round(d.macro, 1),
                "news":            round(d.news, 1),
                "trend":           round(d.trend, 1),
                "fund":            round(d.fund, 1),
                "event_risk":      round(d.event_risk, 1),
                "bullish_factors": list(dict.fromkeys(d.bullish_factors)),
                "bearish_factors": list(dict.fromkeys(d.bearish_factors)),
                "watch_list":      list(dict.fromkeys(d.watch_list)),
            }
            for d in scores
        ],
    }


if __name__ == "__main__":
    # 单元测试
    sample_news = [
        {"title": "避险情绪升温，黄金大涨，美元走强"},
        {"title": "美联储官员释放降息信号，美债收益率下行"},
        {"title": "地缘冲突升级，原油库存下降，欧佩克减产"},
        {"title": "AI芯片半导体需求强劲，韩国三星电子HBM出货超预期"},
    ]
    sample_quote = {
        "XAUUSD": {"close": "2350", "open": "2310", "high": "2360",
                   "low": "2305", "ups_percent": "1.8"},
        "USOIL":  {"close": "82", "open": "80", "high": "83",
                   "low": "79", "ups_percent": "0.8"},
        "USDJPY": {"close": "155.2", "open": "154.8", "high": "155.5",
                   "low": "154.6", "ups_percent": "0.3"},
        "USDCNH": {"close": "7.25", "open": "7.26", "high": "7.27",
                   "low": "7.24", "ups_percent": "-0.1"},
    }
    result = analyze_market_directions(sample_news, sample_quote, {}, [])
    print(json.dumps(result, ensure_ascii=False, indent=2))
