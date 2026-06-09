"""
watchlist_loader.py — 解析 references/watchlist.md，返回用户自定义关注方向配置。

每次调用 jin10-market-analysis skill 时动态读取，
修改 watchlist.md 即可更新关注方向，无需改代码。
"""
from __future__ import annotations
import re
from pathlib import Path

# watchlist.md 相对于本脚本目录的路径
_DEFAULT_PATH = Path(__file__).parent.parent / "references" / "watchlist.md"


def load_watchlist(path: str | Path | None = None) -> list[dict]:
    """
    解析 watchlist.md 中的方向表格。

    返回列表，每项：
    {
        "name":        str,         # 方向名称，如 "CPO（共封装光学）"
        "keywords":    list[str],   # 搜索关键词列表
        "codes":       list[str],   # 代理品种代码（无则空列表）
        "description": str,         # 关注理由
    }
    """
    fpath = Path(path) if path else _DEFAULT_PATH
    if not fpath.exists():
        return []

    text = fpath.read_text(encoding="utf-8")
    directions = []

    for line in text.splitlines():
        line = line.strip()
        # 跳过表头、分隔行、非数据行
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        # 跳过表头行（第一列不是数字）
        try:
            int(cells[0])
        except ValueError:
            continue

        name        = cells[1].strip()
        kw_raw      = cells[2].strip()
        codes_raw   = cells[3].strip()
        description = cells[4].strip() if len(cells) > 4 else ""

        # 解析关键词：支持逗号 / 顿号分隔，去空格
        keywords = [
            k.strip()
            for k in re.split(r"[,，、]", kw_raw)
            if k.strip() and k.strip() not in ("—", "-", "")
        ]

        # 解析代理品种代码
        codes = []
        if codes_raw not in ("—", "-", ""):
            codes = [
                c.strip()
                for c in re.split(r"[,，、/]", codes_raw)
                if c.strip() and c.strip() not in ("—", "-")
            ]

        if name:
            directions.append({
                "name":        name,
                "keywords":    keywords,
                "codes":       codes,
                "description": description,
            })

    return directions


def get_all_keywords(watchlist: list[dict]) -> list[str]:
    """返回所有方向关键词的去重列表（按出现顺序）。"""
    seen: set[str] = set()
    result = []
    for d in watchlist:
        for kw in d["keywords"]:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
    return result


def get_all_codes(watchlist: list[dict]) -> list[str]:
    """返回所有方向代理品种代码的去重列表。"""
    seen: set[str] = set()
    result = []
    for d in watchlist:
        for code in d["codes"]:
            if code not in seen:
                seen.add(code)
                result.append(code)
    return result


if __name__ == "__main__":
    import json
    wl = load_watchlist()
    print(f"加载了 {len(wl)} 个关注方向：")
    for d in wl:
        print(f"  [{d['name']}]")
        print(f"    关键词: {', '.join(d['keywords'][:5])}{'...' if len(d['keywords'])>5 else ''}")
        print(f"    代码:   {d['codes'] or '无（纯新闻驱动）'}")
    print(f"\n全部关键词（{len(get_all_keywords(wl))}个）：{get_all_keywords(wl)}")
    print(f"全部代码：{get_all_codes(wl)}")
