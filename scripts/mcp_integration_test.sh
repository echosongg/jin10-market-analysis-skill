#!/bin/bash
# MCP Integration Test for Jin10 Financial Data
# Full protocol flow: initialize -> tools/list -> resources/list -> tools/call
# Usage: JIN10_TOKEN="sk-..." bash scripts/mcp_integration_test.sh

set -e
TOKEN="${JIN10_TOKEN:?JIN10_TOKEN not set}"
URL='https://mcp.jin10.com/mcp'

echo "=== Step 1: initialize ==="
RESP=$(curl -s -D /tmp/jin10_sess.txt \
  -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"hermes-test","version":"1.0"}}}' \
  --max-time 15)

SESSION=$(grep -i 'mcp-session-id:' /tmp/jin10_sess.txt | head -1 | sed 's/.*: //' | tr -d '\r\n')
echo "Session: $SESSION"
echo "$RESP" | grep '^data: ' | sed 's/^data: //' > /tmp/jin10_init.json
python3 -c "import json; d=json.load(open('/tmp/jin10_init.json')); r=d.get('result',{}); print(f'  Server: {r.get(\"serverInfo\",{}).get(\"name\")} v{r.get(\"serverInfo\",{}).get(\"version\")}'); print(f'  Protocol: {r.get(\"protocolVersion\")}')"

echo -e "\n=== Step 2: notifications/initialized ==="
curl -s \
  -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
  --max-time 10 > /dev/null
echo "  OK"

echo -e "\n=== Step 3: tools/list ==="
RESP=$(curl -s \
  -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  --max-time 15)
echo "$RESP" | grep '^data: ' | sed 's/^data: //' > /tmp/jin10_tools.json
python3 -c "
import json
d = json.load(open('/tmp/jin10_tools.json'))
for t in d.get('result',{}).get('tools',[]):
    props = list(t.get('inputSchema',{}).get('properties',{}).keys())
    desc = t.get('description','')[:100]
    print(f'  {t[\"name\"]}({', '.join(props)})')
    if desc: print(f'    -> {desc}')
"

echo -e "\n=== Step 4: resources/list ==="
RESP=$(curl -s \
  -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":3,"method":"resources/list","params":{}}' \
  --max-time 15)
echo "$RESP" | grep '^data: ' | sed 's/^data: //' > /tmp/jin10_resources.json
python3 -c "
import json
d = json.load(open('/tmp/jin10_resources.json'))
for r in d.get('result',{}).get('resources',[]): print(f'  {r[\"uri\"]}')
for r in d.get('result',{}).get('resourceTemplates',[]): print(f'  [template] {r[\"uriTemplate\"]}')
"

echo -e "\n=== Step 5: get_quote(XAUUSD) ==="
RESP=$(curl -s \
  -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_quote","arguments":{"code":"XAUUSD"}}}' \
  --max-time 15)
echo "$RESP" | grep '^data: ' | sed 's/^data: //' > /tmp/jin10_quote.json
python3 -c "
import json
d = json.load(open('/tmp/jin10_quote.json'))
for item in d.get('result',{}).get('content',[]):
    parsed = json.loads(item.get('text','{}'))
    for k,v in parsed.get('data',{}).items():
        print(f'  {k}: {v}')
"

echo -e "\n=== Step 6: list_flash (top 3) ==="
RESP=$(curl -s \
  -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"list_flash","arguments":{}}}' \
  --max-time 15)
echo "$RESP" | grep '^data: ' | sed 's/^data: //' > /tmp/jin10_flash.json
python3 -c "
import json
d = json.load(open('/tmp/jin10_flash.json'))
for item in d.get('result',{}).get('content',[]):
    parsed = json.loads(item.get('text','{}'))
    items = parsed.get('data',{}).get('items',[])[:3]
    for i,it in enumerate(items):
        print(f'  {i+1}. {it.get(\"title\", it.get(\"content\", \"\"))[:100]}')
    print(f'  has_more={parsed.get(\"data\",{}).get(\"has_more\")} next_cursor={parsed.get(\"data\",{}).get(\"next_cursor\")}')
"

echo -e "\n=== Step 7: list_calendar (top 5) ==="
RESP=$(curl -s \
  -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"list_calendar","arguments":{}}}' \
  --max-time 15)
echo "$RESP" | grep '^data: ' | sed 's/^data: //' > /tmp/jin10_cal.json
python3 -c "
import json
d = json.load(open('/tmp/jin10_cal.json'))
for item in d.get('result',{}).get('content',[]):
    parsed = json.loads(item.get('text','{}'))
    items = parsed.get('data',[])[:5]
    print(f'  Total: {len(parsed.get(\"data\",[]))} items')
    for it in items:
        star = '★' * it.get('star',0) + '☆' * (3-it.get('star',0))
        print(f'  [{star}] {it.get(\"title\",\"\")[:50]} | 前值:{it.get(\"previous\",\"-\")} 预期:{it.get(\"consensus\",\"-\")} 实际:{it.get(\"actual\",\"-\")}')
"

echo -e "\n=== ALL DONE ==="
