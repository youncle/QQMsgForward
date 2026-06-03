"""QQ消息转发 — 企业微信配置界面"""
import tkinter as tk
from tkinter import ttk, messagebox

from .base import load_config, save_config

def create_wecom_frame(parent, cfg=None):
    """企业微信机器人设置界面 Frame，可嵌入 Notebook"""
    if cfg is None:
        cfg = load_config()
    frame = ttk.Frame(parent, padding=(5, 10))
    pad = {"padx": 0, "pady": 5}

    enabled = cfg.get("wecom_enabled", True)

    frm_top = ttk.Frame(frame)
    frm_top.pack(fill="x", pady=(0, 5))
    enabled_cb = tk.Checkbutton(frm_top, text="启用微信转发")
    enabled_cb.pack(side="left", padx=(0, 15))

    if enabled:
        enabled_cb.select()
    else:
        enabled_cb.deselect()

    ui_mode = cfg.get("wecom_mode", "api") == "ui"
    ui_cb = tk.Checkbutton(frm_top, text="强制UI转发 (操控企业微信)")
    ui_cb.pack(side="left")
    if ui_mode:
        ui_cb.select()
    else:
        ui_cb.deselect()

    def _toggle_ui_state():
        is_en = bool(int(enabled_cb.getvar(enabled_cb["variable"])))
        ui_cb.config(state="normal" if is_en else "disabled")
        if not is_en:
            ui_cb.deselect()

    enabled_cb.configure(command=_toggle_ui_state)
    _toggle_ui_state()

    bots = cfg.get("wecom_bots", [])
    if not isinstance(bots, list):
        bots = []

    # ==== 输入区域 ====
    frm_input = ttk.LabelFrame(frame, text="添加/编辑机器人", padding=10)
    frm_input.pack(fill="x", **pad)

    ttk.Label(frm_input, text="Webhook Key").grid(row=0, column=0, sticky="w")
    key_entry = ttk.Entry(frm_input, width=60)
    key_entry.grid(row=0, column=1, sticky="ew", **pad)

    ttk.Label(frm_input, text="群名称").grid(row=1, column=0, sticky="w")
    name_entry = ttk.Entry(frm_input, width=60)
    name_entry.grid(row=1, column=1, sticky="ew", **pad)

    ttk.Label(frm_input, text="来源群过滤（逗号分隔，留空=全部转发）").grid(row=2, column=0, sticky="w")
    sources_entry = ttk.Entry(frm_input, width=60)
    sources_entry.grid(row=2, column=1, sticky="ew", **pad)

    frm_input.grid_columnconfigure(1, weight=1)

    # ==== 机器人列表 ====
    frm_list = ttk.LabelFrame(frame, text="已配置机器人", padding=10)
    frm_list.pack(fill="both", expand=True, **pad)

    bot_list = tk.Listbox(frm_list, height=8)
    bot_list.pack(fill="both", expand=True, **pad)

    def refresh_list():
        bot_list.delete(0, "end")
        for bot in bots:
            name = bot.get("name", "")
            key = bot.get("key", "")
            sources = bot.get("source_groups", [])
            src_str = ", ".join(sources) if sources else "全部"
            if name:
                label = name + " (" + src_str + ")"
            elif key:
                label = key[:16] + "... (" + src_str + ")"
            else:
                label = "未命名 (" + src_str + ")"
            bot_list.insert("end", label)

    def on_list_select(event):
        sel = bot_list.curselection()
        if sel:
            bot = bots[sel[0]]
            key_entry.delete(0, "end")
            key_entry.insert(0, bot.get("key", ""))
            name_entry.delete(0, "end")
            name_entry.insert(0, bot.get("name", ""))
            sources_entry.delete(0, "end")
            sources_entry.insert(0, ", ".join(bot.get("source_groups", [])))

    bot_list.bind("<<ListboxSelect>>", on_list_select)

    # ==== 按钮行 ====
    btn_frm = ttk.Frame(frame)
    btn_frm.pack(fill="x", **pad)

    def on_add():
        key = key_entry.get().strip()
        name = name_entry.get().strip()
        raw = sources_entry.get().replace("，", ",")
        srcs = [s.strip() for s in raw.split(",") if s.strip()]
        is_ui = bool(int(ui_cb.getvar(ui_cb["variable"])))
        if is_ui:
            if not name:
                messagebox.showwarning("提示", "UI 模式需要填写群名称")
                return
        else:
            if not key:
                messagebox.showwarning("提示", "API 模式需要填写 Webhook Key")
                return
        for i, bot in enumerate(bots):
            if bot.get("key", "") == key and key:
                bots[i] = {"key": key, "name": name, "source_groups": srcs}
                refresh_list()
                key_entry.delete(0, "end")
                name_entry.delete(0, "end")
                sources_entry.delete(0, "end")
                return
            if bot.get("name", "") == name and name:
                bots[i] = {"key": key, "name": name, "source_groups": srcs}
                refresh_list()
                key_entry.delete(0, "end")
                name_entry.delete(0, "end")
                sources_entry.delete(0, "end")
                return
        bots.append({"key": key, "name": name, "source_groups": srcs})
        refresh_list()
        key_entry.delete(0, "end")
        name_entry.delete(0, "end")
        sources_entry.delete(0, "end")

    def on_del():
        sel = bot_list.curselection()
        if sel:
            del bots[sel[0]]
            refresh_list()

    def on_test():
        sel = bot_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个机器人")
            return
        bot = bots[sel[0]]
        is_ui = bool(int(ui_cb.getvar(ui_cb["variable"])))

        if is_ui:
            chat_name = bot.get("name", "")
            if not chat_name:
                messagebox.showwarning("提示", "UI模式需要配置群名称")
                return
            from wecom import test_ui
            ok, msg = test_ui(chat_name)
        else:
            key = bot.get("key", "")
            if not key:
                messagebox.showwarning("提示", "该机器人没有 Key")
                return
            from wecom import test_bot
            ok, msg = test_bot(key)

        if ok:
            messagebox.showinfo("测试成功", msg)
        else:
            messagebox.showerror("测试失败", msg)

    ttk.Button(btn_frm, text="＋ 添加/更新", command=on_add).pack(side="left", padx=2)
    ttk.Button(btn_frm, text="－ 删除", command=on_del).pack(side="left", padx=2)
    ttk.Button(btn_frm, text="📨 测试发送", command=on_test).pack(side="left", padx=2)

    # ==== 保存 ====
    save_frm = ttk.Frame(frame)
    save_frm.pack(fill="x", **pad)

    status_var = tk.StringVar(value="")

    def on_save():
        cfg["wecom_enabled"] = bool(int(enabled_cb.getvar(enabled_cb["variable"])))
        cfg["wecom_mode"] = "ui" if bool(int(ui_cb.getvar(ui_cb["variable"]))) else "api"
        cfg["wecom_bots"] = bots
        try:
            save_config(cfg)
            status_var.set("配置已保存，立即生效。")
            messagebox.showinfo("保存成功", "配置已保存，立即生效。")
        except Exception as e:
            status_var.set("保存失败: " + str(e))
            messagebox.showerror("保存失败", str(e))

    ttk.Button(save_frm, text="💾 保存", command=on_save).pack(side="right", padx=5)
    ttk.Label(save_frm, textvariable=status_var, foreground="gray").pack(side="right", padx=10)

    refresh_list()
    return frame
