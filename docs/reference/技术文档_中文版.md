# BNOS (Bionic Neural Network Visual Orchestration Platform)
## 技术说明书

> 📖 English version: [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [核心组件详解](#3-核心组件详解)
   - 3.1 启动层
   - 3.2 主窗口层
   - 3.3 画布层
   - 3.4 核心服务层
   - 3.5 面板层
   - 3.6 项目管理层
   - 3.7 工具层
4. [数据流程](#4-数据流程)
5. [进程通信机制](#5-进程通信机制)
6. [节点生命周期管理](#6-节点生命周期管理)
   - 6.1 生命周期状态图
   - 6.2 状态检测机制
   - 6.3 孤儿进程处理
   - 6.4 进程树终止机制

---

## 1. 项目概述

BNOS 是一个基于 PySide6 的神经网络可视化编排平台，提供节点的可视化编排、进程管理、实时监控等功能。

### 核心功能

| 功能模块 | 描述 |
|---------|------|
| 节点管理 | 节点的创建、启动、停止、删除 |
| 画布编排 | 可视化节点连线和数据流编排 |
| 进程监控 | 实时监控节点进程状态和资源使用 |
| 项目管理 | 项目的新建、打开、保存、导入导出 |
| 外部挂载 | 支持挂载外部节点到当前项目 |
| 终端集成 | 嵌入式 PowerShell/CMD/Bash 终端 Dock |
| 历史回滚 | Photoshop 风格撤销/重做，Command 模式 |

### 技术栈

- **框架**: PySide6 (Qt6 绑定)
- **语言**: Python 3.12+
- **进程通信**: QLocalSocket / QLocalServer
- **UI 样式**: QSS (Qt Style Sheets)
- **架构模式**: Mixin + Registry + Command + EventBus

---

## 2. 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     BNOS Console                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   启动层    │───▶│   UI 层     │───▶│  业务层     │        │
│  │ bnos_console│    │ main_window │    │ node_process│        │
│  │             │    │ canvas_view │    │ ipc         │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                │
│         ▼                  ▼                  ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   终端      │    │    面板     │    │   管理器    │        │
│  │ terminal/   │    │ node_list   │    │ polling     │        │
│  │             │    │ node_monitor│    │ project     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 分层架构

| 层级 | 组件 | 描述 |
|-------|-----------|-------------|
| **UI 层** | `main_window/`、`canvas/`、`panels/`、`dialogs/` | 用户界面渲染与交互 |
| **核心服务层** | `core/`、`menu/`、`icons/` | EventBus、DI、进程管理、动作系统 |
| **数据层** | `nodes/`、`app_config.json`、`canvas_layout.json` | 持久化存储与运行时数据 |
| **工具层** | `tools/` | 节点模板生成器 |

---

## 3. 核心组件详解

### 3.1 启动层

#### 3.1.1 bnos_console.py

**职责**: 应用主入口，初始化 Qt 环境和主窗口

**核心函数**:

| 函数 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `_progress()` | 向启动器发送进度 | `progress_file`: 文件路径, `pct`: 百分比, `msg`: 消息 | 无 |
| `main()` | 应用主入口 | 无 | 无 |

**启动流程**:
1. 解析命令行参数（进度文件路径）
2. 初始化国际化
3. 初始化 Qt 应用
4. 创建主窗口
5. 加载项目
6. 进入事件循环

---

### 3.2 主窗口层

#### 3.2.1 ui/main_window/__main__.py

**职责**: 主窗口中心，整合 8 个 Mixin 模块

**Mixin 模块**:

| 文件 | Mixin 名称 | 职责 |
|------|-----------|--------------|
| `state.py` | `MainWindowStateMixin` | 窗口状态、节点数据、项目路径管理 |
| `lifecycle.py` | `MainWindowLifecycleMixin` | 初始化、关闭编排、保存/恢复 |
| `actions.py` | `MainWindowActionsMixin` | 动作绑定、工具栏、菜单设置 |
| `panel.py` | `MainWindowPanelMixin` | 浮动面板和 Dock 管理 |
| `ipc.py` | `MainWindowIPCMixin` | IPC 服务器设置、多实例处理 |
| `node.py` | `MainWindowNodeMixin` | 节点控制委托（启动/停止/重启） |
| `interaction.py` | `MainWindowInteractionMixin` | 快捷键、拖拽、窗口事件 |

**架构**: 每个 Mixin 聚焦单一职责，主类继承所有 Mixin，保持 `__main__.py` 在 ~500 行以内。

---

### 3.3 画布层

#### 3.3.1 画布架构

画布层采用 **View + Mixins + Items** 架构：

```
ui/canvas/
├── canvas_view.py          # 主控制器（QGraphicsView）
├── mixins/                 # 功能 Mixin
│   ├── canvas_layout.py       # 布局持久化
│   ├── canvas_connections.py  # 连线创建/管理
│   ├── canvas_menus.py        # 右键菜单
│   ├── canvas_batch_ops.py    # 批量启停/清空
│   ├── canvas_box_select.py   # 框选
│   ├── canvas_colors.py       # 颜色管理
│   ├── canvas_event_handlers.py # 鼠标/键盘事件
│   ├── canvas_node_manager.py # 节点增删改
│   ├── canvas_selection.py    # 选择逻辑
│   ├── canvas_background_renderer.py # 网格背景
│   └── controllers.py         # 保存/加载控制器
├── items/                  # 图形元素
│   ├── node_item.py
│   ├── edge_item.py
│   ├── anchor_item.py
│   ├── anchor_manager.py
│   ├── node_status_widget.py
│   └── styles/             # 样式注册表
│       ├── _base.py
│       └── detailed.py
├── drawing/                # 绘图层
│   ├── draw_layer.py
│   ├── draw_toolbar.py
│   └── graphic_items/      # 形状注册表
│       ├── _base.py
│       ├── rect.py
│       ├── arrow.py
│       └── text.py
└── parameter_widgets/      # 参数控件注册表
    ├── _base.py
    ├── string.py
    ├── int_widget.py
    └── ... (11 种类型)
```

#### 3.3.2 canvas_view.py

**类 `NodeCanvas(QGraphicsView)`**: 画布主容器，继承所有画布 Mixin。

**关键属性**:
- `self.nodes: dict[str, NodeItem]` → 节点名 → 节点图形项
- `self.edges: list[EdgeItem]` → 所有连线
- `self._save_timer: QTimer` → 自动保存防抖定时器（500ms）
- `self.canvas_width / canvas_height` → 逻辑画布尺寸

**关键方法**:
- `save_layout(project_path)` → 持久化到 `canvas_layout.json`
- `load_layout(project_path)` → 从 `canvas_layout.json` 恢复

#### 3.3.3 canvas_layout.py

**保存流程**:
1. 遍历 `self.nodes` → 写入 x/y/width/height/style/custom_colors
2. 遍历 `self.edges` → 写入 source/target/source_port/target_port
3. 保存视图状态（scale/scroll/center）
4. 原子写入到 `<project>/canvas_layout.json`

**加载流程**:
1. `_save_timer.stop()` — 防止加载时保存
2. 读取 `canvas_layout.json`
3. 遍历节点 → 创建/更新 NodeItem
4. 遍历连线 → 通过 AnchorManager 绑定到指定端口
5. `_validate_edge_anchor_binding()` — 修复失效引用
6. 恢复视图状态

#### 3.3.4 Items 模块

**NodeItem**: 节点图形容器，通过 StyleRegistry 支持 3 种样式
- **Rect**: 标准矩形，完整锚点
- **Dot**: 紧凑圆形，三层 z 轴架构
- **Detailed**: ComfyUI 风格，画布内嵌参数编辑控件

**EdgeItem**: 直角直线连线，带可拖拽折叠手柄
- 长按 + 拖拽创建折叠路径点
- 记录目标/源端口用于锚点重新绑定

**AnchorManager**: 管理每个节点的输入/输出锚点
- 多端口支持（来自 `config.json` 的 `input_ports`）
- Required 端口优先作为默认连接点
- 样式切换时自动迁移连线

---

### 3.4 核心服务层

#### 3.4.1 event_bus.py

**EventBus 单例**: 解耦的模块间通信

```python
event_bus.publish("node.status_changed", node_name="node_1", status="running")
event_bus.subscribe("node.status_changed", on_status_changed)
```

**常用事件**:
- `node.created` / `node.removed` / `node.status_changed`
- `project.opened` / `project.closed`
- `config.modified` / `canvas.layout_saved`

#### 3.4.2 di.py

**DIContainer**: 服务注册与解析

```python
container.register("event_bus", event_bus)
container.register("process_manager", process_manager)
event_bus = container.resolve("event_bus")
```

#### 3.4.3 actions/

**统一动作系统**: ~80 个动作，按类别组织

| 类别 | 文件 | 示例 |
|----------|-------|----------|
| 画布 | `builtin_canvas_actions.py` | 缩放、适应视图、重置视图、切换绘图 |
| 节点 | `builtin_node_actions.py` + `node/` | 启动、停止、重命名、删除、切换样式 |
| 项目 | `builtin_project_actions.py` | 新建项目、打开项目、刷新节点 |
| 视图 | `builtin_view_actions.py` | 切换面板、切换主题 |

**节点动作子包** (`actions/node/`):
- `_lifecycle.py`: 启动/停止/重启
- `_context_menu.py`: IDE 打开、终端、资源管理器
- `_batch.py`: 批量操作
- `_selection.py`: 选择/取消选择
- `_group.py`: 分组/取消分组
- `_style.py`: 样式切换

#### 3.4.4 polling_manager.py

**统一轮询管理器**: 集中式定时任务调度

| 任务名 | 间隔(秒) | 用途 |
|-----------|-------------|--------|
| `node_health` | 2 | 节点进程健康检查 |
| `global_logs` | 2 | 全局日志检测 |
| `global_config` | 2 | 全局配置检测 |
| `node_logs` | 2 | 节点日志检测 |
| `node_config` | 2 | 节点配置检测 |
| `node_output` | 2 | 节点输出检测 |
| `app_state` | 5 | 应用状态检测 |

**信号**: `node_status_changed`、`log_file_changed`、`config_file_changed`、`output_json_changed`

#### 3.4.5 process_manager.py & node_process.py

**ProcessManager**: UI 子进程生命周期（画布、面板、核心）
- 每 2 秒健康检查
- 崩溃时自动重启（最多 5 次）

**node_process.py**: 单个节点进程管理
- 三态模型: `running` | `idle` | `stopped`
- PID 文件持久化（`.pid`）
- 孤儿进程扫描与清理
- 跨会话恢复

#### 3.4.6 terminal/

**嵌入式终端 Dock**:
- `terminal_process.py`: QProcess 包装，ANSI 剥离
- `terminal_widget.py`: QTextEdit + 输入历史
- `terminal_dock.py`: 多标签终端 Dock（PowerShell/CMD/Bash）

**特性**: 实时 stdout/stderr、标签页、工作目录同步到当前项目

#### 3.4.7 commands/

**Command 模式历史系统**:
- `base.py`: `Command` 基类，含 `execute()` / `undo()`
- `history_manager.py`: 扁平命令列表 + `current_index` 指针
- `node_commands.py`: AddNodeCommand、RemoveNodeCommand、MoveNodeCommand
- `edge_commands.py`: AddEdgeCommand、RemoveEdgeCommand
- `compound_commands.py`: 多操作原子命令

**特性**: 撤销/重做/跳转到任意历史状态、精确的锚点恢复

#### 3.4.8 toast/

**Toast 通知系统**:
- `toast_notification.py`: 单个 Toast，带动画
- `toast_queue_manager.py`: FIFO 队列，最多同时显示 3 个，智能替换

---

### 3.5 面板层

| 面板 | 文件 | 模式 | 描述 |
|-------|-------|------|-------------|
| 节点列表 | `node_list_panel.py` + `node_list_dock.py` | 悬浮 + Dock | 树形视图，分组，拖拽，多选 |
| 节点监测 | `node_monitor.py` + `node_monitor_dock.py` | 悬浮 + Dock | 实时日志 |
| 资源监测 | `resource_monitor.py` + `resource_monitor_dock.py` | 悬浮 + Dock | 系统 CPU/内存监测 |
| 历史 | `history_panel.py` | 悬浮 | 可视化命令历史，点击跳转 |
| 属性 | `property_panel.py` | 对话框 | 配置编辑器、颜色设置 |
| 展开 | `node_expand_panel.py` | 面板 | output.json 查看/编辑 |
| 分组管理 | `node_group_manager.py` | 对话框 | 分组增删改查 |

**共享组件** (`panels/_shared/`):
- `node_log_sub_panel.py`: 通用日志显示控件
- `node_panel_sync_mixin.py`: 面板与画布同步逻辑
- `system_resource_collector.py`: 系统指标采集

---

### 3.6 项目管理层

#### 3.6.1 project_manager.py

**职责**: 项目新建/打开/刷新

**项目结构**:
```
project_dir/
├── nodes/              # 节点目录
│   ├── node1/
│   │   ├── config.json
│   │   ├── main.py
│   │   └── ...
│   └── node2/
├── node_registry.json  # 节点注册表
└── canvas_layout.json  # 画布布局
```

#### 3.6.2 node_registry.py

**NodeRegistry**: 带挂载来源的持久化节点索引

**数据结构**:
```json
{
    "nodes": {
        "node_name": {
            "path": "/absolute/path",
            "last_seen": "2025-01-01T00:00:00",
            "status": "active",
            "mount_root": "/mount/path"
        }
    }
}
```

#### 3.6.3 external_node_manager.py

- 通过引用挂载外部节点（不复制文件）
- 自动创建锁定组（🔒）
- 安全卸载保留源文件

#### 3.6.4 connection_inferrer.py

从 `config.json` 的 `listen_upper_file` 和 `port_mappings` 反推连线关系

---

### 3.7 工具层

| 组件 | 文件 | 描述 |
|-----------|------|-------------|
| 日志 | `logger.py` | 全局日志，轮转（控制台 INFO + 文件 DEBUG） |
| IDE 扫描 | `ide_scanner.py` | 四层检测：缓存 → config → PATH → 进程/文件系统扫描 |
| 配置解析 | `node_config_parser.py` | ParameterDef / InputPortDef / OutputPortDef 解析 |
| 验证器 | `validators.py` | 节点名和路径验证 |
| i18n | `i18n.py` | 中英双语资源 |
| 主题 | `theme.py` | 深色 QSS 主题 |
| 窗口状态 | `window_state_manager.py` | 几何和分隔条比例持久化 |
| 快捷键 | `shortcut_manager.py` | 全局键盘快捷键 |

---

## 4. 数据流程

### 项目打开流程

```
用户点击"打开项目"
        │
        ▼
选择项目目录
        │
        ▼
验证项目结构（nodes/ 或 canvas_layout.json）
        │
        ▼
创建画布 Dock（通过 CanvasHost）
        │
        ▼
扫描 nodes/ 目录加载节点
        │
        ▼
同步节点注册表
        │
        ▼
恢复挂载节点
        │
        ▼
检测后台运行的节点
        │
        ▼
更新 UI（画布+面板）
```

### 节点启动流程

```
用户点击"启动节点"
        │
        ▼
获取选中节点信息
        │
        ▼
检查节点状态（非 running/idle）
        │
        ▼
清理残留孤儿进程
        │
        ▼
读取 start.json 配置
        │
        ▼
定位虚拟环境 Python
        │
        ▼
启动 listener.py 进程
        │
        ▼
写入 PID 文件
        │
        ▼
更新节点状态为 idle
        │
        ▼
更新 UI 显示
```

---

## 5. 进程通信机制

### IPC 架构

```
主进程 (Server)
    │
    ├── 画布进程 (Client)
    │       └── 接收命令: 添加/删除节点、更新状态、同步数据
    │
    ├── 面板进程 (Client)
    │       └── 接收命令: 同步节点列表、属性更新
    │
    └── 核心进程 (Client)
            └── 接收命令: 后台业务处理
```

### 消息格式

```json
{
    "action": "canvas.add_node",
    "params": {
        "node_name": "my_node",
        "info": {...}
    },
    "request_id": "a1b2c3d4"
}
```

---

## 6. 节点生命周期管理

### 生命周期状态图

```
         ┌──────────┐
         │  stopped │
         └────┬─────┘
              │ start()
              ▼
         ┌──────────┐
         │   idle   │◄───────────────┐
         └────┬─────┘                │
              │ 执行任务              │ 任务完成
              ▼                      │
         ┌──────────┐                │
         │ running  │────────────────┘
         └────┬─────┘
              │ stop() / 崩溃
              ▼
         ┌──────────┐
         │  stopped │
         └──────────┘
```

### 状态检测机制

| 检测方式 | 优先级 | 说明 |
|----------|--------|------|
| 进程扫描 | 最高 | 通过系统命令查找 Python 进程 |
| PID 文件 | 次高 | 读取 .pid 文件获取 PID |
| Process 对象 | 次低 | 检查 subprocess.Popen 对象 |

### 孤儿进程处理

当 PID 文件丢失或进程异常退出时：
1. 通过 `_find_node_processes()` 扫描系统进程
2. 找到属于该节点的 Python 进程
3. 通过 `_kill_all_node_processes()` 强制终止
4. 更新节点状态为 `stopped`

### 进程树终止机制

为了彻底终止节点及其所有子进程（支持任意编程语言），实现了进程树追踪机制。

#### 核心函数

| 函数 | 功能 |
|------|------|
| `_get_process_tree(root_pid)` | 递归获取进程树中所有进程 PID |
| `_kill_process_tree(root_pid)` | 彻底终止进程树 |

#### 工作原理

```
进程树终止流程:
┌─────────────────────────────────────────────────────────┐
│ 1. 读取 PID 文件获取主进程 PID                            │
├─────────────────────────────────────────────────────────┤
│ 2. 调用 _get_process_tree() 递归查询进程树               │
│    - Windows: WMI 查询 Win32_Process.ParentProcessId    │
│    - Linux/Mac: pstree 或 ps 命令                       │
├─────────────────────────────────────────────────────────┤
│ 3. 调用 _kill_process_tree() 按顺序终止进程             │
│    - 子进程在前，根进程在后                              │
│    - 使用 taskkill /F (Windows) 或 SIGKILL (Linux)     │
├─────────────────────────────────────────────────────────┤
│ 4. 兜底：进程扫描清理残留孤儿进程                        │
└─────────────────────────────────────────────────────────┘
```

#### 跨平台实现

**Windows**：
```python
# 使用 WMI 查询进程树
Get-CimInstance Win32_Process | ForEach-Object {
    $_.ProcessId + '|' + $_.ParentProcessId
}
```

**Linux/Mac**：
```python
# 优先使用 pstree
pstree -p <root_pid>

# 回退到 ps 命令
ps -ef | grep <keyword>
```

#### 支持多语言

该机制不依赖于特定编程语言，通过操作系统级别的进程关系追踪：
- Python 节点
- Node.js 节点
- Java 节点
- C/C++ 节点
- 任意语言创建的子进程

#### 停止节点流程

```python
def stop_node_process(node_info):
    # 1. 获取 PID
    pid = process.pid if process else _read_pid(node_path)

    # 2. 使用进程树终止机制
    _kill_process_tree(pid)

    # 3. 兜底：进程扫描清理残留
    remaining = _find_node_processes(node_path)
    if remaining:
        _kill_all_node_processes(node_path)

    # 4. 删除 PID 文件，更新状态
    _delete_pid(node_path)
    node_info['status'] = 'stopped'
```

---

## 附录：文件结构与代码行数

### 项目总览

| 区域 | 文件数 | 总行数 |
|------|--------|--------|
| ui/main_window/ | 9 | 1,997 |
| ui/canvas/ | 49 | 7,604 |
| ui/core/ | 69 | 11,816 |
| ui/panels/ | 19 | 5,078 |
| ui/dialogs/ | 5 | 1,555 |
| ui/creators/ | 1 | 268 |
| ui/menu/ | 1 | 109 |
| ui/icons/ | 2 | 711 |
| tools/ | 2 | 1,304 |
| tests/ | 9 | 504 |
| **ui/ 总计** | **157** | **29,155** |

### 主窗口层

| 文件 | 行数 | 说明 |
|------|------|-------------|
| `__main__.py` | ~500 | 主窗口中心（8 个 Mixin） |
| `state.py` | ~300 | 状态管理 |
| `lifecycle.py` | ~280 | 生命周期与关闭 |
| `actions.py` | ~250 | 动作绑定 |
| `panel.py` | ~200 | 面板管理 |
| `ipc.py` | ~180 | IPC 通信 |
| `node.py` | ~160 | 节点控制委托 |
| `interaction.py` | ~127 | 用户交互 |

### 画布层

| 文件 | 行数 | 说明 |
|------|------|-------------|
| `canvas_view.py` | ~935 | 画布主视图控制器 |
| `mixins/canvas_layout.py` | ~593 | 布局持久化 |
| `mixins/canvas_connections.py` | ~280 | 连接管理 |
| `mixins/canvas_event_handlers.py` | ~400 | 事件处理 |
| `mixins/canvas_node_manager.py` | ~240 | 节点增删改 |
| `items/edge_item.py` | ~650 | 连线项（直角直线） |
| `items/node_item.py` | ~400 | 节点容器 |
| `items/anchor_manager.py` | ~350 | 锚点管理 |
| `drawing/draw_layer.py` | ~317 | 绘图层 |

### 核心服务层

| 文件 | 行数 | 说明 |
|------|------|-------------|
| `polling_manager.py` | ~520 | 统一轮询管理器 |
| `canvas_host.py` | ~550 | 画布宿主与停靠 |
| `node_process.py` | ~484 | 节点进程生命周期 |
| `actions/action_factory.py` | ~300 | 动作工厂 |
| `commands/history_manager.py` | ~250 | 历史回滚 |
| `terminal/terminal_dock.py` | ~224 | 终端 Dock |
| `terminal/terminal_process.py` | ~120 | 终端进程 |
| `toast/toast_queue_manager.py` | ~180 | Toast 队列 |
| `event_bus.py` | ~80 | 事件总线 |
| `di.py` | ~60 | DI 容器 |

---

*最后更新: 2026-06-17*
