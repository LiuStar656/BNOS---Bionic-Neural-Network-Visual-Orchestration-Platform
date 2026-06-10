# Core 模块（核心基础设施）

> 核心模块：BNOS 的基础设施层，包含事件总线、依赖注入容器、进程管理、配置解析、国际化、通知系统等。
> 所有上层功能（画布、面板、对话框）都依赖本模块提供的基础设施。

---

## 📁 模块结构

```
ui/core/
├── event_bus.py           # 全局事件总线（EventBus）— 模块间通信
├── di.py                 # 依赖注入容器（DIContainer）— 服务注册与解析
├── shutdown_orchestrator.py # 优雅关闭协调器
├── polling_manager.py     # 统一轮询管理器（节点状态/资源监控）
├── process_manager.py     # 进程管理器（启动/停止/监控）
├── node_process.py        # 单个节点进程封装（QProcess）
├── core_process.py        # 核心进程（全局事件循环相关）
├── node_control_service.py # 节点控制服务（统一启动/停止接口）
├── project_manager.py     # 项目管理器（打开/保存项目）
├── file_operation_manager.py # 文件操作管理（异步删除/移动）
├── node_creation_worker.py # 节点创建工作线程（不阻塞 GUI）
├── external_node_manager.py # 外部节点管理（挂载/卸载）
├── node_registry.py       # 节点注册表（已挂载节点索引）
├── connection_inferrer.py # 连接推断器（从 config.json 自动推断连线）
├── node_config_parser.py  # 节点配置解析器（ParameterDef/InputPortDef）
├── json_node_starter.py   # JSON 节点启动器（支持 venv）
├── packager.py            # 项目打包/导出
├── import_export_manager.py # 导入/导出管理器
├── canvas_host.py         # CanvasHost（画布宿主窗口）
├── dock_manager.py        # Dock 管理器（窗口停靠）
├── panel_manager.py       # 面板管理器（浮动面板）
├── bnos_dock.py           # 基础 Dock 组件
├── floating_panel.py      # 浮动面板组件
├── window_state_manager.py # 窗口状态持久化
├── ide_scanner.py         # IDE 扫描器（VSCode / Trae IDE 自动检测）
├── app_config.py          # 应用配置（settings/主题）
├── theme.py               # 主题系统（深色/浅色切换）
├── i18n.py               # 国际化（中/英）
├── strings_cn.json       # 中文字符串资源
├── strings_en.json       # 英文字符串资源
├── logger.py             # 日志系统
├── shortcut_manager.py   # 快捷键管理
├── menu_manager.py       # 菜单管理器（Action 驱动）
├── splash_screen.py      # 启动动画
├── dark_title_bar.py     # 深色标题栏（无边框窗口适配）
├── ipc.py                # IPC 进程间通信
├── actions/              # Action 系统（50+ 个内建 Action）
│   ├── action_definition.py  # Action 基类定义
│   ├── action_registry.py    # Action 注册表
│   ├── action_factory.py     # Action 工厂
│   ├── builtin_canvas_actions.py  # 画布级 Action
│   ├── builtin_node_actions.py    # 节点级 Action
│   ├── builtin_project_actions.py # 项目级 Action
│   └── builtin_view_actions.py    # 视窗级 Action
├── terminal/             # 终端组件
│   ├── terminal_dock.py      # 终端 Dock 窗口
│   ├── terminal_widget.py    # 终端控件（QTextEdit 封装）
│   └── terminal_process.py   # 终端进程管理
├── toast/                # Toast 通知系统
│   ├── toast_notification.py  # 单个 Toast 组件
│   └── toast_queue_manager.py # 队列管理器（自动替换/过期）
└── utils/                # 工具集
    ├── dialog_utils.py       # 对话框工具
    ├── file_utils.py         # 文件操作工具
    └── log_viewer.py         # 日志查看器
```

---

## 🎯 核心架构组件

### 1. EventBus（事件总线）— event_bus.py

模块间解耦通信。替代直接函数调用，改为事件发布/订阅。

```python
# 发布事件
event_bus.publish("node.status_changed", node_name="node_1", status="running")

# 订阅事件
event_bus.subscribe("node.status_changed", on_status_changed)

# 常用事件
"node.created"          # 节点创建
"node.removed"          # 节点删除
"node.status_changed"   # 节点状态变更
"project.opened"        # 项目打开
"project.closed"        # 项目关闭
"config.modified"       # 节点配置修改
"canvas.layout_saved"   # 布局保存
```

### 2. DIContainer（依赖注入容器）— di.py

全局服务注册和解析，避免大量全局变量。

```python
# 注册
container.register("event_bus", event_bus)
container.register("process_manager", process_manager)

# 解析
event_bus = container.resolve("event_bus")
```

### 3. ShutdownOrchestrator（优雅关闭）— shutdown_orchestrator.py

应用关闭时按顺序释放资源：
1. 停止所有节点进程
2. 保存画布布局
3. 保存窗口状态
4. 停止定时器
5. 关闭外部进程

### 4. ProcessManager（进程管理）— process_manager.py

统一管理所有节点进程的生命周期。

```python
manager.start_node(node_name, node_path, config)
manager.stop_node(node_name)
manager.get_status(node_name) → "running" | "stopped" | "error"
```

**特性**：异步启动/停止（不阻塞 GUI）、进程树终止（杀死子进程）、自动重启（可选）。

### 5. PollingManager（轮询管理）— polling_manager.py

统一管理所有定时轮询任务，避免分散的 QTimer。

```python
# 注册轮询任务
polling_manager.register("node_status_check", 1000, check_all_nodes)

# 暂停/恢复
polling_manager.pause("node_status_check")
polling_manager.resume("node_status_check")
```

---

## 🔌 数据模型（node_config_parser.py）

### ParameterDef（参数定义）

```python
ParameterDef(
    name="max_tokens",      # 参数名（唯一标识）
    type="int",             # 类型: string | text | password | int | float | bool
                            #       | enum | file | directory | color | range
    label="最大 Token 数",   # UI 显示名
    default=2048,           # 默认值
    required=False,         # 是否必填
    min=0, max=32768,       # （仅数值类型）范围
    step=1,                 # （仅数值类型）步长
    options=[...],          # （仅 enum 类型）选项列表
)
```

### InputPortDef（输入端口定义）

```python
InputPortDef(
    name="prompt",          # 端口唯一标识
    label="Prompt 输入",    # UI 显示名
    type="string",          # 数据类型
    required=True,          # 是否必填连接
    description="...",      # 描述（tooltip）
    source="node",          # 【关键】数据源模式
                            #   - "node"  → 在画布上生成锚点，可连接上游
                            #   - "edit"  → 文本输入框（用户手填）
                            #   - "param" → 参数面板（与普通参数一致）
                            #   - None    → 兼容旧版，不生成锚点
)
```

### OutputPortDef（输出端口定义）

```python
OutputPortDef(
    name="default",         # 端口唯一标识
    label="输出",           # UI 显示名
    type="default",         # 数据类型
)
```

### 解析接口

```python
from ui.core.node_config_parser import NodeConfigParser

params = NodeConfigParser.parse(config)         # 参数列表
ports = NodeConfigParser.parse_input_ports(config) # 输入端口列表
out_ports = NodeConfigParser.parse_output_ports(config) # 输出端口列表
values = NodeConfigParser.extract_values(config) # 参数实际值 dict

has_params = NodeConfigParser.has_parameters(config)
has_ports = NodeConfigParser.has_input_ports(config)
port_names = NodeConfigParser.get_input_port_names(config)
```

---

## 🎨 Action 系统（actions/）

统一管理所有用户操作，支持菜单、工具栏、快捷键多种触发方式。

### Action 定义（action_definition.py）

```python
@ActionRegistry.register("node.start", category="node", label="启动节点",
                        icon="play", shortcut="Ctrl+R", enabled_when="node_selected")
class StartNodeAction(ActionDefinition):
    def execute(self, context):
        # context 包含: parent_window, canvas, selected_nodes, current_project...
        node = context.selected_nodes[0]
        context.process_manager.start_node(node.node_name, node.node_path)
```

### Action 注册表（action_registry.py）

```python
# 注册
ActionRegistry.register("id", MyAction)

# 查找
action = ActionRegistry.get("node.start")

# 批量获取
canvas_actions = ActionRegistry.get_by_category("canvas")
node_actions = ActionRegistry.get_by_category("node")
```

### Action 工厂（action_factory.py）

```python
# 生成 QAction（绑定到 QMenu / QToolBar）
qaction = ActionFactory.create_qaction("node.start", parent_widget, context)
menu.addAction(qaction)

# 批量生成菜单
ActionFactory.populate_menu(menu, ["node.start", "node.stop", "node.delete"], context)
```

---

## 🚀 启动流程（splash_screen.py + main_window.py）

```
1. QApplication 启动
2. SplashScreen 显示（加载动画 + 进度条）
3. DIContainer 初始化 + 注册核心服务
4. PollingManager 启动
5. 读取 app_config.json（主题、语言、窗口状态）
6. 加载 i18n 字符串
7. 初始化主题（dark_title_bar 应用无边框样式）
8. MainWindow 显示
9. 如有最近打开项目 → 自动打开
10. SplashScreen 关闭
```

---

## 🌐 国际化（i18n.py + strings_cn/en.json）

```python
from ui.core.i18n import t

label.setText(t("k_node_start"))  # 自动根据 app_config.language 选择
```

**字符串文件格式**（JSON）：
```json
{
  "k_node_start": "启动节点",
  "k_node_stop": "停止节点",
  "k_canvas_edge_exists": "该连线已存在",
  ...
}
```

新增字符串需同时修改 `strings_cn.json` 和 `strings_en.json`。

---

## 📬 Toast 通知（toast/）

轻量、非阻塞的消息提示系统。

```python
# 显示 Toast（自动排队）
ToastQueueManager.show("节点已启动", ToastType.SUCCESS, duration_ms=3000)
ToastQueueManager.show("配置已保存", ToastType.INFO)
ToastQueueManager.show("启动失败", ToastType.ERROR)

# 类型
ToastType.INFO      # 蓝色
ToastType.SUCCESS   # 绿色
ToastType.WARNING   # 黄色
ToastType.ERROR     # 红色
```

**特性**：队列管理（最多同时显示 N 条）、自动替换同类型消息、右上角定位、淡入淡出动画。

---

## 💻 终端组件（terminal/）

在底部 Dock 中显示节点进程的 stdout/stderr。

```python
# 嵌入到 CanvasHost 底部
terminal = TerminalDock("node_python_1", parent_widget)
terminal.write("已启动节点，等待上游输入...\n")
terminal.show()
```

**特性**：实时输出流、自动滚动、ANSI 颜色支持、可停靠/浮动切换。

---

## 🔍 IDE 扫描器（ide_scanner.py）

自动检测系统中安装的 IDE，供节点配置对话框使用。

```python
# 检测 VSCode / Trae IDE
ide_paths = IDEScanner.scan_all()
# → {"vscode": "/usr/bin/code", "trae": "/opt/Trae/trae"}

# 四层检测链路
# 1. 内存缓存（本次会话已检测过）
# 2. app_config.json 中的 user_ide_path
# 3. PATH 环境变量
# 4. 进程列表扫描 / 常见安装路径探测（跨平台）
```

---

## 🏗️ 项目管理（project_manager.py）

```python
# 打开项目
project_manager.open_project(project_dir)
# → 读取 project.json
# → 扫描 nodes/ 目录
# → 触发 "project.opened" 事件
# → canvas.load_layout(project_dir)

# 新建项目
project_manager.create_project(parent_dir, project_name)
# → 创建目录结构
# → 写入初始配置

# 最近项目
recent = project_manager.get_recent_projects()
```

---

## 🔄 ConnectionInferrer（连接推断）

根据节点 config.json 中的 `listen_upper_file` 和 `port_mappings`，自动推断节点之间的连线。

```python
inferrer = ConnectionInferrer(project_path, parent_window.nodes_data)
edges = inferrer.infer_all_edges()
# → [{"source": "node_2", "target": "node_1", "target_port": "prompt"}, ...]
```

用于：
- 项目首次打开（无 canvas_layout.json 时）
- 批量恢复连线（节点文件夹直接拖入后）

---

## 📦 打包与导出（packager.py + import_export_manager.py）

```python
# 导出项目包
packager.export_project(project_path, output_path)
# → <project_name>.bnos（含所有节点 + 布局 + 资源）

# 导入项目包
packager.import_project(bnos_path, target_dir)
# → 解压到目标目录，自动修正路径引用
```

---

## 🎨 主题系统（theme.py + dark_title_bar.py）

```json
// app_config.json
{
  "theme": "dark",        // dark | light
  "accent_color": "#0078D4",
  "canvas_bg": "#1e1e1e",
  "canvas_edge_color": "#4A90E2",
  "canvas_edge_width": 2.5
}
```

**特性**：动态切换（无需重启）、颜色配置持久化、Windows 11 无边框暗色标题栏。

---

## ⚠️ 关键约束

1. **所有 UI 操作必须在主线程**：后台线程（如 PollingManager）需要更新 UI 时，使用信号/槽或 `QMetaObject.invokeMethod`
2. **节点进程不阻塞 GUI**：`node_process.py` 使用 QProcess，start/stop 均为异步
3. **config.json 是权威数据源**：所有配置修改必须写回 `nodes/<name>/config.json`，画布和面板都是"视图"
4. **canvas_layout.json 是布局快照**：只记录节点位置、连线关系，不包含业务数据（业务数据在 config.json）
5. **Action 系统是单向数据流**：菜单 → Action.execute(context) → 事件总线 → 各模块响应，禁止在 Action 中直接修改其他模块的内部状态

---

## 📖 相关文档

- [画布模块](../canvas/README.md)
- [画布项模块](../canvas/items/README.md)
- [Toast 模块详细设计](../docs/TOAST_MODULE_README.md)
- [Multi-Anchor 重构计划](../docs/MULTI_ANCHOR_REFACTOR_PLAN.md)
- [更新日志](../../docs/changelogs/README.md)
