#!/usr/bin/env python3
"""
QQMsgForward 开发 Harness 验证脚本（Evaluation 层）

用法：python scripts/verify.py

检查项：
1. 模块导入检查 — 所有 src/ 模块能否正常 import
2. 配置一致性检查 — forward_qq.py 和 settings.py 的 load_config / CONFIG_PATH 签名对齐
3. filter 模块逻辑检查 — should_filter 基本调用无异常
4. 目录完整性检查 — 必要目录和文件是否存在
5. 构建链检查 — build.bat 引用的路径是否存在
6. 安全规则检查 — safety.md 中声明的红线路径是否合理

返回码：0=全部通过，1=有警告，2=有错误
"""

import importlib
import os
import sys
import ast
import re

# ── 路径设置 ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.insert(0, SRC_DIR)

# ── 状态符号 ──
PASS = "✅"
WARN = "⚠️"
FAIL = "❌"
INFO = "ℹ️"


def log(status: str, msg: str):
    """打印日志，自动处理 GBK 编码环境"""
    try:
        print(f"  {status}  {msg}")
    except UnicodeEncodeError:
        m = {"✅": "PASS", "⚠️": "WARN", "❌": "FAIL", "ℹ️": "INFO"}
        fallback = m.get(status, "??")
        print(f"  [{fallback}]  {msg}")


# ── 检查 1：模块导入检查 ──
def check_imports() -> list[str]:
    """逐个 import src/ 下的模块，捕获导入异常"""
    errors = []
    modules = [
        "filter", "forward_qq", "nt_utils", "qr_decoder",
        "splash", "tray", "wecom", "wecom_ui",
    ]
    skip_if_missing_dep = {
        "qr_decoder": ["PIL", "pyzbar"],
        "wecom_ui": ["win32com"],
    }

    for mod_name in modules:
        skip_deps = skip_if_missing_dep.get(mod_name, [])
        deps_missing = []
        for dep in skip_deps:
            try:
                importlib.import_module(dep)
            except ImportError:
                deps_missing.append(dep)

        if deps_missing:
            log(WARN, f"{mod_name}: 跳过（缺少依赖: {', '.join(deps_missing)}）")
            continue

        try:
            importlib.import_module(mod_name)
            log(PASS, f"{mod_name}: 导入成功")
        except Exception as e:
            msg = f"{mod_name}: 导入失败 — {e}"
            log(FAIL, msg)
            errors.append(msg)

    return errors


# ── 检查 2：配置一致性检查 ──
def check_config_consistency() -> list[str]:
    """检查两处配置接口是否对齐：
    - forward_qq.py: 需要 CONFIG_PATH + load_config()（只读）
    - settings.py: 需要 CONFIG_PATH + load_config() + save_config()（读写）
    """
    errors = []
    fwd_path = os.path.join(SRC_DIR, "forward_qq.py")
    set_path = os.path.join(SRC_DIR, "settings.py")

    # forward_qq.py — 只读配置
    if os.path.exists(fwd_path):
        with open(fwd_path, "r", encoding="utf-8") as f:
            content = f.read()
        ok = True
        if "CONFIG_PATH" not in content:
            errors.append("forward_qq.py: 缺少 CONFIG_PATH")
            ok = False
        if "def load_config(" not in content:
            errors.append("forward_qq.py: 缺少 load_config()")
            ok = False
        log(PASS if ok else FAIL, f"forward_qq.py: 配置接口{'完整' if ok else '不完整'}")

    # settings.py — 读写配置
    if os.path.exists(set_path):
        with open(set_path, "r", encoding="utf-8") as f:
            content = f.read()
        ok = True
        if "CONFIG_PATH" not in content:
            errors.append("settings.py: 缺少 CONFIG_PATH")
            ok = False
        if "def load_config(" not in content:
            errors.append("settings.py: 缺少 load_config()")
            ok = False
        if "def save_config(" not in content:
            errors.append("settings.py: 缺少 save_config()")
            ok = False
        log(PASS if ok else FAIL, f"settings.py: 配置接口{'完整' if ok else '不完整'}")

    return errors


# ── 检查 3：filter 模块逻辑检查 ──
def check_filter_logic() -> list[str]:
    """基本检查 filter 模块的关键函数和常量"""
    errors = []
    try:
        import filter
        required_funcs = ["should_filter", "check_qrcode_ad", "check_contact_info"]
        for func_name in required_funcs:
            if hasattr(filter, func_name):
                log(PASS, f"filter.{func_name}(): 存在")
            else:
                errors.append(f"filter.py: 缺少 {func_name}()")

        for const_name in ["QQ_CONTEXT_WHITELIST", "IMAGE_FILE_EXTENSIONS"]:
            if hasattr(filter, const_name):
                log(PASS, f"filter.{const_name}: 存在")
            else:
                errors.append(f"filter.py: 缺少 {const_name}")
    except Exception as e:
        errors.append(f"filter 模块检查失败: {e}")

    return errors


# ── 检查 4：目录完整性检查 ──
def check_directory_integrity():
    """检查必要目录和文件是否存在"""
    errors = []
    warnings = []

    required = [
        ("config 目录", os.path.join(PROJECT_ROOT, "config")),
        ("docs 目录", os.path.join(PROJECT_ROOT, "docs")),
        ("scripts 目录", os.path.join(PROJECT_ROOT, "scripts")),
        ("src 目录", SRC_DIR),
        ("src/__init__.py", os.path.join(SRC_DIR, "__init__.py")),
        ("main.py", os.path.join(PROJECT_ROOT, "main.py")),
        ("requirements.txt", os.path.join(PROJECT_ROOT, "requirements.txt")),
    ]

    for name, path in required:
        if os.path.exists(path):
            log(PASS, f"{name}: 存在")
        else:
            errors.append(f"缺少: {name}")
            log(FAIL, f"{name}: 缺失")

    docs = ["architecture.md", "build.md", "config_reference.md", "troubleshooting.md", "changelog.md"]
    for doc in docs:
        doc_path = os.path.join(PROJECT_ROOT, "docs", doc)
        if os.path.exists(doc_path):
            log(INFO, f"docs/{doc}: 存在")
        else:
            warnings.append(f"docs/{doc}: 缺失（可选）")
            log(WARN, f"docs/{doc}: 缺失（可选）")

    return errors, warnings


# ── 检查 5：构建链检查 ──
def check_build_chain() -> list[str]:
    """检查构建脚本和资源"""
    errors = []
    build_bat = os.path.join(PROJECT_ROOT, "scripts", "build.bat")
    if not os.path.exists(build_bat):
        errors.append("scripts/build.bat: 缺失")
        log(FAIL, "scripts/build.bat: 缺失")
        return errors

    log(PASS, "scripts/build.bat: 存在")
    ico_path = os.path.join(PROJECT_ROOT, "resources", "app.ico")
    if os.path.exists(ico_path):
        log(PASS, "resources/app.ico: 存在")
    else:
        log(WARN, "resources/app.ico: 缺失（构建时会自动生成）")

    return errors


# ── 检查 6：安全规则完整性检查 ──
def check_safety_rules() -> list[str]:
    """检查 safety 规则文件是否完备"""
    errors = []
    safety_path = os.path.join(PROJECT_ROOT, ".rules", "safety.md")
    if not os.path.exists(safety_path):
        errors.append(".rules/safety.md: 缺失")
        log(FAIL, ".rules/safety.md: 缺失")
        return errors

    log(PASS, ".rules/safety.md: 存在")
    rt_path = os.path.join(PROJECT_ROOT, "runtime")
    if os.path.exists(rt_path):
        log(INFO, "runtime/: 存在（已受 safety.md 保护）")
    else:
        log(INFO, "runtime/: 不存在（可能已被清理）")

    return errors



# ── 检查 7：Filter 验收检查（JSON 物理锁）──
def check_filter_acceptance() -> list[str]:
    """读取 filter 验收 JSON，逐条运行测试用例验证"""
    errors = []
    acceptance_path = os.path.join(PROJECT_ROOT, ".rules", "verify", "filter-acceptance.json")
    if not os.path.exists(acceptance_path):
        log(INFO, ".rules/verify/filter-acceptance.json: 不存在，跳过")
        return errors

    import filter
    import json
    with open(acceptance_path, "r", encoding="utf-8") as f:
        suite = json.load(f)

    for tc in suite.get("test_cases", []):
        tc_id = tc["id"]
        msg = tc["input"]["message"]
        cfg = tc["input"]["config"]
        expected = tc["expected"]
        try:
            result, _ = filter.should_filter(msg, cfg)
            if result == expected:
                log(PASS, f"{tc_id}: {tc["description"]}")
            else:
                log(FAIL, f"{tc_id}: 失败—期望={expected}, 实际={result}")
                errors.append(f"{tc_id}: 期望={expected}, 实际={result}")
        except Exception as e:
            log(FAIL, f"{tc_id}: 异常—{e}")
            errors.append(f"{tc_id}: {e}")
    return errors


# ── 检查 8：Safety 红线违规检查（沙盒隔离）──
def check_safety_violations() -> list[str]:
    """检查当前 git diff 是否触碰 safety.md 中的 Level 1 红线"""
    errors = []
    import subprocess

    # 暂存区变更
    r1 = subprocess.run(["git", "diff", "--name-only", "--cached"], capture_output=True, text=True, cwd=PROJECT_ROOT)
    # 未暂存变更
    r2 = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, cwd=PROJECT_ROOT)
    r3 = subprocess.run(["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT)

    all_changed = set(r1.stdout.splitlines() + r2.stdout.splitlines())

    forbidden_paths = ["config/config.json", "main.py"]
    found = False
    for f in sorted(all_changed):
        if not f.strip():
            continue
        for forbidden in forbidden_paths:
            if f.startswith(forbidden):
                msg = f"Safety 违规: {f} — 触碰 Level 1 红线（禁止修改）"
                errors.append(msg)
                log(FAIL, msg)
                found = True

    if not found:
        log(PASS, "无 Safety 红线违规")
    return errors


# ── 检查 9：记忆健康检查 ──
def check_memory_health() -> list[str]:
    """检查 CLAUDE.md 是否超限"""
    errors = []
    claude_path = os.path.join(PROJECT_ROOT, "CLAUDE.md")
    if not os.path.exists(claude_path):
        log(INFO, "CLAUDE.md: 不存在，跳过")
        return errors

    with open(claude_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    line_count = len(lines)
    if line_count > 200:
        log(WARN, f"CLAUDE.md: {line_count} 行（超过 200 行，运行 scripts/compress-memory.py）")
    else:
        log(PASS, f"CLAUDE.md: {line_count} 行（正常）")
    return errors


# ── 检查 10：进度追踪检查 ──
def check_progress() -> list[str]:
    """检查 progress.json 是否存在且格式正确"""
    errors = []
    progress_path = os.path.join(PROJECT_ROOT, ".rules", "verify", "progress.json")
    if not os.path.exists(progress_path):
        log(WARN, ".rules/verify/progress.json: 不存在")
        return errors

    import json
    with open(progress_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ms = data.get("milestones", [])
    total = len(ms)
    done = sum(1 for m in ms if m.get("status") == "completed")
    log(INFO, f"进度: {done}/{total} milestones 已完成")
    return errors


# ── 检查 11：qr_decoder 验收检查 ──
def check_qr_decoder_acceptance() -> list[str]:
    """检查 qr_decoder 验收 JSON 中的模块健康状况"""
    errors = []
    accept_path = os.path.join(PROJECT_ROOT, ".rules", "verify", "qr-decoder-acceptance.json")
    if not os.path.exists(accept_path):
        log(INFO, ".rules/verify/qr-decoder-acceptance.json: 不存在，跳过")
        return errors

    import json
    with open(accept_path, "r", encoding="utf-8") as f:
        suite = json.load(f)

    for tc in suite.get("test_cases", []):
        log(INFO, f"{tc["id"]}: {tc["description"]}")

    try:
        import qr_decoder
        has_pyzbar = getattr(qr_decoder, "PYZBAR_AVAILABLE", False)
        log(PASS if has_pyzbar else WARN, f"PYZBAR_AVAILABLE = {has_pyzbar}")
        if not has_pyzbar:
            errors.append("qr_decoder: pyzbar 不可用，解码功能受限")
    except Exception as e:
        errors.append(f"qr_decoder: 导入失败 — {e}")
        log(FAIL, f"qr_decoder: 导入失败")

    return errors


# ── 检查 12：文档同步检查 ──
def check_doc_sync() -> list[str]:
    """检查项目文档之间的引用一致性和内容同步状态"""
    errors = []
    warnings = []

    # 1. AGENTS.md 引用的文件是否存在
    agents_path = os.path.join(PROJECT_ROOT, "AGENTS.md")
    if os.path.exists(agents_path):
        with open(agents_path, "r", encoding="utf-8") as f:
            agents_content = f.read()

        refs = set(re.findall(r"[`]?([a-zA-Z0-9_./-]+\\.(?:md|py|json|bat|vbs))[`]?", agents_content))
        for ref in sorted(refs):
            if ref.startswith("docs/") or ref.startswith(".rules/") or ref.startswith("scripts/"):
                ref_path = os.path.join(PROJECT_ROOT, ref)
                if not os.path.exists(ref_path):
                    msg = f"AGENTS.md 引用了不存在的文件: {ref}"
                    warnings.append(msg)
                    log(WARN, msg)
                else:
                    log(PASS, f"AGENTS.md → {ref}")

    # 2. src 模块在 architecture.md 中是否都有记录
    arch_path = os.path.join(PROJECT_ROOT, "docs", "architecture.md")
    src_modules = [f.replace(".py", "") for f in os.listdir(SRC_DIR) if f.endswith(".py") and f != "__init__.py"]

    if os.path.exists(arch_path):
        with open(arch_path, "r", encoding="utf-8") as f:
            arch_content = f.read()
        for mod in sorted(src_modules):
            if mod in arch_content:
                log(PASS, f"docs/architecture.md → src/{mod}.py")
            else:
                msg = f"src/{mod}.py 在 docs/architecture.md 中未提及"
                warnings.append(msg)
                log(WARN, msg)

    # 3. config_reference.md 字段 vs config.json 实际字段
    config_ref_path = os.path.join(PROJECT_ROOT, "docs", "config_reference.md")
    config_json_path = os.path.join(PROJECT_ROOT, "config", "config.json")

    if os.path.exists(config_ref_path) and os.path.exists(config_json_path):
        import json
        with open(config_json_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        with open(config_ref_path, "r", encoding="utf-8") as f:
            ref_content = f.read()

        for key in sorted(cfg.keys()):
            if key == "llbot_apis":
                continue  # 动态写入，不需要文档
            pattern = rf"[`]{{0,1}}{key}[`]{{0,1}}"
            if re.search(pattern, ref_content):
                log(PASS, f"config_reference.md → config.json.{key}")
            else:
                msg = f"config.json.{key} 在 docs/config_reference.md 中未记录"
                warnings.append(msg)
                log(WARN, msg)

    if warnings:
        for w in warnings:
            errors.append(w)

    return errors

# ── 主流程 ──
def main():
    print("=" * 56)
    print("  QQMsgForward Harness Verification")
    print("=" * 56)

    all_errors = []
    all_warnings = []

    sections = [
        ("模块导入检查", lambda: check_imports()),
        ("配置一致性检查", lambda: check_config_consistency()),
        ("Filter 逻辑检查", lambda: check_filter_logic()),
        ("Filter 验收检查", lambda: check_filter_acceptance()),
        ("目录完整性检查", lambda: check_directory_integrity()),
        ("构建链检查", lambda: check_build_chain()),
        ("安全规则检查", lambda: check_safety_rules()),
        ("Safety 红线违规检查", lambda: check_safety_violations()),
        ("记忆健康检查", lambda: check_memory_health()),
        ("进度追踪检查", lambda: check_progress()),
        ("qr_decoder 验收检查", lambda: check_qr_decoder_acceptance()),
        ("文档同步检查", lambda: check_doc_sync()),
    ]

    for section_name, check_fn in sections:
        print(f"\n── {section_name} ──")
        try:
            result = check_fn()
            if isinstance(result, tuple):
                errs, warns = result
                all_errors.extend(errs)
                all_warnings.extend(warns)
            else:
                all_errors.extend(result)
        except Exception as e:
            log(FAIL, f"检查异常: {e}")
            all_errors.append(f"{section_name}: {e}")

    print()
    print("=" * 56)

    if all_errors:
        print(f"\n{FAIL} 失败: {len(all_errors)} 个错误")
        for e in all_errors:
            print(f"     {e}")
        print(f"\n  → 请修复错误后重新运行")
        return 2
    elif all_warnings:
        print(f"\n{WARN} 通过（{len(all_warnings)} 个警告）")
        for w in all_warnings:
            print(f"     {w}")
        return 1
    else:
        print(f"\n{PASS} 全部通过")
        return 0


if __name__ == "__main__":
    sys.exit(main())
