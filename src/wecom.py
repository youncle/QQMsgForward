"""企业微信机器人转发模块 — 独立于QQ转发通道"""

import requests
import json
import logging
from typing import List, Dict, Optional

from filter import should_filter

logger = logging.getLogger(__name__)

from wecom_ui import WeComUIEngine

# 全局单例（惰性初始化）
_ui_engine: WeComUIEngine | None = None


def get_ui_engine() -> WeComUIEngine:
    global _ui_engine
    if _ui_engine is None:
        _ui_engine = WeComUIEngine()
        _ui_engine.start()
        logger.info("[WECOM_UI] 引擎已初始化")
    return _ui_engine


WECOM_API = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"

import hashlib
import base64
from io import BytesIO

# 图片下载缓存 {url: bytes}
_image_cache = {}

def _download_image(url: str, timeout: int = 5):
    """下载图片"""
    if url in _image_cache:
        return _image_cache[url]
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.content
        _image_cache[url] = data
        return data
    except Exception:
        _image_cache[url] = None
        return None

def _image_b64_md5(data: bytes):
    """图片转 base64 + md5"""
    b64 = base64.b64encode(data).decode("utf-8")
    md5 = hashlib.md5(data).hexdigest()
    return b64, md5

def _send_image(key: str, data: bytes) -> bool:
    """发送图片消息"""
    b64, md5 = _image_b64_md5(data)
    payload = {"msgtype": "image", "image": {"base64": b64, "md5": md5}}
    return send_to_bot(key, payload)

def _extract_key(key: str) -> str:
    """从输入中提取企微 webhook key，支持完整 URL 或裸 key"""
    key = key.strip()
    # 完整 URL: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
    if "key=" in key:
        from urllib.parse import parse_qs, urlparse
        try:
            parsed = urlparse(key)
            qs = parse_qs(parsed.query)
            if "key" in qs:
                return qs["key"][0].strip()
        except Exception:
            pass
        # fallback: 手动提取
        import re
        m = re.search(r'key=([^&\s]+)', key)
        if m:
            return m.group(1).strip()
    return key

def send_to_bot(key: str, payload: dict) -> bool:
    """发送消息到企微机器人"""
    msgtype = payload.get("msgtype", "未知")
    key_preview = key[:8] + "..." if len(key) > 8 else key
    try:
        resp = requests.post(
            f"{WECOM_API}?key={key}",
            json=payload,
            timeout=5,
        )
        try:
            result = resp.json()
            errcode = result.get("errcode", -1)
            errmsg = result.get("errmsg", "无")
            if errcode == 0:
                logger.info(f"[WECOM] 发送结果: status={resp.status_code} errcode={errcode} msgtype={msgtype} key={key_preview} → 成功")
                return True
            logger.warning(f"[WECOM] 发送结果: status={resp.status_code} errcode={errcode} errmsg={errmsg} msgtype={msgtype} key={key_preview} → 失败")
            return False
        except (ValueError, TypeError):
            logger.warning(f"[WECOM] 发送结果: status={resp.status_code} JSON解析失败 msgtype={msgtype} key={key_preview} → 原文: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"[WECOM] 发送异常: status=??? errcode=-1 msgtype={msgtype} key={key_preview} → {e}")
        return False

def try_forward(data: dict, cfg: dict) -> None:
    """企微转发入口 — 由 forward_qq.py webhook 调用"""
    if not cfg.get("wecom_enabled", True):
        return
    bots = cfg.get("wecom_bots", [])
    if not bots:
        return

    group_id = str(data.get("group_id", ""))
    if not group_id:
        return

    # 匹配 source_groups
    matched = []
    for bot in bots:
        sources = bot.get("source_groups", [])
        if not sources or group_id in sources:
            matched.append(bot)
    if not matched:
        return

    # 解析消息
    raw_text = data.get("raw_message", "")
    message_content = data.get("message", [])
    sender = data.get("sender", {})
    sender_name = (
        sender.get("nickname", "")
        or sender.get("card", "")
        or str(sender.get("user_id", ""))
    )
    sender_qq = sender.get("user_id", 0)
    group_name = data.get("group_name", "") or ""

    # 过滤检查（同QQ通道规则）
    filter_config = cfg.get("filter", {})
    if filter_config:
        blocked, reason = should_filter(message_content, filter_config)
        if blocked:
            logger.info(f"[WECOM] 过滤拦截: 群{group_id} - {reason}")
            return
        if reason:
            logger.info(f"[WECOM] 过滤仅记录: 群{group_id} - {reason}")

    # 解析消息段：分离文本、图片URL
    text_chunks = []
    image_urls = []

    if isinstance(message_content, list):
        for seg in message_content:
            if not isinstance(seg, dict):
                continue
            t = seg.get("type", "")
            d = seg.get("data", {}) or {}
            if t == "text":
                text_chunks.append(d.get("text", ""))
            elif t == "image":
                u = d.get("url", "")
                if u:
                    image_urls.append(u)

    display_text = "".join(text_chunks)

    # 按 mode 路由到不同发送通道
    mode = cfg.get("wecom_mode", "api")
    for bot in matched:
        if mode == "ui":
            _forward_ui(bot, display_text, image_urls, group_id)
        else:
            _forward_api(bot, display_text, image_urls, group_id)


def _forward_api(bot: dict, text: str, image_urls: list, group_id: str) -> None:
    """API 模式发送 — 通过企微 Webhook API"""
    key = _extract_key(bot.get("key", ""))
    if not key:
        return
    nm = bot.get("name", "") or key[:8]

    # 1. 发送文本
    if text:
        text_ok = send_to_bot(key, {"msgtype": "text", "text": {"content": text[:2000]}})
        if text_ok:
            logger.info(f"[WECOM] ✅ 文本转发: 群{group_id} → {nm}")
        else:
            logger.warning(f"[WECOM] ❌ 文本失败: 群{group_id} → {nm}")

    # 2. 发送图片（最多3张）
    for i, url in enumerate(image_urls[:3]):
        img_data = _download_image(url)
        if img_data:
            img_ok = _send_image(key, img_data)
            if img_ok:
                logger.info(f"[WECOM] ✅ 图片转发({i+1}): 群{group_id} → {nm}")
            else:
                logger.warning(f"[WECOM] ❌ 图片失败({i+1}): 群{group_id} → {nm}")
                send_to_bot(key, {"msgtype": "text", "text": {"content": "[图片]"}})
        else:
            logger.warning(f"[WECOM] ⚠️ 图片下载失败({i+1}): 群{group_id}")
            send_to_bot(key, {"msgtype": "text", "text": {"content": "[图片]"}})



def _forward_ui(bot: dict, text: str, image_urls: list, group_id: str) -> None:
    """UI 模式发送 — 入队后立即返回"""
    chat_name = bot.get("name", "")
    if not chat_name:
        logger.warning(f"[WECOM_UI] bot 缺少 name 字段，跳过")
        return

    engine = get_ui_engine()
    if not engine.is_available():
        logger.warning(f"[WECOM_UI] 企微窗口不可用，降级API: {chat_name}")
        _forward_api(bot, text, image_urls, group_id)
        return

    nm = bot.get("name", "") or _extract_key(bot.get("key", ""))[:8]
    logger.info(f"[WECOM_UI] 入队: 群{group_id} → {nm} ({chat_name})")

    # 预下载图片
    images = []
    for url in image_urls[:3]:
        data = _download_image(url)
        if data:
            images.append(data)

    engine.enqueue({
        "chat_name": chat_name,
        "text": text,
        "images": images,
    }, lambda: _forward_api(bot, text, image_urls, group_id))


def test_bot(key: str) -> tuple:
    """测试企微机器人连通性"""
    payload = {
        "msgtype": "text",
        "text": {"content": "✅ QQMsgForward 企微通道测试消息\n配置正确，服务正常。"},
    }
    ok = send_to_bot(_extract_key(key), payload)
    if ok:
        return True, "测试消息已发送，请在企微群中确认。"
    return False, "发送失败，请检查 Key 是否正确。"

