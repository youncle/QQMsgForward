## 1. 默认窗口尺寸

- [x] 1.1 将 `root.geometry('520x500')` 改为 `root.geometry('900x650')`

## 2. 窗口尺寸持久化

- [x] 2.1 在 `tray.py` 新增 `WINDOW_STATE_FILE` 常量、`load_window_geometry()` 和 `save_window_geometry()` 函数
- [x] 2.2 在 `__main__` 块中整合读取逻辑：窗口创建后先 `withdraw()` → 读保存值 → `geometry()` → 后续正常流程
- [x] 2.3 绑定 `<Configure>` 事件 + debounce 500ms 保存逻辑，过滤最小化状态
