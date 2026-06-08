import sys, os
path = r"D:\DevGitee\agent-space\QQMsgForward\scripts\verify.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "def log(status: str, msg: str):\n    print(f\"  {status}  {msg}\")"
new = '''def log(status: str, msg: str):
    """打印日志，自动处理 GBK 编码环境"""
    try:
        print(f"  {status}  {msg}")
    except UnicodeEncodeError:
        m = {"✅": "PASS", "⚠️": "WARN", "❌": "FAIL", "ℹ️": "INFO"}
        fallback = m.get(status, "??")
        print(f"  [{fallback}]  {msg}")'''

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK")
else:
    print("NOT FOUND")
