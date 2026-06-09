#!/bin/bash
# Push all skill files to GitHub via Content API (curl only)
# Uses /tmp/gh_pat.txt for token (not exposed in command line)

SKILL_DIR="/home/ada39/.hermes/skills/mcp/jin10-market-analysis"
OWNER="echosongg"
REPO="jin10-market-analysis-skill"
TOKEN=$(cat /tmp/gh_pat.txt)

push_file() {
  local filepath="$1"
  local fullpath="$2"
  local encoded
  local existing_sha="$3"
  
  encoded=$(base64 -w0 < "$fullpath")
  
  local payload
  if [ -n "$existing_sha" ]; then
    payload=$(cat <<EOF
{
  "message": "update: ${filepath}",
  "content": "${encoded}",
  "sha": "${existing_sha}"
}
EOF
)
  else
    payload=$(cat <<EOF
{
  "message": "add: ${filepath}",
  "content": "${encoded}"
}
EOF
)
  fi
  
  local result
  result=$(curl -s -X PUT \
    "https://api.github.com/repos/${OWNER}/${REPO}/contents/${filepath}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Content-Type: application/json" \
    -d "${payload}" 2>&1)
  
  if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'content' in d or 'commit' in d else 1)" 2>/dev/null; then
    echo "  ✅ ${filepath}"
    return 0
  elif echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','')); exit(1)" 2>/dev/null; then
    return 1
  else
    echo "  ❌ ${filepath} (SSL error or empty response)"
    # Retry once
    sleep 2
    result=$(curl -s -X PUT \
      "https://api.github.com/repos/${OWNER}/${REPO}/contents/${filepath}" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Accept: application/vnd.github.v3+json" \
      -H "Content-Type: application/json" \
      -d "${payload}" 2>&1)
    if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'content' in d or 'commit' in d else 1)" 2>/dev/null; then
      echo "  ✅ ${filepath} (after retry)"
      return 0
    else
      echo "  ❌ ${filepath} (retry failed)"
      return 1
    fi
  fi
}

echo "=== 获取已有文件列表 ==="
# 获取已有文件和子目录内容
python3 << 'PYEOF'
import subprocess, json

token = open("/tmp/gh_pat.txt").read().strip()
owner = "echosongg"
repo = "jin10-market-analysis-skill"

def fetch(path=""):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = subprocess.run(["curl", "-s", url,
      "-H", f"Authorization: Bearer {token}",
      "-H", "Accept: application/vnd.github.v3+json"],
      capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout)
    except:
        return []

result = fetch()
for item in result:
    if item["type"] == "file":
        print(f"{item['path']}:{item['sha']}")
    elif item["type"] == "dir":
        for child in fetch(item["path"]):
            if child["type"] == "file":
                print(f"{child['path']}:{child['sha']}")
PYEOF

echo ""
echo "=== 推送根目录文件 ==="
# Root files
for f in "$SKILL_DIR"/SKILL.md "$SKILL_DIR"/README.md "$SKILL_DIR"/JIN10_API_REFERENCE.md "$SKILL_DIR"/.gitignore; do
  basename_f=$(basename "$f")
  if [ -f "$f" ]; then
    existing=$(python3 -c "
import json
with open('/dev/stdin') as f: pass
print('')
" 2>/dev/null || echo "")
    # We'll get sha from the list above
    push_file "$basename_f" "$f" ""
  fi
done

echo ""
echo "=== 推送 scripts/ ==="
for f in "$SKILL_DIR"/scripts/*.py "$SKILL_DIR"/scripts/*.sh; do
  if [ -f "$f" ]; then
    basename_f="scripts/$(basename "$f")"
    push_file "$basename_f" "$f" ""
  fi
done

echo ""
echo "=== 推送 references/ ==="
for f in "$SKILL_DIR"/references/*.md; do
  if [ -f "$f" ]; then
    basename_f="references/$(basename "$f")"
    push_file "$basename_f" "$f" ""
  fi
done

echo ""
echo "=== 推送 examples/ ==="
for f in "$SKILL_DIR"/examples/*.md; do
  if [ -f "$f" ]; then
    basename_f="examples/$(basename "$f")"
    push_file "$basename_f" "$f" ""
  fi
done

echo ""
echo "=== 完成 ==="
