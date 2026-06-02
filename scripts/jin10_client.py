"""
jin10_client.py — 金十数据 MCP 客户端

底层使用 curl 子进程（curl 100% 可靠，Python ssl 3.14 与服务器握手间歇性失败）。

Token：环境变量 JIN10_MCP_TOKEN
"""
from __future__ import annotations
import json, os, sys, subprocess, time
from typing import Any

MCP_URL = "https://mcp.jin10.com/mcp"
PROTOCOL_VERSION = "2025-11-25"
TIMEOUT = 15.0
_MAX_RETRIES = 3


def _get_token() -> str:
    token = os.environ.get("JIN10_MCP_TOKEN", "").strip()
    if not token:
        print(
            "错误：未找到 JIN10_MCP_TOKEN 环境变量，请先配置金十 MCP 访问令牌。\n"
            "示例：export JIN10_MCP_TOKEN='your_token_here'",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


class MCPError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(f"MCP协议错误[{code}]: {message}")
        self.code = code


class ToolError(Exception):
    """isError=true 时的工具业务错误"""


def _curl_post(payload: dict, session_id: str | None = None) -> tuple[dict, str | None]:
    """执行一次 curl POST 请求，返回 (parsed_jsonrpc, new_session_id)。

    用 -D- 输出响应头到 stdout（在 SSE body 之前），从中提取 Mcp-Session-Id。
    """
    data = json.dumps(payload)
    cmd = [
        "curl", "-s", "-D-", "--max-time", str(TIMEOUT), MCP_URL,
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {_get_token()}",
        "-d", data,
    ]
    if session_id:
        cmd.extend(["-H", f"Mcp-Session-Id: {session_id}"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 5)
    if result.returncode != 0:
        stderr = result.stderr.strip()[:200]
        raise ConnectionError(f"curl 请求失败 (rc={result.returncode}): {stderr}")

    # 输出格式: HTTP headers 后跟空行再跟 SSE body
    output = result.stdout
    sid = None

    # 分离 header 和 body
    header_end = output.find("\n\n")
    if header_end != -1:
        header_section = output[:header_end]
        body = output[header_end + 2:]
        for hl in header_section.split("\n"):
            hl = hl.strip()
            if hl.lower().startswith("mcp-session-id:"):
                sid = hl.split(":", 1)[1].strip()
                break
    else:
        body = output

    # 解析 SSE data: 行
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            parsed = json.loads(line[6:])
            return parsed, sid
    raise MCPError(-1, f"无法解析响应: {output[:200]}")


class Jin10MCPClient:
    """
    金十数据 MCP 客户端。

    基于 curl 子进程实现，解决 Python 3.14 SSL 握手兼容性问题。
    支持 session 过期自动重建（最多重试 _MAX_RETRIES 次）。
    """

    def __init__(self):
        self._token = _get_token()
        self._req_id = 0
        self._session_id: str | None = None

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _post(self, payload: dict, _retry: bool = True) -> dict:
        for attempt in range(_MAX_RETRIES):
            try:
                resp, sid = _curl_post(payload, self._session_id)
                if sid:
                    self._session_id = sid
                break
            except (ConnectionError, subprocess.TimeoutExpired) as e:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(1)
                    continue
                raise ConnectionError(f"金十 MCP 服务连接失败（重试{_MAX_RETRIES}次）: {e}")

        if "error" in resp:
            err = resp["error"]
            code = err.get("code", -1)
            # Session 过期自动重建
            if _retry and code == -32603:
                self._session_id = None
                self.initialize()
                self.initialized()
                return self._post(payload, _retry=False)
            raise MCPError(code, err.get("message", "未知错误"))

        return resp

    @staticmethod
    def _extract(result: dict) -> Any:
        if result.get("isError"):
            raw = result.get("content", [{}])[0].get("text", str(result))
            raise ToolError(f"工具业务错误：{raw}")
        content = result.get("content", [])
        if isinstance(content, list) and len(content) > 0:
            text = content[0].get("text", "")
            if text:
                try:
                    return json.loads(text)
                except Exception:
                    return {"raw_text": text}
        return content

    # ── MCP 协议方法 ──────────────────────────────────────────

    def initialize(self) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}, "resources": {}},
                "clientInfo": {"name": "hermes-jin10", "version": "1.0.0"},
            },
        }
        resp = self._post(payload, _retry=False)
        return resp.get("result", {})

    def initialized(self):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
            _curl_post(payload, self._session_id)
        except Exception:
            pass

    def list_tools(self) -> list[dict]:
        resp = self._post({
            "jsonrpc": "2.0", "id": self._next_id(),
            "method": "tools/list", "params": {},
        })
        return resp.get("result", {}).get("tools", [])

    def list_resources(self) -> list[dict]:
        resp = self._post({
            "jsonrpc": "2.0", "id": self._next_id(),
            "method": "resources/list", "params": {},
        })
        return resp.get("result", {}).get("resources", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        resp = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })
        return self._extract(resp.get("result", {}))

    def read_resource(self, uri: str) -> Any:
        resp = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/read",
            "params": {"uri": uri},
        })
        contents = resp.get("result", {}).get("contents", [])
        if contents:
            text = contents[0].get("text", "")
            if text:
                try:
                    return json.loads(text)
                except Exception:
                    return text
        return resp.get("result", {})

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# ── 便捷封装 ────────────────────────────────────────────────

def get_quote(c: Jin10MCPClient, code: str) -> dict:
    r = c.call_tool("get_quote", {"code": code})
    return r.get("data", {}) if isinstance(r, dict) else {}


def get_kline(c: Jin10MCPClient, code: str, time: int | None = None, count: int = 100) -> dict:
    args: dict = {"code": code, "count": count}
    if time is not None:
        args["time"] = time
    r = c.call_tool("get_kline", args)
    return r.get("data", {}) if isinstance(r, dict) else {}


def list_flash(c: Jin10MCPClient, cursor: str | None = None) -> dict:
    args = {}
    if cursor:
        args["cursor"] = cursor
    r = c.call_tool("list_flash", args)
    return r.get("data", {}) if isinstance(r, dict) else {}


def search_flash(c: Jin10MCPClient, keyword: str, cursor: str | None = None) -> list[dict]:
    args: dict = {"keyword": keyword}
    if cursor:
        args["cursor"] = cursor
    r = c.call_tool("search_flash", args)
    if isinstance(r, dict):
        return r.get("data", {}).get("items", [])
    return []


def list_news(c: Jin10MCPClient, cursor: str | None = None) -> dict:
    args = {}
    if cursor:
        args["cursor"] = cursor
    r = c.call_tool("list_news", args)
    return r.get("data", {}) if isinstance(r, dict) else {}


def search_news(c: Jin10MCPClient, keyword: str, cursor: str | None = None) -> list[dict]:
    args: dict = {"keyword": keyword}
    if cursor:
        args["cursor"] = cursor
    r = c.call_tool("search_news", args)
    if isinstance(r, dict):
        return r.get("data", {}).get("items", [])
    return []


def get_news(c: Jin10MCPClient, news_id: int | str) -> dict:
    r = c.call_tool("get_news", {"id": news_id})
    return r.get("data", {}) if isinstance(r, dict) else {}


def list_calendar(c: Jin10MCPClient) -> list[dict]:
    r = c.call_tool("list_calendar", {})
    if isinstance(r, dict):
        data = r.get("data", [])
        return data if isinstance(data, list) else []
    return []


def read_quote_codes(c: Jin10MCPClient) -> list:
    r = c.read_resource("quote://codes")
    if isinstance(r, list):
        return r
    if isinstance(r, dict):
        return r.get("codes", [])
    return []


def parse_klines(klines: list[dict]) -> list[dict]:
    result = []
    for k in klines:
        try:
            result.append({
                "time":   k.get("time"),
                "open":   float(k.get("open", 0)),
                "close":  float(k.get("close", 0)),
                "high":   float(k.get("high", 0)),
                "low":    float(k.get("low", 0)),
                "volume": k.get("volume", 0),
            })
        except (TypeError, ValueError):
            result.append(k)
    return result


# ── CLI 快速测试 ─────────────────────────────────────────────

if __name__ == "__main__":
    with Jin10MCPClient() as client:
        print("=== 初始化 ===")
        info = client.initialize()
        client.initialized()
        print(f"服务端: {info.get('serverInfo', {})} | Session: {client._session_id}")

        print("\n=== 黄金实时行情 ===")
        q = get_quote(client, "XAUUSD")
        print(f"  {q.get('name')} {q.get('close')}  涨跌幅 {q.get('ups_percent')}%")

        print("\n=== 黄金K线（最近5根）===")
        kd = get_kline(client, "XAUUSD")
        klines = parse_klines(kd.get("klines", []))
        for k in klines[-5:]:
            import datetime
            t = datetime.datetime.fromtimestamp(k["time"]).strftime("%H:%M")
            print(f"  {t}  O={k['open']:.2f} H={k['high']:.2f} L={k['low']:.2f} C={k['close']:.2f}")

        print("\n=== 最新快讯（前3条）===")
        fd = list_flash(client)
        for item in (fd.get("items") or [])[:3]:
            print(f"  [{item.get('time','')[:16]}] {item.get('content','')[:80]}")

        print("\n=== 财经日历高星事件 ===")
        cal = list_calendar(client)
        high_star = [e for e in cal if int(e.get("star", 0)) >= 3]
        for e in high_star[:5]:
            actual = e.get("actual") or "待公布"
            print(f"  ⭐x{e['star']} {e.get('pub_time','')}  {e.get('title','')} "
                  f"预期={e.get('consensus','?')} 实际={actual}")

        print("\n✅ 全部成功！")
