"""
report_html.py — 将分析 JSON 渲染为交互式 HTML 看板

用法：
    python scripts/market_analyzer.py | python scripts/report_html.py
    python scripts/report_html.py < result.json
    python scripts/run_full_analysis.py   # 一键执行全流程

输入（stdin）：run_full_analysis.py 或 market_analyzer.py 输出的扩展 JSON：
    {
      "regime": "risk-on",
      "directions": [...],
      "quotes": {"XAUUSD": {...}, ...},
      "klines": {"XAUUSD": {"klines": [...]}},
      "calendar": [...]
    }
"""
from __future__ import annotations
import json, sys, os
from datetime import datetime

REGIME_LABELS = {
    "risk-on":           "Risk-On 风险偏好高涨",
    "risk-off":          "Risk-Off 避险情绪主导",
    "inflation_trade":   "Inflation Trade 通胀交易",
    "rate_cut_trade":    "Rate-Cut Trade 降息交易",
    "liquidity_pressure":"Liquidity Pressure 流动性压力",
    "mixed":             "Mixed 混合状态",
}
ALL_REGIMES = list(REGIME_LABELS.keys())

DIRECTION_CODES = {
    "黄金/贵金属":  "XAUUSD",
    "原油/能源":    "USOIL",
    "日股":         "USDJPY",
    "美元/外汇":    "EURUSD",
    "债券/避险资产":"XAUUSD",
}

DISPLAY_QUOTES = [
    ("XAUUSD", "黄金"),
    ("USOIL",  "原油"),
    ("USDJPY", "美元/日元"),
    ("EURUSD", "欧元"),
    ("USDCNH", "人民币"),
]


def _build_payload(data: dict) -> dict:
    regime      = data.get("regime", "mixed")
    directions  = data.get("directions", [])
    raw_quotes  = data.get("quotes", {})
    raw_klines  = data.get("klines", {})
    raw_cal     = data.get("calendar", [])
    top         = directions[0] if directions else {}

    # ── 行情卡片 ─────────────────────────────────────────────
    quotes = []
    for code, fallback in DISPLAY_QUOTES:
        q = raw_quotes.get(code, {})
        if not q:
            continue
        try:
            pct = float(q.get("ups_percent", 0))
        except (TypeError, ValueError):
            pct = 0.0
        quotes.append({
            "name":  q.get("name") or fallback,
            "code":  code,
            "close": q.get("close", "—"),
            "pct":   round(pct, 2),
        })

    # ── K 线 ─────────────────────────────────────────────────
    top_code = DIRECTION_CODES.get(top.get("name", ""), "XAUUSD")
    kline_raw = raw_klines.get(top_code, {}).get("klines", [])
    klines = []
    for k in kline_raw[-100:]:
        try:
            klines.append({
                "t": k["time"],
                "o": float(k["open"]),
                "h": float(k["high"]),
                "l": float(k["low"]),
                "c": float(k["close"]),
                "v": int(k.get("volume", 0)),
            })
        except (KeyError, TypeError, ValueError):
            pass

    # 压力 / 支撑 估算（取近 50 根高低的均值）
    if klines:
        highs  = sorted(k["h"] for k in klines[-50:])
        lows   = sorted(k["l"] for k in klines[-50:])
        resist = round(highs[-5:][2], 2) if len(highs) >= 5 else None
        support= round(lows[:5][2], 2)   if len(lows)  >= 5 else None
    else:
        resist = support = None

    # ── 日历 ─────────────────────────────────────────────────
    calendar = []
    high_cal = sorted(
        [e for e in raw_cal if int(e.get("star", 0)) >= 2],
        key=lambda e: e.get("pub_time", "")
    )
    for e in high_cal[:8]:
        t = e.get("pub_time", "")
        calendar.append({
            "time":      t[-5:] if len(t) >= 5 else t,
            "star":      int(e.get("star", 0)),
            "title":     e.get("title", ""),
            "previous":  e.get("previous"),
            "consensus": e.get("consensus"),
            "actual":    e.get("actual"),
            "affect_txt":e.get("affect_txt", ""),
        })

    important_count = sum(
        1 for e in raw_cal
        if int(e.get("star", 0)) == 3 and not e.get("actual")
    )

    # ── 雷达数据 ─────────────────────────────────────────────
    radar = [
        round(top.get("macro",      50), 1),
        round(top.get("news",       50), 1),
        round(top.get("trend",      50), 1),
        round(top.get("fund",       50), 1),
        round(top.get("event_risk", 50), 1),
    ] if top else [50, 50, 50, 50, 50]

    return {
        "regime":           regime,
        "regime_label":     REGIME_LABELS.get(regime, regime),
        "all_regimes":      ALL_REGIMES,
        "top_direction":    top.get("name", "—"),
        "top_score":        top.get("total", 0),
        "top_level":        top.get("level", "—"),
        "important_events": important_count,
        "directions":       directions,
        "radar":            radar,
        "quotes":           quotes,
        "klines":           klines,
        "kline_code":       top_code,
        "resist":           resist,
        "support":          support,
        "calendar":         calendar,
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ── HTML 模板 ─────────────────────────────────────────────────
# DATA_JSON 占位符将被 Python 替换为真实 JSON。
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>金十 MCP 多市场分析看板</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0D1117;--panel:#161B22;--panel2:#0F172A;--border:#30363D;--text:#E6EDF3;--muted:#8B949E;--cyan:#22D3EE;--blue:#60A5FA;--green:#34D399;--yellow:#FBBF24;--orange:#FB923C;--red:#F87171;--purple:#A78BFA;}
*{box-sizing:border-box;}
body{margin:0;background:radial-gradient(circle at top left,rgba(34,211,238,.16),transparent 28%),radial-gradient(circle at top right,rgba(167,139,250,.12),transparent 25%),var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Arial,sans-serif;line-height:1.55;}
.page{max-width:1440px;margin:0 auto;padding:28px;}
.hero{display:grid;grid-template-columns:1.4fr .8fr;gap:18px;align-items:stretch;margin-bottom:18px;}
.title-card,.metric-card,.card{background:linear-gradient(180deg,rgba(22,27,34,.96),rgba(15,23,42,.94));border:1px solid var(--border);border-radius:22px;box-shadow:0 18px 50px rgba(0,0,0,.28);}
.title-card{padding:26px;position:relative;overflow:hidden;}
.title-card:after{content:"";position:absolute;width:260px;height:260px;right:-90px;top:-90px;background:radial-gradient(circle,rgba(34,211,238,.24),transparent 70%);}
h1{margin:0 0 10px;font-size:34px;letter-spacing:.4px;}
h2{margin:0 0 16px;font-size:20px;}
h3{margin:0;font-size:16px;}
.subtitle{color:var(--muted);max-width:760px;}
.hero-metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;}
.metric-card{padding:18px;}
.metric-label{color:var(--muted);font-size:13px;}
.metric-value{font-size:28px;font-weight:800;margin-top:4px;}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;}
.card{padding:20px;min-height:320px;}
.span-12{grid-column:span 12;}.span-7{grid-column:span 7;}.span-6{grid-column:span 6;}.span-5{grid-column:span 5;}.span-4{grid-column:span 4;}
.tag{display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border-radius:999px;border:1px solid rgba(96,165,250,.36);color:#BFDBFE;background:rgba(96,165,250,.1);font-size:12px;}
.section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px;}
.pipeline{display:grid;grid-template-columns:1.1fr .8fr .8fr .8fr;gap:14px;align-items:stretch;}
.pipe-col{border:1px solid rgba(48,54,61,.9);background:rgba(13,17,23,.55);border-radius:18px;padding:15px;position:relative;}
.pipe-col:not(:last-child)::after{content:"→";position:absolute;right:-18px;top:50%;transform:translateY(-50%);color:var(--cyan);font-size:26px;font-weight:800;}
.pipe-title{color:var(--cyan);font-weight:800;margin-bottom:10px;}
.pill-list{display:flex;flex-wrap:wrap;gap:8px;}
.pill{padding:6px 9px;border-radius:10px;background:rgba(96,165,250,.10);border:1px solid rgba(96,165,250,.22);color:#D8EAFE;font-size:12px;}
canvas{width:100%!important;max-height:430px;}
.rank-wrap{display:grid;grid-template-columns:1.1fr 1fr;gap:16px;align-items:start;}
.rank-notes{display:grid;gap:10px;}
.note{border:1px solid var(--border);border-radius:14px;padding:10px 12px;background:rgba(13,17,23,.52);font-size:13px;}
.note strong{color:var(--text);}
.positive{color:var(--green);}.risk{color:var(--orange);}
.regime-box{display:grid;grid-template-columns:.8fr 1.2fr;gap:18px;align-items:center;}
.traffic{border:1px solid var(--border);border-radius:24px;padding:18px;background:#0B1220;display:grid;gap:12px;}
.light{display:flex;align-items:center;gap:12px;padding:12px;border-radius:16px;background:rgba(255,255,255,.03);color:var(--muted);}
.dot{width:18px;height:18px;border-radius:50%;background:#3A3F4B;}
.active{color:var(--text);border:1px solid rgba(52,211,153,.34);background:rgba(52,211,153,.08);}
.active .dot{background:var(--green);box-shadow:0 0 20px rgba(52,211,153,.8);}
.asset-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;}
.asset{padding:13px;border-radius:16px;border:1px solid var(--border);background:rgba(13,17,23,.56);text-align:center;}
.asset .name{color:var(--muted);font-size:12px;}
.asset .chg{font-size:20px;font-weight:800;margin-top:5px;}
.timeline{position:relative;padding-left:22px;display:grid;gap:12px;}
.timeline:before{content:"";position:absolute;left:8px;top:6px;bottom:6px;width:2px;background:linear-gradient(var(--cyan),var(--purple));}
.event{position:relative;border:1px solid var(--border);border-radius:14px;padding:12px 14px;background:rgba(13,17,23,.54);}
.event:before{content:"";position:absolute;left:-20px;top:18px;width:12px;height:12px;border-radius:50%;background:var(--cyan);box-shadow:0 0 14px rgba(34,211,238,.8);}
.event-head{display:flex;justify-content:space-between;gap:12px;margin-bottom:6px;}
.time{color:#BFDBFE;font-weight:800;}.stars{color:var(--yellow);}
.mini{color:var(--muted);font-size:12px;}
.affected{display:inline-block;margin-top:7px;color:#C4B5FD;font-size:12px;}
.legend{display:flex;flex-wrap:wrap;gap:8px;color:var(--muted);font-size:12px;}
.up{color:var(--green);}.dn{color:var(--red);}.flat{color:var(--muted);}
@media(max-width:1100px){.hero,.rank-wrap,.regime-box{grid-template-columns:1fr;}.span-7,.span-6,.span-5,.span-4{grid-column:span 12;}.pipeline{grid-template-columns:1fr;}.pipe-col:not(:last-child)::after{content:"↓";right:50%;top:auto;bottom:-22px;transform:translateX(50%);}.asset-grid{grid-template-columns:repeat(2,1fr);}}
</style>
</head>
<body>
<main class="page">
  <section class="hero">
    <div class="title-card">
      <span class="tag">金十 MCP · 多市场 Regime 分析</span>
      <h1>财经市场智能分析看板</h1>
      <p class="subtitle">从实时行情、分钟级 K 线、快讯、深度资讯和财经日历中提取信号，对 10 个市场方向进行五维评分，并输出中文 Markdown 报告。</p>
      <p class="mini" id="ts"></p>
    </div>
    <div class="hero-metrics">
      <div class="metric-card"><div class="metric-label">当前 Regime</div><div class="metric-value" id="m-regime">—</div></div>
      <div class="metric-card"><div class="metric-label">最高关注方向</div><div class="metric-value" id="m-top">—</div></div>
      <div class="metric-card"><div class="metric-label">覆盖方向</div><div class="metric-value">10</div></div>
      <div class="metric-card"><div class="metric-label">高星待发布事件</div><div class="metric-value" id="m-events">—</div></div>
    </div>
  </section>

  <section class="grid">
    <div class="card span-12">
      <div class="section-head"><h2>01 数据流水线</h2><span class="tag">金十 MCP → 分析引擎 → HTML 看板</span></div>
      <div class="pipeline">
        <div class="pipe-col"><div class="pipe-title">金十 MCP 数据源</div><div class="pill-list"><span class="pill">get_quote 实时行情</span><span class="pill">get_kline 分钟K线</span><span class="pill">list_flash 快讯</span><span class="pill">search_flash 搜索快讯</span><span class="pill">list_news 深度资讯</span><span class="pill">search_news 搜索资讯</span><span class="pill">get_news 资讯详情</span><span class="pill">list_calendar 财经日历</span><span class="pill">quote://codes 品种代码</span></div></div>
        <div class="pipe-col"><div class="pipe-title">数据采集层</div><div class="pill-list"><span class="pill">jin10_client.py</span><span class="pill">Bearer Token</span><span class="pill">SSE + Session</span><span class="pill">字段清洗</span></div></div>
        <div class="pipe-col"><div class="pipe-title">评分与 Regime 引擎</div><div class="pill-list"><span class="pill">market_analyzer.py</span><span class="pill">五维评分</span><span class="pill">锚定资产组合</span><span class="pill">关键词匹配</span></div></div>
        <div class="pipe-col"><div class="pipe-title">看板输出层</div><div class="pill-list"><span class="pill">report_html.py</span><span class="pill">交互图表</span><span class="pill">雷达/条形/K线</span><span class="pill">中文 Markdown</span></div></div>
      </div>
    </div>

    <div class="card span-5">
      <div class="section-head"><h2>02 顶部方向五维雷达</h2><span class="tag" id="radar-tag">总分 — · —</span></div>
      <canvas id="radarChart"></canvas>
      <div class="legend">宏观25% · 新闻25% · 趋势20% · 资金15% · 风险15%</div>
    </div>

    <div class="card span-7">
      <div class="section-head"><h2>03 多方向排名</h2><span class="tag">按总分降序</span></div>
      <div class="rank-wrap">
        <canvas id="rankingChart"></canvas>
        <div class="rank-notes" id="rankNotes"></div>
      </div>
    </div>

    <div class="card span-6">
      <div class="section-head"><h2>04 市场 Regime 仪表盘</h2><span class="tag">锚定资产组合判断</span></div>
      <div class="regime-box">
        <div class="traffic" id="trafficLights"></div>
        <div>
          <div class="asset-grid" id="assetGrid"></div>
          <p class="mini" id="regimeDesc"></p>
        </div>
      </div>
    </div>

    <div class="card span-6">
      <div class="section-head"><h2>05 财经日历事件时间线</h2><span class="tag">预期 vs 实际 · star ≥ 2</span></div>
      <div class="timeline" id="calTimeline"></div>
    </div>

    <div class="card span-12">
      <div class="section-head"><h2>06 日内分钟 K 线</h2><span class="tag" id="kline-tag">最近100根分钟级K线</span></div>
      <canvas id="klineChart"></canvas>
      <p class="mini" id="klineDesc"></p>
    </div>
  </section>
</main>

<script>
const D = /*DATA_JSON*/null;

Chart.defaults.color = '#8B949E';
Chart.defaults.borderColor = 'rgba(139,148,158,0.18)';
Chart.defaults.font.family = '-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,Microsoft YaHei,Arial';

const levelColor = s => s>=80?'#34D399':s>=65?'#60A5FA':s>=50?'#FBBF24':s>=35?'#FB923C':'#F87171';
const levelText  = s => s>=80?'强关注':s>=65?'可关注':s>=50?'中性观察':s>=35?'谨慎':'暂不关注';

const REGIME_DESC = {
  'risk-on':           '科技、成长、新兴市场占优；风险资产全面走强。',
  'risk-off':          '黄金、美债、美元走强；股市和新兴市场承压。',
  'inflation_trade':   '原油、黄金等实物资产受追捧；通胀保值需求主导。',
  'rate_cut_trade':    '降息预期推升黄金、科技和债券；流动性宽松逻辑主导。',
  'liquidity_pressure':'美元走强压制新兴市场；资金回流美元资产。',
  'mixed':             '缺乏明显主线，各方向逻辑分散，精选催化剂为主。',
};
const REGIME_LABEL = {
  'risk-on':           'Risk-On 风险偏好高涨',
  'risk-off':          'Risk-Off 避险情绪主导',
  'inflation_trade':   'Inflation Trade 通胀交易',
  'rate_cut_trade':    'Rate-Cut Trade 降息交易',
  'liquidity_pressure':'Liquidity Pressure 流动性压力',
  'mixed':             'Mixed 混合状态',
};

// ── 1. Hero 指标 ───────────────────────────────────────────────
document.getElementById('ts').textContent = '生成时间：' + D.timestamp;
const regimeEl = document.getElementById('m-regime');
regimeEl.textContent = REGIME_LABEL[D.regime] || D.regime;
const regimeColors = {'risk-on':'#34D399','risk-off':'#F87171','inflation_trade':'#FB923C','rate_cut_trade':'#22D3EE','liquidity_pressure':'#A78BFA','mixed':'#FBBF24'};
regimeEl.style.fontSize = '18px';
regimeEl.style.color = regimeColors[D.regime] || '#E6EDF3';
document.getElementById('m-top').textContent = D.top_direction;
const evEl = document.getElementById('m-events');
evEl.textContent = D.important_events;
evEl.style.color = D.important_events > 3 ? '#F87171' : D.important_events > 0 ? '#FBBF24' : '#34D399';

// ── 2. 雷达图 ─────────────────────────────────────────────────
const top = D.directions[0] || {};
document.getElementById('radar-tag').textContent =
  `总分 ${top.total||'—'} · ${top.level||'—'}`;
new Chart(document.getElementById('radarChart'),{
  type:'radar',
  data:{
    labels:['宏观环境','新闻催化','行情趋势','资金偏好','事件风险'],
    datasets:[{
      label: D.top_direction,
      data: D.radar,
      backgroundColor:'rgba(34,211,238,.18)',
      borderColor:'#22D3EE',
      pointBackgroundColor:'#34D399',
      pointBorderColor:'#0D1117',
      borderWidth:2
    }]
  },
  options:{
    responsive:true,
    scales:{r:{min:0,max:100,ticks:{stepSize:20,backdropColor:'transparent'},grid:{color:'rgba(139,148,158,.18)'},angleLines:{color:'rgba(139,148,158,.18)'},pointLabels:{color:'#E6EDF3',font:{size:13}}}},
    plugins:{legend:{labels:{color:'#E6EDF3'}},tooltip:{callbacks:{label:ctx=>`${ctx.dataset.label}: ${ctx.raw}分`}}}
  }
});

// ── 3. 排名条形图 ────────────────────────────────────────────
new Chart(document.getElementById('rankingChart'),{
  type:'bar',
  data:{
    labels: D.directions.map(d=>d.name),
    datasets:[{
      label:'总分',
      data: D.directions.map(d=>d.total),
      backgroundColor: D.directions.map(d=>levelColor(d.total)),
      borderRadius:10,borderSkipped:false
    }]
  },
  options:{
    indexAxis:'y',responsive:true,
    scales:{
      x:{min:0,max:100,grid:{color:'rgba(139,148,158,.16)'}},
      y:{ticks:{color:'#E6EDF3'}}
    },
    plugins:{
      legend:{display:false},
      tooltip:{callbacks:{label:ctx=>`${ctx.raw}分 · ${levelText(ctx.raw)}`}}
    }
  }
});

// ── 4. Top-5 说明卡 ──────────────────────────────────────────
document.getElementById('rankNotes').innerHTML = D.directions.slice(0,5).map(d=>`
  <div class="note">
    <strong>${d.name}</strong> · <span style="color:${levelColor(d.total)}">${d.total}分 / ${d.level}</span><br/>
    <span class="positive">利好：</span>${(d.bullish_factors||[]).slice(0,3).join('、')||'—'}<br/>
    <span class="risk">风险：</span>${(d.bearish_factors||[]).slice(0,2).join('、')||'—'}
  </div>`).join('');

// ── 5. Regime 交通灯 ────────────────────────────────────────
document.getElementById('trafficLights').innerHTML = D.all_regimes.map(r=>`
  <div class="light ${D.regime===r?'active':''}">
    <span class="dot"></span>
    <span>${REGIME_LABEL[r]||r}</span>
  </div>`).join('');
document.getElementById('regimeDesc').textContent = REGIME_DESC[D.regime]||'';

// ── 6. 资产行情网格 ──────────────────────────────────────────
document.getElementById('assetGrid').innerHTML = D.quotes.map(q=>{
  const cls = q.pct>0?'up':q.pct<0?'dn':'flat';
  const sign = q.pct>0?'+':'';
  return `<div class="asset"><div class="name">${q.name}</div><div class="chg ${cls}">${sign}${q.pct}%</div></div>`;
}).join('');

// ── 7. 财经日历时间线 ────────────────────────────────────────
const stars = n => '★'.repeat(n) + '☆'.repeat(3-n);
document.getElementById('calTimeline').innerHTML = D.calendar.length
  ? D.calendar.map(e=>{
      const actual = e.actual != null ? e.actual : '<span style="color:var(--yellow)">待公布</span>';
      return `<div class="event">
        <div class="event-head"><span class="time">${e.time}</span><span class="stars">${stars(e.star)}</span></div>
        <h3>${e.title}</h3>
        <div class="mini">前值 ${e.previous??'—'} · 预期 ${e.consensus??'—'} · 实际 ${actual}</div>
        ${e.affect_txt?`<span class="affected">影响：${e.affect_txt}</span>`:''}
      </div>`;
    }).join('')
  : '<div class="mini" style="padding:20px">暂无高星事件数据</div>';

// ── 8. K 线 + 成交量 ────────────────────────────────────────
document.getElementById('kline-tag').textContent = `${D.kline_code} · 最近${D.klines.length}根分钟级K线`;

const kLabels = D.klines.map(k=>{
  const d = new Date(k.t * 1000);
  return `${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
});
const kClose  = D.klines.map(k=>k.c);
const kVol    = D.klines.map(k=>k.v);
const kColors = D.klines.map(k=>k.c>=k.o?'rgba(52,211,153,.35)':'rgba(248,113,113,.35)');

const datasets = [
  {type:'line',label:D.kline_code+' 价格',data:kClose,borderColor:'#22D3EE',backgroundColor:'rgba(34,211,238,.10)',tension:.22,pointRadius:0,yAxisID:'y'},
  {type:'bar', label:'成交量',data:kVol,backgroundColor:kColors,borderRadius:3,yAxisID:'y1'},
];
if(D.resist)  datasets.push({type:'line',label:'压力位 '+D.resist,data:kLabels.map(()=>D.resist),borderColor:'#F87171',borderDash:[6,5],pointRadius:0,yAxisID:'y'});
if(D.support) datasets.push({type:'line',label:'支撑位 '+D.support,data:kLabels.map(()=>D.support),borderColor:'#34D399',borderDash:[6,5],pointRadius:0,yAxisID:'y'});

new Chart(document.getElementById('klineChart'),{
  data:{labels:kLabels,datasets},
  options:{
    responsive:true,
    interaction:{mode:'index',intersect:false},
    scales:{
      y: {position:'left', title:{display:true,text:'价格'},grid:{color:'rgba(139,148,158,.14)'}},
      y1:{position:'right',title:{display:true,text:'成交量'},grid:{drawOnChartArea:false}},
      x: {ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:15}}
    },
    plugins:{legend:{labels:{color:'#E6EDF3'}}}
  }
});

if(D.resist||D.support){
  document.getElementById('klineDesc').textContent =
    `关键价位：${D.resist?'上方压力 '+D.resist+'；':''}${D.support?'下方支撑 '+D.support+'；':''}成交量放大突破压力时提高"行情趋势"分。`;
}
</script>
</body>
</html>"""


def render_html_dashboard(
    data: dict,
    output_path: str = "dashboard.html",
) -> str:
    """
    将扩展分析 JSON 渲染为 HTML 看板文件。

    参数：
        data         包含 regime/directions/quotes/klines/calendar 的完整字典
        output_path  输出 HTML 路径

    返回：
        输出文件绝对路径
    """
    payload = _build_payload(data)
    html = _TEMPLATE.replace("/*DATA_JSON*/null", json.dumps(payload, ensure_ascii=False))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(output_path)


if __name__ == "__main__":
    raw = sys.stdin.read().strip()
    if not raw:
        print("错误：请通过 stdin 传入分析 JSON（来自 market_analyzer.py 或 run_full_analysis.py）",
              file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"错误：JSON 解析失败：{e}", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out = f"dashboard_{ts}.html"
    path = render_html_dashboard(data, out)
    print(f"✅ HTML 看板已生成：{path}")
