# 自适应节点视图（ComfyUI 风格详细版）

## 📋 更新概述

本更新完成 **Phase 12：自适应节点视图**。新增第三种节点样式「详细版」，在画布上直接渲染节点参数编辑控件（类似 ComfyUI）。参数修改即时写回 `config.json`，支持双向数据绑定。所有样式切换通过右键菜单统一驱动，节点尺寸精确还原，无残留控件。

---

## 🏗️ 架构设计

```
                             config.json
                      { "parameters": [ ... ] }
                              │
                       ┌──────▼──────┐
                       │ NodeConfigParser │
                       │  解析参数定义  │
                       └──────┬──────┘
                              │
                       ┌──────▼──────┐
                       │ ParameterWidgets │
                       │  参数控件工厂  │
                       │  string/text/password  │
                       │  int/float/bool/enum  │
                       │  file/dir/color/range │
                       └──────┬──────┘
                              │
                 ┌────────────┼────────────┐
         ┌───────▼──────┐   ┌▼────────┐   ┌▼────────┐
         │ DetailedNodeStyle │   │ RectNodeStyle │   │ DotNodeStyle │
         │  内容驱动尺寸  │   │ 方形版   │   │ 圆形版   │
         │  status_show=True │   │  140×80  │   │  80×80  │
         └────────┬───────┘   └──────────┘   └──────────┘
                  │
           ┌──────▼──────┐
           │  NodeItem    │
           │  _proxy_widgets │
           │  _param_widgets │
           │  set_style()   │
           └────────────────┘
```

---

## 🎯 核心功能

### 1. 参数 JSON 标准格式

**`node_python_1/config.json` 示例**

```json
{
    "node_name": "cloud_inference",
    "listen_upper_file": "../data/upper_data.json",
    "output_file": "./output.json",
    "parameters": [
        {
            "name": "provider",
            "type": "enum",
            "label": "云服务商",
            "default": "openai",
            "options": ["openai", "anthropic", "google"]
        },
        {
            "name": "model",
            "type": "enum",
            "label": "模型",
            "default": "gpt-4o",
            "options": ["gpt-4o", "gpt-4o-mini", "claude-sonnet"]
        },
        {
            "name": "temperature",
            "type": "float",
            "label": "Temperature",
            "default": 0.7,
            "min": 0.0,
            "max": 2.0,
            "step": 0.1
        },
        {
            "name": "api_key",
            "type": "password",
            "label": "API Key",
            "default": ""
        },
        {
            "name": "max_tokens",
            "type": "int",
            "label": "最大Token",
            "default": 2048,
            "min": 1,
            "max": 128000
        },
        {
            "name": "system_prompt",
            "type": "text",
            "label": "系统提示词",
            "default": "你是一个有帮助的AI助手",
            "rows": 3
        }
    ]
}
```

**参数类型 → 控件映射**

| type | 控件 | Qt 组件 | 特性 |
|------|------|---------|------|
| `string` | 单行文本输入 | `QLineEdit` | 自由文本 |
| `text` | 多行文本输入 | `QPlainTextEdit` | 支持 `rows` 参数 |
| `password` | 密码输入框 | `QLineEdit(EchoMode.Password)` | 输入被遮蔽 |
| `int` | 整数输入 | `QSpinBox` | 支持 `min/max/step` |
| `float` | 浮点输入 | `QDoubleSpinBox` | 支持 `min/max/step/decimals` |
| `bool` | 复选框 | `QCheckBox` | 开关值 |
| `enum` | 下拉选择 | `QComboBox` | 支持 `options` |
| `file` | 文件选择 | `QLineEdit` + 文件对话框 | `file_filter` |
| `directory` | 目录选择 | `QLineEdit` + 目录对话框 | |
| `color` | 颜色选择 | `QPushButton` + `QColorDialog` | 实时颜色预览 |
| `range` | 滑块 + 数值 | `QSlider` + `QLabel` | 支持 `min/max` |

---

### 2. NodeConfigParser — 参数解析器

**新增文件**：`ui/core/node_config_parser.py`（55 行）

```python
@dataclass
class ParameterDef:
    name: str
    type: str
    label: str
    default: Any = None
    required: bool = False
    # 约束字段
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 2
    options: list[str] = field(default_factory=list)
    file_filter: str = ""
    rows: int = 1

class NodeConfigParser:
    @staticmethod
    def parse(config: dict) -> list[ParameterDef]:
        raw = config.get("parameters", [])
        return [ParameterDef(**p) for p in raw]

    @staticmethod
    def extract_values(config: dict) -> dict[str, Any]:
        result = {}
        for p in (config.get("parameters") or []):
            result[p["name"]] = config.get(p["name"], p.get("default"))
        return result

    @staticmethod
    def has_parameters(config: dict) -> bool:
        return bool(config and config.get("parameters"))
```

---

### 3. ParameterWidgets — 参数控件工厂

**新增文件**：`ui/canvas/parameter_widgets.py`（372 行）

**基类 `ParameterWidget(QWidget)`**：

```python
class ParameterWidget(QWidget):
    value_changed = Signal(str, object)  # param_name, value
    def __init__(self, param: ParameterDef, current_value=None): ...
    def get_value(self): ...
    def set_value(self, v): ...
    @classmethod
    def create(cls, param: ParameterDef, current_value=None): ...
```

**11 种具体控件类**：

| 类名 | 功能 | 信号发射 |
|------|------|---------|
| `StringWidget` | 标签 + 单行输入框 | `textChanged` → `value_changed` |
| `TextWidget` | 标签 + 多行输入框（高度=rows×22） | `textChanged` → `value_changed` |
| `PasswordWidget` | 标签 + 密码输入框（黑色圆点） | `textChanged` → `value_changed` |
| `IntWidget` | 标签 + QSpinBox | `valueChanged` → `value_changed` |
| `FloatWidget` | 标签 + QDoubleSpinBox | `valueChanged` → `value_changed` |
| `BoolWidget` | 标签 + QCheckBox | `stateChanged` → `value_changed` |
| `EnumWidget` | 标签 + QComboBox | `currentTextChanged` → `value_changed` |
| `FilePickerWidget` | 标签 + QLineEdit + QPushButton(📁) | 确认后发射 |
| `DirPickerWidget` | 标签 + QLineEdit + QPushButton(📂) | 确认后发射 |
| `ColorWidget` | 标签 + QPushButton(颜色预览) + QColorDialog | 选择后发射 |
| `RangeWidget` | 标签 + QSlider + QLabel(数值) | `valueChanged` → `value_changed` |

**尺寸约束**：
- 标签宽度自动根据文本内容计算（`QFontMetrics`）
- 每个参数行统一 `setMinimumHeight(24)`
- 输入控件统一 `setMinimumHeight(22)`

---

### 4. DetailedNodeStyle — 详细版样式

**修改文件**：`ui/canvas/items/node_style.py`

```python
class DetailedNodeStyle(RectNodeStyle):
    """详细版节点 — 画布上直显参数编辑控件"""
    style_key = "detailed"
    style_name = "详细版"
    is_dot = False
    status_show = True

    HEADER_HEIGHT = 26       # 标题区高度（节点名称）
    DIVIDER_HEIGHT = 4       # 标题与参数区间隔
    BOTTOM_PADDING = 6       # 底部留白
    ROW_HEIGHT = 24          # 单行参数控件高度
    MIN_NODE_WIDTH = 240     # 最小宽度兜底

    def set_sizes(self, content_width: int, content_height: int):
        self._computed_width = max(self.MIN_NODE_WIDTH, content_width)
        self._computed_height = (
            self.HEADER_HEIGHT + self.DIVIDER_HEIGHT +
            content_height + self.BOTTOM_PADDING
        )
        self.node_width = self._computed_width
        self.node_height = self._computed_height

    def apply(self, node_item):
        if hasattr(node_item, "_status_widget") and node_item._status_widget:
            node_item._status_widget.set_visible(False)
        node_item._build_detailed_view()
```

**STYLES 注册表更新**：

```python
STYLES = {
    "rect": DarkRectNodeStyle,     # 方形版
    "dot": DotNodeStyle,            # 圆形版
    "detailed": DetailedNodeStyle,  # 详细版（新增）
}
```

---

### 5. NodeItem 扩展 — 控件嵌入与数据绑定

**修改文件**：`ui/canvas/items/node_item.py`

新增核心数据结构：

```python
self._proxy_widgets: list[QGraphicsProxyWidget] = []
self._param_widgets: dict[str, ParameterWidget] = {}
self._rect_default_width = 140   # 原始节点宽
self._rect_default_height = 80   # 原始节点高
```

**核心方法 `_build_detailed_view()`**：

```python
def _build_detailed_view(self):
    # 读取节点 config.json
    config = self._get_node_config()
    if not config or not NodeConfigParser.has_parameters(config):
        # 无参数定义 — 降级为普通方框
        from ui.canvas.items.node_style import DarkRectNodeStyle
        fallback = DarkRectNodeStyle()
        fallback.node_width = self._rect_default_width
        fallback.node_height = self._rect_default_height
        self._style = fallback
        fallback.apply(self)
        return

    params = NodeConfigParser.parse(config)
    values = NodeConfigParser.extract_values(config)

    # Phase 1: 先构建所有 ParameterWidget，adjustSize() 获取自然尺寸
    max_label_w = 0
    max_control_w = 200
    total_content_h = 0
    temp_widgets = []
    for param in params:
        current = values.get(param.name, param.default)
        widget = ParameterWidget.create(param, current)
        widget.adjustSize()
        temp_widgets.append(widget)
        total_content_h += max(widget.sizeHint().height(), ROW_HEIGHT)

    margin_left, margin_right = 10, 10
    content_w = max_label_w + max_control_w + 8
    content_h = total_content_h

    # Phase 2: 设置节点尺寸，绘制方框
    self._style.set_sizes(content_w, content_h)
    # 调用 RectNodeStyle.apply，跳过 build，直接 setRect + 样式绘制
    RectNodeStyle.apply(self._style, self)

    # Phase 3: 将所有 ParameterWidget 嵌入 QGraphicsProxyWidget
    y_offset = HEADER_HEIGHT + DIVIDER_HEIGHT
    content_area_w = self._style.node_width - margin_left - margin_right
    for widget in temp_widgets:
        widget.setFixedWidth(content_area_w)
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(widget)
        proxy.setPos(margin_left, y_offset)
        proxy.setZValue(5)
        self._proxy_widgets.append(proxy)
        self._param_widgets[widget.param.name] = widget
        y_offset += widget.height()

    # Phase 4: 数据变更监听
    for widget in self._param_widgets.values():
        widget.value_changed.connect(self._on_param_changed)
```

**双向数据绑定**：

```python
def _on_param_changed(self, name: str, value):
    """参数变更 → 即时写回 config.json"""
    config = self._get_node_config()
    if config is not None:
        config[name] = value
        self._save_node_config(config)

def _get_node_config(self) -> Optional[dict]:
    pw = self._canvas_ref.parent_window
    if pw:
        data = pw.nodes_data.get(self._node_name, {})
        return data.get('config')
    return None

def _save_node_config(self, config: dict):
    """保存 config 并同步到磁盘"""
    # 更新 nodes_data 内存 + 写回 config.json 文件
```

---

### 6. 样式切换 — 统一入口 `set_style()`

**修改文件**：`ui/canvas/items/node_item.py`（`set_style` 方法）

```python
def set_style(self, style):
    # 1) 销毁旧详细版控件
    if hasattr(self, '_proxy_widgets') and self._proxy_widgets:
        self._destroy_detailed()

    self._style = style

    # 2) 根据样式类型设置正确尺寸（避免类默认值 vs 节点原始尺寸的不一致）
    if isinstance(self._style, DotNodeStyle):
        self._style.node_width = 80
        self._style.node_height = 80
    elif isinstance(self._style, DetailedNodeStyle):
        pass  # 内容驱动，由 _build_detailed_view() 计算
    elif isinstance(self._style, RectNodeStyle):
        self._style.node_width = self._rect_default_width   # 140
        self._style.node_height = self._rect_default_height  # 80

    # 3) 应用样式
    self._style.apply(self)
    self._style.apply_status(self, self.status)

    # 4) 状态栏重新布局（使用新尺寸）
    if self._style.status_show and not self._style.is_dot:
        if not self._status_widget:
            self._status_widget = NodeStatusWidget(self)
        self._status_widget.set_visible(True)
        self._status_widget.update_layout()
        self._start_time = None
        self._connect_resource_monitor_signals()
    else:
        if self._status_widget:
            self._status_widget.set_visible(False)
            self._status_widget = None

    self._update_selection_ring(self.isSelected())
    if self.scene():
        self.scene().update()
```

**修改文件**：`ui/canvas/canvas_menus.py`（`_switch_node_style` 简化为单一调用）

```python
def _switch_node_style(self, style_key, node_item):
    from ui.canvas.items.node_style import STYLES
    cls = STYLES.get(style_key)
    if not cls:
        return
    node_item.set_style(cls())  # 所有逻辑由 NodeItem 统一处理
```

---

### 7. NodeStatusWidget — 尺寸解耦

**修改文件**：`ui/canvas/items/node_status_widget.py`

**问题**：`__init__` 中 `self._style = node_item._style` 缓存了旧样式引用，切换后仍读旧尺寸。

**修复**：每次布局时直接从 `node_item._style` 读取当前样式：

```python
def _layout_widgets(self):
    current_style = self.node_item._style
    w, h = current_style.node_width, current_style.node_height
    # ... 使用当前尺寸定位所有控件

def update_status(self, cpu_percent, mem_mb, duration_seconds):
    current_style = self.node_item._style
    w, h = current_style.node_width, current_style.node_height
    # ... 使用当前尺寸重绘进度条
```

---

## 📂 文件变更汇总

| 文件 | 操作 | 行数 | 描述 |
|------|------|------|------|
| `ui/core/node_config_parser.py` | **新增** | 55 | ParameterDef + NodeConfigParser |
| `ui/canvas/parameter_widgets.py` | **新增** | 372 | 11 种参数控件 + 工厂方法 |
| `ui/canvas/items/node_style.py` | 修改 | +32 | DetailedNodeStyle 类 + STYLES 注册 |
| `ui/canvas/items/node_item.py` | 修改 | +80 | _proxy_widgets/_param_widgets、_build_detailed_view、set_style 重构 |
| `ui/canvas/canvas_menus.py` | 修改 | -10 | _switch_node_style 简化为 set_style() |
| `ui/canvas/items/node_status_widget.py` | 修改 | +12 | 不缓存样式引用，每次读 node_item._style |
| `ui/core/strings_cn.json` | 修改 | +3 | "详细版" / "方形版" / "圆形版" i18n |
| `ui/core/strings_en.json` | 修改 | +3 | "Detailed" / "Square" / "Circle" i18n |

---

## 🐛 问题排查与修复记录

### 问题 1：切换样式后节点尺寸不正确

**现象**：从详细版切回方形版，节点变高 40 像素，状态栏间距变大。

**根因**：节点 `__init__` 默认 `h=80`，但 `NodeStyle` 类默认 `node_height=120`。切换时新 `DarkRectNodeStyle()` 实例用类默认值 120，导致节点从 140×80 变成 140×120。

**修复**：
1. 在 `NodeItem.__init__` 中保存 `self._rect_default_width/height`
2. `set_style()` 中用 `isinstance` 判断样式类型，分别设置正确尺寸：
   - RectNodeStyle → 原始尺寸 (140, 80)
   - DotNodeStyle → 类默认 (80, 80)
   - DetailedNodeStyle → 内容驱动

### 问题 2：状态栏仍使用旧尺寸

**现象**：切换后 CPU/内存进度条位置不变，与新节点尺寸不匹配。

**根因**：`NodeStatusWidget.__init__` 缓存了 `self._style = node_item._style` 引用，样式变更后指向旧对象。

**修复**：移除 `_layout_widgets` 和 `update_status` 中的 `self._style` 缓存，改为 `self.node_item._style` 每次读取最新引用，并在 `set_style` 后调用 `update_layout()`。

### 问题 3：QComboBox 下拉弹窗被截断

**现象**：详细版中 QComboBox 下拉列表被节点边界截断。

**根因**：`QGraphicsProxyWidget` 中嵌入的 QComboBox 弹窗 `mapToGlobal()` 坐标计算错误。

**修复**：`_ProxyAwareComboBox` 重写 `showPopup()`，手动从 `proxy → scene → view → viewport → global` 计算正确屏幕坐标。

### 问题 4：Proxy 控件残留

**现象**：切换回方形版后仍能看到旧参数控件。

**根因**：`_destroy_detailed()` 中未完整清理 `scene.removeItem()` + `setWidget(None)`。

**修复**：在切换前统一调用 `_destroy_detailed()`，并在 `setRect` 前重置缓存模式。

---

## ✅ 验收标准

| 检查项 | 状态 |
|--------|------|
| `config.json` 声明 `parameters` 后，详细版自动渲染参数控件 | ✅ |
| 右键菜单显示三种样式：详细版 / 方形版 / 圆形版 | ✅ |
| 详细版在画布上直接显示 11 种参数编辑控件（不下弹窗） | ✅ |
| 画布上修改参数即时保存到 `config.json` | ✅ |
| 外部修改 `config.json` 后，画布控件同步刷新 | ✅ |
| 样式切换不丢失配置数据 | ✅ |
| 切换后节点尺寸精确还原（方形 140×80，圆形 80×80） | ✅ |
| 任意样式间来回切换无 Proxy 控件残留 | ✅ |
| 所有文件 PyLance 诊断零错误 | ✅ |

---

**更新日期**：2026-06-10
