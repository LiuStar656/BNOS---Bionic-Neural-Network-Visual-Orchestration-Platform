# Phase 12：自适应节点视图（类似 ComfyUI）— 完整开发方案

## 📋 更新概述

开发类似 ComfyUI 的自适应节点视图系统。节点开发者通过 JSON 配置声明视图参数，BNOS 读取后在画布上自动生成参数编辑控件，用户直接在画布上进行参数编辑。

**节点表现形式**（右键切换）：

| 表现形式 | 适用场景 | 显示内容 |
|----------|----------|----------|
| **详细版** | 需要频繁调整参数的节点 | 完整显示所有可编辑参数控件（文本框、下拉菜单、滑块、文件选择器等） |
| **方形版** | 中等复杂度节点 | 显示节点名称 + 少量关键状态信息（简洁风格） |
| **圆形版** | 简单节点或数据传递节点 | 仅显示节点图标或名称（最小占用空间） |

---

## 🔍 现状分析

| 维度 | 现状 | 缺口 |
|------|------|------|
| 节点样式 | 仅 2 种：rect（方形）/ dot（圆形） | 无"详细版"（带参数的完整视图） |
| 参数编辑 | 原始 JSON 文本框（dialog 弹窗） | 无画布直显、无结构化控件 |
| 控件嵌入 | **完全未使用** `QGraphicsProxyWidget` | 需要从零引入 |
| NodeItem | 单一类，样式仅改视觉 | 需要支持内容差异化渲染 |
| config.json | 自由格式，无 schema | 需要标准化参数声明格式 |
| Action 系统 | 50 个 Action 全覆盖 | 新增样式切换只需注册 STYLES 条目 |

---

## 🏗️ 架构设计

```
                          ┌─────────────────────────┐
                          │    node_config.json       │
                          │  {                        │
                          │    "parameters": [...],   │
                          │    "node_name": "...",    │
                          │    ...                    │
                          │  }                        │
                          └──────────┬───────────────┘
                                     │
                          ┌──────────▼───────────────┐
                          │   NodeConfigParser        │
                          │   parse() → ParameterDef[]│
                          │   extract_values()        │
                          │   validate()              │
                          └──────────┬───────────────┘
                                     │
                          ┌──────────▼───────────────┐
                          │   WidgetFactory           │
                          │   create(param) → QWidget │
                          │   TYPE_MAP:               │
                          │    string → QLineEdit     │
                          │    enum   → QComboBox     │
                          │    float  → QDoubleSpinBox│
                          │    file   → FilePicker    │
                          │    ...                    │
                          └──────────┬───────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │  DetailedNode   │   │  RectNodeStyle  │   │  DotNodeStyle   │
    │  Style          │   │  (existing)     │   │  (existing)     │
    │  ProxyWidget[]  │   │  纯 QGraphics   │   │  纯 QGraphics   │
    │  双向数据绑定    │   │  Item 渲染       │   │  Item 渲染       │
    └─────────────────┘   └─────────────────┘   └─────────────────┘
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     ▼
                          ┌─────────────────────────┐
                          │   NodeItem               │
                          │   +_proxy_widgets: list  │
                          │   +_param_widgets: dict  │
                          │   +_build_detailed_view()│
                          │   +_destroy_detailed()   │
                          └─────────────────────────┘
```

**设计原则**：
- `NodeStyle.apply()` 负责创建/销毁控件 — 样式决定内容
- `WidgetFactory` 是纯函数映射，不持有状态
- `NodeConfigParser` 只做解析，不做渲染
- 数据绑定：widget → config.json（即时）+ config.json → widget（polling_manager 信号）

---

## 🎯 核心特性

| 特性 | 描述 |
|------|------|
| **画布直显** | 节点视图直接渲染在画布上，无需弹出新窗口 |
| **声明式配置** | 节点开发者通过 JSON 声明视图参数，无需编写 UI 代码 |
| **类型驱动渲染** | 根据参数类型（string、enum、float、file、model 等）自动选择合适控件 |
| **多表现形式** | 支持详细版/方形版/圆形版三种样式，右键随时切换 |
| **双向数据绑定** | 画布上修改参数即时保存到 JSON 配置，外部修改自动刷新画布 |
| **统一框架** | 所有需要参数编辑的节点都基于同一套机制，扩展简便 |

---

## 📐 任务分解

| 任务 | 描述 | 优先级 |
|------|------|--------|
| **T1** | 设计节点配置 JSON 标准格式规范 | 高 |
| **T2** | 开发 `NodeConfigParser` JSON 解析器 | 高 |
| **T3** | 实现 `WidgetFactory` 参数类型到画布控件的映射系统 | 高 |
| **T4** | 开发画布控件库（文本框、下拉框、滑块、文件选择器、密码框等 11 种类型） | 高 |
| **T5** | 实现 `DetailedNodeStyle` + `NodeItem` 详细版布局渲染 | 高 |
| **T6** | 实现节点三种表现形式（详细版/方形版/圆形版）样式切换 | 高 |
| **T7** | 实现画布节点实时参数编辑与双向数据绑定 | 高 |
| **T8** | 添加 i18n 字符串 | 中 |

---

## 🔧 Step 1：参数 JSON 标准格式

在现有 `config.json` 中新增 `parameters` 字段，完全后向兼容（无 `parameters` 字段时不影响现有功能）：

**示例 1：云 API 推理节点配置**

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
            "options": ["openai", "anthropic", "google", "local"]
        },
        {
            "name": "api_key",
            "type": "password",
            "label": "API Key",
            "required": true
        },
        {
            "name": "model",
            "type": "enum",
            "label": "模型",
            "default": "gpt-4o",
            "options": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "dynamic_options": {
                "source": "api:list_models",
                "depends_on": ["provider", "api_key"]
            }
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
            "name": "max_tokens",
            "type": "int",
            "label": "最大 Token 数",
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

**示例 2：本地推理引擎节点配置**

```json
{
    "node_name": "local_inference",
    "listen_upper_file": "../data/upper_data.json",
    "output_file": "./output.json",
    "parameters": [
        {
            "name": "model_path",
            "type": "file",
            "label": "模型文件",
            "file_filter": "模型文件 (*.bin *.gguf *.safetensors)",
            "required": true
        },
        {
            "name": "model_type",
            "type": "enum",
            "label": "模型类型",
            "default": "llama",
            "options": ["llama", "mistral", "qwen", "other"]
        },
        {
            "name": "context_length",
            "type": "int",
            "label": "上下文长度",
            "default": 4096,
            "min": 512,
            "max": 32768
        },
        {
            "name": "gpu_layers",
            "type": "int",
            "label": "GPU 卸载层数",
            "default": -1,
            "min": -1,
            "max": 100
        },
        {
            "name": "threads",
            "type": "int",
            "label": "CPU 线程数",
            "default": 8,
            "min": 1,
            "max": 128
        },
        {
            "name": "batch_size",
            "type": "int",
            "label": "Batch Size",
            "default": 512,
            "min": 1,
            "max": 8192
        }
    ]
}
```

**参数类型与控件映射表**：

| type | 控件 | 描述 | 额外字段 |
|------|------|------|----------|
| `string` | QLineEdit | 单行文本 | - |
| `text` | QTextEdit（通过 ProxyWidget 嵌入） | 多行文本 | `rows` |
| `password` | QLineEdit (EchoMode.Password) | 密码隐藏 | - |
| `int` | QSpinBox | 整数 | `min`, `max`, `step` |
| `float` | QDoubleSpinBox | 浮点数 | `min`, `max`, `step`, `decimals` |
| `bool` | QCheckBox | 复选框 | - |
| `enum` | QComboBox | 下拉选择 | `options`, `dynamic_options`(v1.1) |
| `file` | QLineEdit + QPushButton(…) | 文件选择 | `file_filter` |
| `directory` | QLineEdit + QPushButton(…) | 目录选择 | - |
| `color` | QPushButton + QColorDialog | 颜色选择 | - |
| `range` | QSlider + QLabel | 滑块+数值 | `min`, `max`, `step` |

---

## 🔧 Step 2：`NodeConfigParser` — 新增 `ui/core/node_config_parser.py`

```python
"""
节点配置解析器 — 从 config.json 中提取参数定义
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParameterDef:
    """单个参数的定义"""
    name: str
    type: str          # string|text|password|int|float|bool|enum|file|directory|color|range
    label: str
    default: Any = None
    required: bool = False
    # 数值约束
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 2
    # 枚举约束
    options: list[str] = field(default_factory=list)
    # 文件约束
    file_filter: str = ""
    # 文本约束
    rows: int = 1
    # 动态选项（v1.1）
    dynamic_options: Optional[dict] = None


class NodeConfigParser:
    """节点配置解析器"""

    @staticmethod
    def parse(config: dict) -> list[ParameterDef]:
        """从 config.json 字典中提取参数定义列表"""
        raw = config.get("parameters", [])
        if not raw:
            return []
        return [ParameterDef(**p) for p in raw]

    @staticmethod
    def extract_values(config: dict) -> dict[str, Any]:
        """从 config.json 中提取参数实际值（参数名 → 当前值）"""
        result = {}
        for p_def in (config.get("parameters") or []):
            name = p_def["name"]
            result[name] = config.get(name, p_def.get("default"))
        return result

    @staticmethod
    def has_parameters(config: dict) -> bool:
        """检查配置是否包含参数定义"""
        return bool(config.get("parameters"))
```

---

## 🔧 Step 3：`WidgetFactory` + 控件库 — 新增 `ui/canvas/parameter_widgets.py`

```
参数控件层次：
    ParameterWidget (基类)
    ├── StringWidget      — QLineEdit
    ├── TextWidget        — QTextEdit (proxy)
    ├── PasswordWidget    — QLineEdit(EchoMode.Password)
    ├── IntWidget         — QSpinBox
    ├── FloatWidget       — QDoubleSpinBox
    ├── BoolWidget        — QCheckBox
    ├── EnumWidget        — QComboBox
    ├── FilePickerWidget  — QLineEdit + QPushButton(…)
    ├── DirPickerWidget   — QLineEdit + QPushButton(…)
    ├── ColorWidget       — QPushButton + QColorDialog
    └── RangeWidget       — QSlider + QLabel
```

每个控件类遵循统一接口：

```python
class ParameterWidget(QWidget):
    """参数控件基类"""
    value_changed = Signal(str, object)  # param_name, value

    def __init__(self, param: ParameterDef, current_value=None): ...

    def get_value(self) -> Any:
        """获取当前值"""
        return self._current

    def set_value(self, value: Any):
        """由外部设置值（数据绑定回写时调用）"""
        ...

    @classmethod
    def create(cls, param: ParameterDef, current_value=None) -> 'ParameterWidget':
        """工厂方法"""
        mapping = {
            "string": StringWidget,
            "text": TextWidget,
            "password": PasswordWidget,
            "int": IntWidget,
            "float": FloatWidget,
            "bool": BoolWidget,
            "enum": EnumWidget,
            "file": FilePickerWidget,
            "directory": DirPickerWidget,
            "color": ColorWidget,
            "range": RangeWidget,
        }
        return mapping.get(param.type, StringWidget)(param, current_value)
```

**注意**：`QTextEdit` 不能直接通过 `QGraphicsProxyWidget` 完美工作（富文本控件有焦点问题），多行文本改用 `QPlainTextEdit`。

---

## 🔧 Step 4：`DetailedNodeStyle` — 扩展 `ui/canvas/items/node_style.py`

```python
class DetailedNodeStyle(RectNodeStyle):
    """详细版节点 — 画布上直显参数编辑控件"""
    style_key = "detailed"
    style_name = "详细版"
    is_dot = False
    status_show = True

    ROW_HEIGHT = 28

    def __init__(self):
        super().__init__()
        self._param_count = 0

    def set_param_count(self, count: int):
        """根据参数数量动态调整节点高度"""
        self._param_count = count
        # 基础高度 60（标题栏+状态栏） + 参数区高度 + 底部留白 20
        self.node_height = max(120, 60 + count * self.ROW_HEIGHT + 20)
        # 详细版适当加宽以容纳控件
        self.node_width = max(220, self.node_width)

    def apply(self, node_item: 'NodeItem'):
        # 1. 方框基础渲染（标题栏、锚点、状态灯等）
        super().apply(node_item)
        # 2. 触发参数控件构建（在 NodeItem 中执行）
        node_item._build_detailed_view()
```

**STYLES 注册表更新**：

```python
STYLES = {
    "rect": DarkRectNodeStyle,       # 现有：方形版
    "dot": DotNodeStyle,             # 现有：圆形版
    "detailed": DetailedNodeStyle,   # 新增：详细版
}
DEFAULT_STYLE = "rect"
```

---

## 🔧 Step 5：修改 `NodeItem` — `ui/canvas/items/node_item.py`

新增字段和方法：

```python
class NodeItem(QGraphicsRectItem):
    def __init__(self, ...):
        # ... 原有代码 ...
        self._proxy_widgets: list[QGraphicsProxyWidget] = []  # 新增
        self._param_widgets: dict[str, ParameterWidget] = {}  # 新增

    def _build_detailed_view(self):
        """构建详细版参数控件（仅 DetailedNodeStyle 调用）"""
        self._destroy_detailed()

        config = self._get_node_config()
        if not config or not NodeConfigParser.has_parameters(config):
            return

        params = NodeConfigParser.parse(config)
        self._style.set_param_count(len(params))
        self._style.apply(self)  # 重新设置节点尺寸

        y_offset = 55  # 参数区起始 Y（标题栏下方）
        for i, param in enumerate(params):
            current = config.get(param.name, param.default)
            widget = ParameterWidget.create(param, current)
            widget.value_changed.connect(self._on_param_changed)
            self._param_widgets[param.name] = widget

            # 嵌入到 QGraphicsScene 的关键步骤
            proxy = QGraphicsProxyWidget(self)
            proxy.setWidget(widget)
            proxy.setPos(8, y_offset + i * self._style.ROW_HEIGHT)
            proxy.setZValue(5)
            self._proxy_widgets.append(proxy)

    def _destroy_detailed(self):
        """销毁详细版控件（样式切换时调用）"""
        for p in self._proxy_widgets:
            p.setWidget(None)
            if self.scene():
                self.scene().removeItem(p)
        self._proxy_widgets.clear()
        self._param_widgets.clear()

    def _on_param_changed(self, name: str, value):
        """参数变更 → 写回 config.json"""
        config = self._get_node_config()
        if config is not None:
            config[name] = value
            self._save_node_config(config)

    def _get_node_config(self) -> Optional[dict]:
        """获取当前节点 config"""
        pw = self._get_parent_window()
        if pw:
            data = pw.nodes_data.get(self._node_name, {})
            return data.get('config')
        return None

    def _save_node_config(self, config: dict):
        """保存 config 到文件并同步内存"""
        pw = self._get_parent_window()
        if pw:
            pw.nodes_data[self._node_name]['config'] = config
            node_path = pw.nodes_data[self._node_name].get('path', '')
            if node_path:
                import json
                cfg_path = os.path.join(node_path, 'config.json')
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)

    def _get_parent_window(self):
        """获取 main_window 引用"""
        if self._canvas_ref and self._canvas_ref.parent_window:
            return self._canvas_ref.parent_window
        return None
```

---

## 🔧 Step 6：样式切换流程

`canvas_menus.py` 中 `_switch_node_style` 需要加一行清理逻辑：

```python
def _switch_node_style(self, style_key, node_item):
    # ★ 切换前先销毁详细版控件
    node_item._destroy_detailed()

    # ... 原有切换逻辑（创建新样式实例 → apply → 重绘连线 → 保存布局）...
```

右键菜单中样式子菜单已通过遍历 `STYLES` 自动生成，`DetailedNodeStyle` 注册后自动出现在列表中，无需额外代码。

---

## 🔧 Step 7：双向数据绑定

```
参数编辑流：
  widget.value_changed ──► _on_param_changed() ──► config.json 写入
                                                            │
外部修改流：                                                  │
  polling_manager.config_file_changed ◄──────────────────────┘
          │
          ▼
    NodeItem._on_external_config_change() ──► widget.set_value()
```

`NodeItem` 中订阅 polling_manager 信号（在 `__init__` 或 `_build_detailed_view` 中）：

```python
def _subscribe_config_changes(self):
    """订阅 config.json 外部变更信号"""
    pw = self._get_parent_window()
    if pw and hasattr(pw, 'polling_manager'):
        try:
            pw.polling_manager.config_file_changed.connect(
                self._on_external_config_change)
        except Exception:
            pass  # 重复连接忽略

def _on_external_config_change(self, node_name: str):
    """外部修改 config.json → 刷新画布控件"""
    if node_name != self._node_name:
        return
    config = self._get_node_config()
    if config:
        for name, widget in self._param_widgets.items():
            if name in config:
                widget.set_value(config[name])
```

---

## 🔧 Step 8：i18n 字符串

**`strings_cn.json` 新增**：

```json
"k_node_style_detailed": "详细版",
"k_node_style_square": "方形版",
"k_node_style_circular": "圆形版"
```

**`strings_en.json` 新增**：

```json
"k_node_style_detailed": "Detailed",
"k_node_style_square": "Square",
"k_node_style_circular": "Circular"
```

样式类 `style_name` 属性改用 `t("k_node_style_detailed")`。

---

## 📁 文件变更汇总

| 文件 | 操作 | 预估行数 | 描述 |
|------|------|----------|------|
| `ui/core/node_config_parser.py` | **新增** | ~120 | 参数定义解析器 + ParameterDef 数据类 |
| `ui/canvas/parameter_widgets.py` | **新增** | ~250 | 参数控件工厂 + 11 种子类 |
| `ui/canvas/items/node_style.py` | 修改 | +50 | 新增 `DetailedNodeStyle` + STYLES 注册表更新 |
| `ui/canvas/items/node_item.py` | 修改 | +80 | 嵌入 proxy_widgets + 数据绑定 + 订阅 config 变更 |
| `ui/canvas/canvas_menus.py` | 修改 | +3 | 样式切换前清理详细版控件 |
| `ui/core/strings_cn.json` | 修改 | +3 | 中文字符串 |
| `ui/core/strings_en.json` | 修改 | +3 | 英文字符串 |

**预估净增代码：~500 行**

---

## 🗺️ 画布效果示意

```
详细版（云 API 推理节点）                  方形版                    圆形版
┌─────────────────────────────────┐     ┌───────────────┐         ◯
│ ☁️ 云端推理          ● 运行中    │     │   ☁️ 云推理   │    云端推理
├─────────────────────────────────┤     │    ● 运行中    │
│ 云服务商 [OpenAI          ▼]    │     └───────────────┘         ◯
│ API Key  [•••••••••••••••]     │
│ 模型     [GPT-4o          ▼]    │
│ Temp     [══════●═══════] 0.7  │
│ 最大Token [____2048______]      │
│ 系统提示词 [你是一个有帮助的...] │    右键菜单：              右键菜单：
│                                  │    ┌────────────────┐   ┌────────────────┐
│ 右键菜单：                       │    │ 🔲 方形版       │   │ ◯ 圆形版       │
└──────────────────────────────────┘    │ 📋 详细版       │   │ 📋 详细版       │
                                         │ 🗑️ 删除        │   │ 🗑️ 删除        │
                                         └────────────────┘   └────────────────┘
```

---

## ⚠️ 注意事项

- **QGraphicsProxyWidget 性能**：每个嵌入的 widget 都会产生额外开销，单个节点的参数建议控制在 10 个以内。大量详细版节点时（>30 个），可考虑懒加载（仅视口内节点构建控件）
- **QTextEdit 问题**：`QTextEdit` 通过 proxy 嵌入时可能有焦点和滚动条问题，改用 `QPlainTextEdit`
- **后向兼容**：无 `parameters` 字段的 config.json 完全不受影响，详细版将降级为普通方形版渲染
- **Dynamic options**（v1.1）：`dynamic_options` 字段预留但暂不实现，当前仅支持静态 `options`
- **布局持久化**：`canvas_layout.json` 已保存每个节点的 `style` 字段，样式切换后自动持久化
- **config.json 写冲突**：防抖参数变更 + 文件写锁机制防止 `polling_manager` 与画布编辑产生冲突

---

## ✅ 验收标准

- [ ] 节点 `config.json` 中声明 `parameters` 字段后，切换到详细版自动渲染对应控件
- [ ] 右键菜单显示三种样式选项：详细版 / 方形版 / 圆形版
- [ ] 详细版在画布上直接显示所有参数编辑控件（不弹 window/dialog）
- [ ] 支持全部 11 种参数类型（string/text/password/int/float/bool/enum/file/directory/color/range）
- [ ] 画布上修改参数后，`config.json` 文件即时写入新值
- [ ] 外部修改 `config.json` 后，画布控件同步刷新显示新值
- [ ] 三种样式互相切换不丢失已编辑的配置数据
- [ ] 无可访问性/诊断/PyLance 错误

---

**制定日期**：2026-06-10
