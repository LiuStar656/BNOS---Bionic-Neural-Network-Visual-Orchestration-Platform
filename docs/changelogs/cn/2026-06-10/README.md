# 2026-06-10 更新日志

## 📋 更新概述

本次更新完成了 Phase 10（IDE 工作区集成）和 **Phase 12（自适应节点视图）**。新增 IDEScanner 自动扫描器、4 个 IDE Action 注册到 Action 系统，以及第三种节点样式「详细版」（类似 ComfyUI，在画布上直接渲染参数编辑控件）。

---

## ✨ 更新内容

### 1. 🚀 IDE 自动扫描与右键菜单 Action 集成

**功能描述**：
- 新增 `IDEScanner` 自动扫描器（214 行），跨平台检测 VSCode / Trae IDE
- 四层检测链路：内存缓存 → app_config → PATH → 环境变量/进程扫描 → 文件系统
- 4 个 IDE Action 注册到 Action 系统，画布右键菜单完全由 ActionFactory 驱动
- 节点配置对话框 IDE 按钮统一调用 `ide_scanner.add_buttons_to_layout()`
- 环境变量推导 + 进程扫描覆盖非标准 Trae 安装路径（如 `F:\Trae CN\`）

**修改文件**（8 个文件）：
- 新增 `ui/core/ide_scanner.py`
- 修改 `ui/core/actions/builtin_node_actions.py`、`builtin_canvas_actions.py`
- 重构 `ui/canvas/canvas_menus.py`、`ui/dialogs/node_config_dialog.py`
- 配置 `ui/main_window.py`、i18n 字符串文件

**详细文档**：[IDE 自动扫描与右键菜单 Action 集成](./01_IDE自动扫描与右键菜单Action集成.md)

---

### 2. 🎨 自适应节点视图（ComfyUI 风格详细版）

**功能描述**：
- 新增第三种节点样式「详细版」，在画布上直接渲染参数编辑控件（类似 ComfyUI）
- 11 种参数类型：string / text / password / int / float / bool / enum / file / directory / color / range
- 控件由 Qt 原生组件 `QGraphicsProxyWidget` 嵌入，支持键盘交互
- 参数修改即时写回 `config.json`，双向数据绑定
- 样式切换：详细版 ↔ 方形版 ↔ 圆形版，任意切换无残留控件
- 节点尺寸精确还原：方形 140×80，圆形 80×80
- 详细版尺寸由参数内容自动计算（最小宽度 240px）

**修改文件**（8 个文件，~450 行新增代码）：
- **新增** `ui/core/node_config_parser.py`（ParameterDef + 解析器）
- **新增** `ui/canvas/parameter_widgets.py`（11 种控件工厂）
- 修改 `ui/canvas/items/node_style.py`（DetailedNodeStyle + STYLES 注册）
- 修改 `ui/canvas/items/node_item.py`（_build_detailed_view + set_style 重构）
- 修改 `ui/canvas/canvas_menus.py`（_switch_node_style 简化）
- 修改 `ui/canvas/items/node_status_widget.py`（样式引用去缓存）
- 修改 i18n 字符串文件（"详细版" / "方形版" / "圆形版"）

**关键修复**：
- 节点创建尺寸 (140×80) 与样式类默认 (140×120) 不一致 → `_rect_default_width/height` 保存原始值
- NodeStatusWidget 缓存旧样式引用 → 每次从 `node_item._style` 读取
- QComboBox 下拉弹窗在 ProxyWidget 中坐标错误 → `_ProxyAwareComboBox` 重写 showPopup
- 样式切换后 Proxy 控件残留 → `_destroy_detailed()` 统一清理

**详细文档**：[自适应节点视图（ComfyUI 风格详细版）](./02_自适应节点视图_ComfyUI风格详细版.md)

---

## 🎯 总览

| 功能 | 状态 |
|------|------|
| IDEScanner 自动扫描器 | ✅ 完成 |
| IDE Action 注册（4 个） | ✅ 完成 |
| 画布右键菜单 Action 驱动 | ✅ 完成 |
| 节点配置对话框按钮统一 | ✅ 完成 |
| Trae 非标准路径修复 | ✅ 完成 |
| Phase 10 IDE 工作区集成 | ✅ 完成 |
| **Phase 12 详细版节点视图** | ✅ 完成 |
| 参数 JSON 标准格式 | ✅ 完成 |
| 11 种参数控件类型 | ✅ 完成 |
| Qt ProxyWidget 嵌入画布 | ✅ 完成 |
| 双向数据绑定（即时写回 config.json） | ✅ 完成 |
| 样式切换无尺寸错乱 | ✅ 完成 |
| 样式切换无控件残留 | ✅ 完成 |

---

**更新日期**：2026-06-10
