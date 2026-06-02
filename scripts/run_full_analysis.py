"""
run_full_analysis.py — 金十市场分析全流程一键脚本

执行顺序：
  1. 连接金十 MCP，初始化会话
  2. 并行拉取：行情、K线、快讯（多关键词）、财经日历
  3. 调用 market_analyzer 计算多方向评分
  4. 生成中文 Markdown 报告（report_template.py）
  5. 生成 HTML 交互看板（report_html.py）

用法：
  export JIN10_MCP_TOKEN="your_token"
  python scripts/run_full_analysis.py

输出：
  dashboard_YYYYMMDD_HHMM.html    交互式看板（浏览器打开）
  report_YYYYMMDD_HHMM.md         中文 Markdown 报告
"""
from __future__ import annotations
import json, sys, os
from datetime import datetime
from pathlib import Path

# 确保相对导入路径正确（从 scripts/ 目录执行也能找到同级模块）
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))

from jin10_client import (
    Jin10MCPClient, ToolError,
    get_quote, get_kline, list_flash, search_flash, list_calendar,
)
from market_analyzer import analyze_market_directions
from report_template import render_market_report
from report_html import render_html_dashboard

# 需要获取行情的品种
QUOTE_CODES = ["XAUUSD", "XAGUSD", "USOIL", "UKOIL", "USDJPY", "EURUSD", "USDCNH", "COPPER"]

# 关键词搜索列表
SEARCH_KEYWORDS = [
    "美联储", "通胀", "非农", "地缘政治", "原油", "黄金",
    "日本央行", "韩国", "半导体", "AI", "韩元", "欧佩克",
    "美债收益率", "人民币", "南向资金", "PMI", "CPI",
]


def _safe_call(client: Jin10MCPClient, fn, *args, **kwargs):
    """安全调用，出错时打印警告并返回默认值。"""
    try:
        return fn(client, *args, **kwargs)
    except ToolError as e:
        print(f"  ⚠️ 工具错误：{e}", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠️ 调用异常：{e}", file=sys.stderr)
    return {}


def run() -> dict:
    """执行完整分析，返回扩展结果 dict（包含 raw 数据，可直接喂给 report_html）。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    print("🚀 金十市场分析启动...")

    with Jin10MCPClient() as client:
        # ── 初始化 ────────────────────────────────────────────
        print("  连接金十 MCP 服务...")
        client.initialize()
        client.initialized()
        print("  ✅ 会话建立成功")

        # ── 行情 ──────────────────────────────────────────────
        print(f"  拉取 {len(QUOTE_CODES)} 个品种行情...")
        quote_map: dict[str, dict] = {}
        for code in QUOTE_CODES:
            q = _safe_call(client, get_quote, code)
            if q:
                quote_map[code] = q
                pct = q.get("ups_percent", 0)
                sign = "+" if float(pct) >= 0 else ""
                print(f"    {code:10s} {q.get('close','—')}  {sign}{pct}%")

        # ── K 线（仅获取分析需要的代码）─────────────────────
        print("  拉取 K 线（XAUUSD / USOIL / USDJPY）...")
        kline_map: dict[str, dict] = {}
        for code in ["XAUUSD", "USOIL", "USDJPY"]:
            kd = _safe_call(client, get_kline, code)
            if kd:
                kline_map[code] = kd
                print(f"    {code}  {len(kd.get('klines', []))} 根K线")

        # ── 快讯 ──────────────────────────────────────────────
        print("  拉取最新快讯...")
        news_items: list[dict] = []
        latest = _safe_call(client, list_flash)
        if latest:
            news_items.extend(latest.get("items", []))

        print(f"  搜索 {len(SEARCH_KEYWORDS)} 个关键词快讯...")
        seen_urls: set[str] = set()
        for kw in SEARCH_KEYWORDS:
            items = _safe_call(client, search_flash, kw) or []
            for item in items:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    news_items.append(item)
        print(f"  ✅ 共收集 {len(news_items)} 条快讯")

        # ── 财经日历 ──────────────────────────────────────────
        print("  拉取财经日历...")
        calendar_items = _safe_call(client, list_calendar) or []
        high_star = [e for e in calendar_items if int(e.get("star", 0)) >= 3]
        print(f"  ✅ 日历 {len(calendar_items)} 条，其中 ★★★ {len(high_star)} 条")

    # ── 评分 ──────────────────────────────────────────────────
    print("\n🧠 计算多市场方向评分...")
    analysis = analyze_market_directions(news_items, quote_map, kline_map, calendar_items)
    print(f"  Regime: {analysis['regime']}")
    for d in analysis["directions"][:3]:
        print(f"  #{analysis['directions'].index(d)+1} {d['name']}  {d['total']}分  {d['level']}")

    # ── 扩展结果（供 HTML 生成器使用）────────────────────────
    extended = {
        **analysis,
        "quotes":   quote_map,
        "klines":   {code: kdata for code, kdata in kline_map.items()},
        "calendar": calendar_items,
    }

    # ── 输出文件 ───────────────────────────────────────────────
    out_dir = Path.cwd()

    # Markdown 报告
    md_path = out_dir / f"report_{ts}.md"
    md_content = render_market_report(analysis)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\n📄 Markdown 报告：{md_path}")

    # HTML 看板
    html_path = out_dir / f"dashboard_{ts}.html"
    render_html_dashboard(extended, str(html_path))
    print(f"🌐 HTML 看板：{html_path}")
    print("\n✅ 分析完成！用浏览器打开 HTML 文件查看交互看板。")

    return extended


if __name__ == "__main__":
    result = run()
    # 同时将 JSON 输出到 stdout，方便管道使用
    print("\n--- JSON ---")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:500], "...(truncated)")
