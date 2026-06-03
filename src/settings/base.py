"""QQ消息转发 — 设置界面共享工具"""
import json
import os

from wizard import get_base_dir

SCRIPT_DIR = get_base_dir()
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "config.json")


def set_config_path(path: str) -> None:
    """设置配置文件路径（由 tray.py 在启动时调用）"""
    global CONFIG_PATH
    CONFIG_PATH = path


MODE_DESCRIPTIONS = {
    u"仅关键词图片": u"仅拦截同时包含图片和关键词的消息",
    u"拦截纯图片": u"额外拦截无文字说明的纯图片消息",
    u"拦截所有图片": u"拦截所有含图片的消息",
}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)
