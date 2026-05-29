## 1. RED 阶段 — 编写测试

- [ ] 1.1 编写 QQ 正则收紧测试
  - 文件：`tests/test_filter.py`
  - 新增 `test_contact_qq_8_digit_minimum` — "加我QQ 1234567"（7位）不触发拦截
  - 新增 `test_contact_qq_8_digit_matches` — "加我QQ 12345678"（8位）触发拦截
  - 新增 `test_contact_qq_10_digit_matches` — 10位数字触发拦截
  - 新增 `test_contact_qq_11_digit_no_match` — 11位数字不触发（超上限）
  - **验收**：`python -m pytest tests/test_filter.py -v` → 新测试 RED（失败，当前正则仍匹配5位起）

## 2. GREEN+REFACTOR 阶段 — 修改正则与阈值

- [ ] 2.1 修改 filter.py 群号豁免阈值
  - 文件：`filter.py`
  - `>= 6` → `>= 8`
  - **验收**：1.1 测试全部 GREEN

- [ ] 2.2 同步修改三处正则定义
  - 文件：`config.json`（第45行）、`wizard.py`（第36行）、`qr_decoder.py`（第20行）
  - `\d{4,9}` → `\d{7,9}`（三处完全一致）
  - **验收**：三处正则字符串均精确匹配 `\d{7,9}`；1.1 测试全部 GREEN

## 3. 验证阶段

- [ ] 3.1 运行全量测试
  - 命令：`python -m pytest tests/ -v`
  - 所有旧测试保持 GREEN，新测试 GREEN
  - **验收**：0 失败

- [ ] 3.2 编译检查
  - `python -m py_compile filter.py qr_decoder.py wizard.py`
  - 无语法错误
  - **验收**：编译通过
