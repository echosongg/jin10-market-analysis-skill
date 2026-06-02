# get_kline Parameter Guide

## Core Findings

The `get_kline` tool's `time` parameter is a **Unix timestamp in seconds**, **not** a period/minute value.

This is confirmed by the tool's `inputSchema`:
```json
{
  "time": {
    "type": "integer",
    "description": "起始 Unix 时间戳（秒），从此往后取数据，范围24小时内（可选，默认当前时间）"
  },
  "count": {
    "type": "integer",
    "description": "数据量，从 time 开始往后取 count 个分钟K线，范围1-100（可选，默认100）"
  }
}
```

## Usage Patterns

### 1. Get most recent N minute-candles (no time needed)
```python
klines = client.call_tool("get_kline", {"code": "XAUUSD", "count": 100})
```
→ Returns the last 100 minute-candles up to now. This is the most common pattern.

### 2. Get candles from a specific start time
```python
import time as ttime
start_ts = int(ttime.mktime(ttime.strptime("2026-06-01 09:00:00", "%Y-%m-%d %H:%M:%S")))
klines = client.call_tool("get_kline", {"code": "XAUUSD", "time": start_ts, "count": 100})
```

### 3. Using the convenience function
```python
from jin10_client import get_kline

# Most recent 100 candles
data = get_kline(client, "XAUUSD")

# From specific time + count
data = get_kline(client, "XAUUSD", time=start_ts, count=60)
```

## Common Mistakes

| Mistake | What happens |
|---|---|
| `time=60` | Unix timestamp for 1970-01-01 00:01 — returns empty klines |
| `time=5` | Same era; no data |
| `count=200` | Capped at 100 by server; max 100 |

## Return Structure

```json
{
  "data": {
    "code": "XAUUSD",
    "name": "现货黄金",
    "klines": [
      {
        "close": "4500.49",
        "high": "4501.00",
        "low": "4500.44",
        "open": "4500.90",
        "time": 1780299780,   // Unix timestamp in seconds
        "volume": 38
      }
    ]
  },
  "message": "",
  "status": 200
}
```

## Best Practice

For trend analysis, fetch ~100 minute-candles (no time param), then group into 5/15/60-min windows in Python:
```python
klines = data.get("klines", [])
for i in range(0, len(klines), 5):
    chunk = klines[i:i+5]
    o = float(chunk[0]["open"])
    h = max(float(k["high"]) for k in chunk)
    l = min(float(k["low"]) for k in chunk)
    c = float(chunk[-1]["close"])
    print(f"  O={o} H={h:.2f} L={l:.2f} C={c}")
```
