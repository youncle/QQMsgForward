"""NT 工具函数：通过 WebUI ntcall API 获取文件下载链接"""

import pathlib as _pl
import hashlib

_BASE = _pl.Path(__file__).resolve().parent.parent

def get_file_bytes_via_ntcall(filename: str, file_id: str = "", group_id: str = "") -> bytes | None:
    """通过 ntcall 下载文件，返回 bytes"""
    candidates = [file_id] if file_id else []
    # 从数据库补充 fileUuid
    try:
        import sqlite3
        for inst in ["LLBot-CLI-Win-x64", "LLBot-CLI-Win-x64-2"]:
            db_dir = _BASE / "runtime" / inst / "bin" / "llbot" / "data" / "database"
            if not db_dir.exists():
                continue
            for db_file in sorted(db_dir.glob("*.v2.db")):
                try:
                    conn = sqlite3.connect(str(db_file))
                    row = conn.execute(
                        "SELECT fileUuid FROM file WHERE fileUuid=? OR fileName=? LIMIT 1",
                        (file_id or "", filename)
                    ).fetchone()
                    conn.close()
                    if row and row[0]:
                        candidates.append(row[0])
                except Exception:
                    continue
    except Exception:
        pass
    candidates = list(dict.fromkeys(c for c in candidates if c))
    group_num = int(group_id) if group_id.isdigit() else 0
    import requests as _req
    for inst, port in [("LLBot-CLI-Win-x64", 3080), ("LLBot-CLI-Win-x64-2", 3081)]:
        token_path = _BASE / "runtime" / inst / "bin" / "llbot" / "data" / "webui_token.txt"
        if not token_path.exists():
            continue
        token_hash = hashlib.sha256(
            token_path.read_text("utf-8").strip().encode()
        ).hexdigest()
        for uuid in candidates:
            try:
                r = _req.post(
                    f"http://127.0.0.1:{port}/api/ntcall/pmhq/getGroupFileUrl",
                    headers={"X-Webui-Token": token_hash, "Content-Type": "application/json"},
                    json={"args": [group_num, uuid]}, timeout=10
                )
                result = r.json()
                url = result.get("data", {}).get("url", "")
                if url and url.startswith("http"):
                    img = _req.get(url, timeout=15,
                                   headers={"User-Agent": "Mozilla/5.0"})
                    img.raise_for_status()
                    return img.content
            except Exception:
                continue
    return None

def get_file_base64_via_ntcall(filename: str, file_id: str = "", group_id: str = "") -> str | None:
    """通过 ntcall 下载文件，返回 base64 编码"""
    import base64 as _b64
    data = get_file_bytes_via_ntcall(filename, file_id, group_id)
    if data:
        return _b64.b64encode(data).decode("ascii")
    return None
