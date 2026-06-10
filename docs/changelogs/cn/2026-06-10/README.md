# 2026-06-10 更新日志

## 📋 更新概述

本次更新完成了 Phase 10（IDE 工作区集成）、**Phase 12（自适应节点视图）** 以及**多锚点系统完善与连线持久化**。新增 IDEScanner 自动扫描器、4 个 IDE Action 注册到 Action 系统、第三种节点样式「面板模式」（类似 ComfyUI），以及锚点差异化定位、端口映射修正、连线持久化等关键修复。

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

### 2. 🎨 自适应节点视图（ComfyUI 风格面板模式）

**功能描述**：
- 新增第三种节点样式「面板模式」，在画布上直接渲染参数编辑控件（类似 ComfyUI）
- 11 种参数类型：string / text / password / int / float / bool / enum / file / directory / color / range
- 控件由 Qt 原生组件 `QGraphicsProxyWidget` 嵌入，支持键盘交互
- 参数修改即时写回 `config.json`，双向数据绑定
- 样式切换：面板模式 ↔ 框图模式 ↔ 节点模式，任意切换无残留控件
- 节点尺寸精确还原：框图 140×80，节点 80×80
- 面板模式尺寸由参数内容自动计算（最小宽度 240px）

**修改文件**（8 个文件，~450 行新增代码）：
- **新增** `ui/core/node_config_parser.py`（ParameterDef + 解析器）
- **新增** `ui/canvas/parameter_widgets.py`（11 种控件工厂）
- 修改 `ui/canvas/items/node_style.py`（DetailedNodeStyle + STYLES 注册）
- 修改 `ui/canvas/items/node_item.py`（_build_detailed_view + set_style 重构）
- 修改 `ui/canvas/canvas_menus.py`（_switch_node_style 简化）
- 修改 `ui/canvas/items/node_status_widget.py`（样式引用去缓存）
- 修改 i18n 字符串文件（"面板模式" / "框图模式" / "节点模式"）

---

### 3. 📝 节点样式命名优化

**功能描述**：
- 节点样式名称从直白的描述性命名优化为更专业的几何+功能风格命名
- 提升产品设计感和品牌调性

**命名变更**：

| 原名 | 新名称 | 英文名 | 设计理念 |
|------|--------|--------|----------|
| 方形版 | 框图模式 | Block | 经典方块流程图风格 |
| 圆形版 | 节点模式 | Node | 点状节点，突出连接关系 |
| 详细版 | 面板模式 | Panel | 展开式控制面板 |

**修改文件**：
- `ui/core/strings_cn.json`
- `ui/core/strings_en.json`

---

### 4. 🔌 多输入端口支持（面板模式）

**功能描述**：
- 支持通过 `config.json` 定义多个输入端口（`input_ports` 字段）
- 每个端口可定义名称、显示标签、数据类型、是否必需等属性
- 面板模式下自动创建多输入锚点，均匀分布在节点左侧
- 支持端口类型校验和默认端口设置
- 向后兼容：未定义多端口的节点使用默认单锚点

**配置示例**（`config.json`）：
```json
{
  "input_ports": [
    {"name": "input_sensor", "label": "传感器数据", "type": "sensor", "required": true},
    {"name": "input_logs", "label": "日志数据", "type": "log"},
    {"name": "input_config", "label": "配置", "type": "json"}
  ],
  "parameters": [...]
}
```

**输入端口字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 端口唯一标识 |
| `label` | string | 端口显示名称 |
| `type` | string | 数据类型（用于兼容性校验） |
| `required` | bool | 是否必需连接 |
| `description` | string | 端口描述（可选） |

**修改文件**：
- `ui/core/node_config_parser.py`（新增 `InputPortDef` 数据类和解析方法）
- `ui/canvas/items/node_item.py`（新增多锚点容器和构建方法、点击检测逻辑）
- `ui/canvas/items/node_style.py`（所有样式支持多锚点构建）
- `ui/canvas/items/edge_item.py`（支持多端口连接逻辑）
- `ui/canvas/canvas_connections.py`（支持端口映射保存和加载）

**端口映射机制**：
- 连线时根据点击的锚点，将映射关系保存到 `config.json` 的 `port_mappings` 字段
- 每个端口可以连接不同的上游节点
- 节点执行时可根据端口映射从不同数据源获取数据

**样式支持**：
- ✅ 框图模式：支持多输入端口
- ✅ 面板模式：支持多输入端口
- ⚠️ 节点模式（圆形）：仅支持单锚点（空间限制）

**关键修复**：
- 节点创建尺寸 (140×80) 与样式类默认 (140×120) 不一致 → `_rect_default_width/height` 保存原始值
- NodeStatusWidget 缓存旧样式引用 → 每次从 `node_item._style` 读取
- QComboBox 下拉弹窗在 ProxyWidget 中坐标错误 → `_ProxyAwareComboBox` 重写 showPopup
- 样式切换后 Proxy 控件残留 → `_destroy_detailed()` 统一清理

**详细文档**：[自适应节点视图（ComfyUI 风格详细版）](./02_自适应节点视图_ComfyUI风格详细版.md)

---

### 5. 🔧 多锚点系统完善与连线持久化

**功能描述**：
- 锚点差异化：主输入锚点（`listen_upper_file`）16px 左边界居中，附加输入端口锚点 10px 紧贴标签左侧
- 端口映射修正：`port_name="default"` 写入 `listen_upper_file` 而非 `port_mappings["default"]`
- 连线层级提升：EdgeItem z-value 0 → 20，确保连线始终在最顶层
- 持久化修复：`canvas_layout.json` 保存 `source_port` / `target_port`，重启后恢复正确锚点绑定
- 批量清除完善：`clear_canvas` 和 `batch_clear_listen_config` 正确处理 `port_mappings` 清理

**修改文件**（8 个文件）：
- 修改 `ui/canvas/items/anchor_item.py`（双尺寸锚点支持）
- 修改 `ui/canvas/items/anchor_manager.py`（size 参数、动态距离计算）
- 修改 `ui/canvas/items/node_item.py`（小锚点坐标计算）
- 修改 `ui/canvas/items/edge_item.py`（z-value 提升）
- 修改 `ui/canvas/canvas_connections.py`（端口映射分发）
- 修改 `ui/canvas/canvas_layout.py`（持久化 + 绑定校验）
- 修改 `ui/canvas/canvas_view.py`（clear_canvas 修复）
- 修改 `ui/canvas/canvas_batch_ops.py`（批量清除完善）

**详细文档**：[多锚点系统完善与连线持久化](./03_多锚点系统完善与连线持久化.md)

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
| 主/副锚点尺寸差异化（16px / 10px） | ✅ 完成 |
| 端口映射正确分发（default → listen_upper_file） | ✅ 完成 |
| 连线层级提升至最顶层（z=20） | ✅ 完成 |
| 连线端口信息持久化（重启不丢失） | ✅ 完成 |
| 批量清除 port_mappings 支持 | ✅ 完成 |

---

**更新日期**：2026-06-10
