from flask import Flask, request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import time
import logging
import json
import os
from typing import Dict, List

from filter import should_filter

# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
_config = None


def load_config():
    """从文件加载配置（强制重新加载）"""
    global _config
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        _config = json.load(f)
    return _config


def get_config():
    """获取配置（延迟加载，首次访问时从文件读取）"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config_path(path: str) -> None:
    """设置配置文件路径（由 tray.py 在启动时调用）"""
    global CONFIG_PATH, _config
    CONFIG_PATH = path
    _config = None  # 重置缓存，强制重新加载

# 确保 stderr 输出 UTF-8，与日志文件编码一致（windowed 模式下 stderr 为 None）
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

# 初始化日志
if sys.stderr:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
logger = logging.getLogger(__name__)

# 初始化Requests会话（带连接池+自动重试）
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 配置请求头（带Token）— 每次请求前获取
def _get_headers():
    cfg = get_config()
    h = {'Content-Type': 'application/json'}
    token = cfg.get('llbot_token', '')
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h

# 缓存：去重+限流
msg_cache: Dict[str, float] = {}
last_send_time: Dict[str, float] = {}

app = Flask(__name__)


def is_duplicate(msg_id: str) -> bool:
    """检查消息是否重复，同时清理过期缓存"""
    cfg = get_config()
    window = cfg['forward']['duplicate_window']
    now = time.time()
    expired = [k for k, v in msg_cache.items() if now - v > window * 10]
    for k in expired:
        del msg_cache[k]
    if msg_id in msg_cache:
        if now - msg_cache[msg_id] < window:
            return True
    msg_cache[msg_id] = now
    return False


def rate_limit(target_group: str) -> None:
    """限流：保证单群发送间隔不小于配置值"""
    cfg = get_config()
    interval = cfg['forward']['send_interval']
    now = time.time()
    if target_group in last_send_time:
        wait = interval - (now - last_send_time[target_group])
        if wait > 0:
            time.sleep(wait)
    last_send_time[target_group] = time.time()


@app.post("/webhook")
def webhook():
    try:
        cfg = get_config()
        robot_qq = cfg['robot_qq']
        forward_rules = cfg['forward_rules']
        llbot_api = cfg['llbot_api']
        filter_config = cfg.get('filter', {})

        data = request.json
        if not data:
            logger.warning("收到空的WebHook请求")
            return "ok"

        # 1. 过滤非群聊消息
        post_type = data.get("post_type")
        message_type = data.get("message_type")
        if post_type != "message" or message_type != "group":
            return "ok"

        # 2. 解析消息信息
        group_id = str(data.get("group_id", ""))
        sender = data.get("sender", {})
        sender_qq = sender.get("user_id", 0)
        msg_id = str(data.get("message_id", ""))
        raw_text = data.get("raw_message", "")
        message_content = data.get("message", [])

        if not group_id or not msg_id:
            return "ok"

        # 3. 跳过自己发的消息（防止循环转发）
        if sender_qq == robot_qq:
            logger.debug(f"跳过自身消息: {raw_text[:30]}")
            return "ok"

        # 4. 不在转发规则的群，跳过
        if group_id not in forward_rules:
            return "ok"

        # 5. 去重
        if is_duplicate(msg_id):
            logger.info(f"重复消息，跳过: {raw_text[:30]}")
            return "ok"

        # 6. 消息过滤（QR码 + 联系方式）
        if filter_config:
            blocked, reason = should_filter(message_content, filter_config)
            if blocked:
                logger.info(f"[FILTER] 已拦截: 群{group_id} - {reason}")
                return "ok"
            elif reason:
                # log_only 模式：仅记录，不拦截
                logger.info(f"[FILTER] 仅记录: 群{group_id} - {reason}")
            else:
                logger.debug(f"[FILTER] 放行: 群{group_id} | 类型={type(message_content).__name__} "
                            f"| 文本={raw_text[:50]}")

        # 7. 执行转发
        rule = forward_rules[group_id]
        target_groups = rule['targets'] if isinstance(rule, dict) else rule
        for to_group in target_groups:
            try:
                rate_limit(to_group)
                resp = session.post(
                    f"{llbot_api}/send_group_msg",
                    json={
                        "group_id": int(to_group),
                        "message": message_content
                    },
                    headers=_get_headers(),
                    timeout=5
                )
                resp.raise_for_status()
                result = resp.json()
                if result.get("status") == "ok":
                    logger.info(f"✅ 转发成功: {group_id} → {to_group} | {raw_text[:50]}...")
                else:
                    err_msg = result.get("msg", result.get("wording", "未知错误"))
                    logger.error(f"❌ API处理失败: {group_id} → {to_group} | 错误: {err_msg}")

            except requests.exceptions.ConnectionError:
                logger.error(f"❌ 连接失败！请检查LLOneBot的HTTP服务是否开启，端口3000是否正常")
            except requests.exceptions.Timeout:
                logger.error(f"❌ 转发超时: {group_id} → {to_group}")
            except Exception as e:
                logger.error(f"❌ 转发异常: {group_id} → {to_group} | 错误: {str(e)}")

        return "ok"

    except Exception as e:
        logger.error(f"处理WebHook请求异常: {str(e)}", exc_info=True)
        return "ok"


if __name__ == '__main__':
    cfg = get_config()
    logger.info("=" * 50)
    logger.info("✅ QQ群转发服务已启动")
    logger.info(f"📋 WebHook地址: http://127.0.0.1:8080/webhook")
    logger.info(f"📋 转发规则: {cfg['forward_rules']}")
    filter_cfg = cfg.get('filter', {})
    logger.info(f"📋 过滤状态: QR码={'启用' if filter_cfg.get('qrcode',{}).get('enabled') else '关闭'} | 联系方式={'启用' if filter_cfg.get('contact',{}).get('enabled') else '关闭'} | 模式={'仅日志' if filter_cfg.get('log_only') else '拦截'}")
    logger.info("=" * 50)
    app.run(host="127.0.0.1", port=8080, debug=False, threaded=True)
