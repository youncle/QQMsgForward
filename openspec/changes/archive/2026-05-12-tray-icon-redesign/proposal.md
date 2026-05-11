## Why

当前托盘图标使用 PIL 基础绘图绘制的聊天气泡+箭头形状，视觉粗糙、缺乏精致感。需要重新设计为更现代简洁的样式。

## What Changes

- 重写 `create_icon_image()` 函数，将图标设计从"聊天气泡+双箭头"改为"中性色圆点 + 彩色外圈"风格
- 圆点颜色固定为深灰色（#37474F），外圈根据运行状态变色：
  - 绿色外圈（#4CAF50）：正常运行
  - 红色外圈（#F44336）：服务异常
  - 黄色外圈（#FFC107）：部分异常
- 保持 64x64 尺寸，保持 PIL 程序化绘制（无外部资源依赖）
- 保持现有函数签名 `create_icon_image(color: str = 'green')` 不变，调用方无需修改

## Capabilities

### New Capabilities
无新增能力

### Modified Capabilities
- `tray-main-panel`: 托盘图标视觉效果变更（纯视觉实现改动，不涉及规格文档需求变更）

## Impact

- `tray.py`：仅修改 `create_icon_image()` 函数（约 20 行绘图代码）
- 无新增依赖项
- 无外部图标资源文件
- 无 API/接口变更
