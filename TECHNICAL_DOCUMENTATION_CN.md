# BNOS (Bionic Neural Network Visual Orchestration Platform)
## 技术说明书

> 📖 English version: [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [核心组件详解](#3-核心组件详解)
   - 3.1 启动层组件
   - 3.2 进程管理层组件
   - 3.3 项目管理层组件
   - 3.4 UI组件
   - 3.5 工具组件
4. [数据流程](#4-数据流程)
5. [进程通信机制](#5-进程通信机制)
6. [节点生命周期管理](#6-节点生命周期管理)
   - 6.1 生命周期状态图
   - 6.2 状态检测机制
   - 6.3 孤儿进程处理
   - 6.4 进程树终止机制

---

## 1. 项目概述

BNOS 是一个基于 PyQt6 的神经网络可视化编排平台，提供节点的可视化编排、进程管理、实时监控等功能。

### 核心功能

| 功能模块 | 描述 |
|---------|------|
| 节点管理 | 节点的创建、启动、停止、删除 |
| 画布编排 | 可视化节点连线和数据流编排 |
| 进程监控 | 实时监控节点进程状态和资源使用 |
| 项目管理 | 项目的新建、打开、保存、导入导出 |
| 外部挂载 | 支持挂载外部节点到当前项目 |

### 技术栈

- **框架**: PyQt6 (Qt6 绑定)
- **语言**: Python 3.8+
- **进程通信**: QLocalSocket / QLocalServer
- **UI样式**: QSS (Qt Style Sheets)

---

## 2. 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     BNOS Console                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   启动层    │───▶│   UI层      │───▶│  业务层     │        │
│  │ launcher    │    │ main_window │    │ node_process│        │
│  │ bnos_console│    │ canvas_view │    │ ipc         │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                │
│         ▼                  ▼                  ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   子进程    │    │    面板     │    │   管理器    │        │
│  │ canvas_proc │    │ node_list   │    │ polling     │        │
│  │ panel_proc  │    │ node_monitor│    │ project     │        │
│  │ core_proc   │    │ resource    │    │ registry    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 进程架构

| 进程类型 | 描述 | 职责 |
|---------|------|------|
| 主进程 | BNOS Console | UI展示、用户交互、进程协调 |
| 画布进程 | canvas_process | 独立画布渲染、节点绘制 |
| 面板进程 | panel_process | 独立面板渲染、属性编辑 |
| 核心进程 | core_process | 后台业务处理、无UI |

---

## 3. 核心组件详解

### 3.1 启动层组件

#### 3.1.1 launcher.py

**职责**: 闪屏启动器，负责优雅地启动整个应用

**核心函数**:

| 函数 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `find_venv_python()` | 查找虚拟环境Python解释器 | 无 | `str` - Python路径 |
| `main()` | 主启动流程 | 无 | 无 |
| `_fallback_launch()` | 无tkinter时的降级启动 | 无 | 无 |
| `_progress()` | 更新进度文件 | `progress_file`: 进度文件路径 | 无 |

**工作流程**:
1. 显示 tkinter 闪屏（ASCII Logo + 进度条）
2. 查找虚拟环境 Python 解释器
3. 创建临时进度文件
4. 启动主程序 `bnos_console.py --progress=<file>`
5. 轮询读取进度文件，实时更新闪屏
6. 进度达到100%后关闭闪屏

---

#### 3.1.2 bnos_console.py

**职责**: 应用主入口，初始化Qt环境和主窗口

**核心函数**:

| 函数 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `_progress()` | 向启动器发送进度 | `progress_file`: 文件路径, `pct`: 百分比, `msg`: 消息 | 无 |
| `main()` | 应用主入口 | 无 | 无 |

**启动流程**:
1. 解析命令行参数（进度文件路径）
2. 初始化国际化
3. 初始化Qt应用
4. 创建主窗口
5. 加载项目
6. 进入事件循环

---

### 3.2 进程管理层组件

#### 3.2.1 node_process.py

**职责**: 节点进程生命周期管理（启动/停止/监控）

**核心函数**:

| 函数 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `start_node_process()` | 启动节点进程 | `node_info`: 节点信息字典 | `(bool, str)` - (成功, 错误消息) |
| `stop_node_process()` | 停止节点进程 | `node_info`: 节点信息字典, `force`: 是否强制 | `(bool, str)` |
| `detect_running_nodes()` | 检测后台运行的节点 | `nodes_data`: 节点数据 | `list` - [(节点名, PID)] |
| `check_running_processes()` | 检测节点进程状态 | `nodes_data`: 节点数据 | `list` - 状态变更列表 |
| `_find_node_processes()` | 扫描系统中属于节点的进程 | `node_path`: 节点路径 | `list` - PID列表 |
| `_kill_all_node_processes()` | 强制终止所有孤儿进程 | `node_path`: 节点路径 | 无 |
| `_write_pid()` | 写入PID文件 | `node_path`: 节点路径, `pid`: 进程ID | 无 |
| `_read_pid()` | 读取PID文件 | `node_path`: 节点路径 | `int` - PID或None |

**进程状态三态模型**:

| 状态 | 描述 | 判定条件 |
|------|------|----------|
| `running` | 运行中 | listener运行且有main子进程 |
| `idle` | 空闲 | listener运行但无main子进程 |
| `stopped` | 已停止 | 无Python进程运行 |

**PID文件管理**:
- 支持两种格式：`.pid`（标准）和 `node_python_<name>.pid`（命名）
- 启动时写入，停止时删除
- 进程扫描兜底机制处理PID文件丢失情况

---

#### 3.2.2 process_manager.py

**职责**: 管理UI子进程（画布、面板、核心业务）的生命周期

**核心类**:

| 类 | 功能 | 关键方法 |
|------|------|----------|
| `ManagedProcess` | 受管理的子进程 | `start()`, `stop()`, `restart()`, `_check_health()` |
| `ProcessManager` | 进程管理器 | `register()`, `start()`, `stop()`, `stop_all()` |

**健康检测机制**:
- 每2秒检查一次进程状态
- 进程崩溃时自动重启（最多5次）
- 支持崩溃信号通知

---

#### 3.2.3 ipc.py

**职责**: 跨进程通信（QLocalServer + QLocalSocket）

**核心类**:

| 类 | 角色 | 关键方法 |
|------|------|----------|
| `IPCServer` | 主进程服务端 | `start()`, `stop()`, `send()`, `broadcast()` |
| `IPCClient` | 子进程客户端 | `connect_to_server()`, `send()` |

**Action常量**:

| 常量 | 含义 |
|------|------|
| `A_ADD_NODE` | 添加节点到画布 |
| `A_REMOVE_NODE` | 从画布移除节点 |
| `A_UPDATE_STATUS` | 更新节点状态 |
| `A_CREATE_EDGE` | 创建连线 |
| `A_REMOVE_EDGE` | 删除连线 |
| `A_SYNC_DATA` | 同步数据 |
| `A_CLEAR_ALL` | 清空画布 |
| `A_WIN_SYNC` | 窗口几何同步 |

**Event常量**:

| 常量 | 含义 |
|------|------|
| `E_NODE_SELECTED` | 节点被选中 |
| `E_NODE_DBLCLICKED` | 节点被双击 |
| `E_EDGE_CREATED` | 连线已创建 |
| `E_EDGE_REMOVED` | 连线已删除 |

---

#### 3.2.4 polling_manager.py

**职责**: 统一轮询管理器，集中管理所有定时任务

**核心特性**:
- 单例模式
- 所有任务共享一个主定时器
- 支持不同轮询间隔的任务
- 提供统一的信号接口

**默认轮询任务**:

| 任务名 | 间隔(秒) | 回调函数 | 功能 |
|--------|----------|----------|------|
| `node_health` | 2 | `_poll_node_health()` | 节点进程健康检查 |
| `global_logs` | 2 | `_poll_global_logs()` | 全局日志检测 |
| `global_config` | 2 | `_poll_global_config()` | 全局配置检测 |
| `node_logs` | 2 | `_poll_node_logs()` | 节点日志检测 |
| `node_config` | 2 | `_poll_node_config()` | 节点配置检测 |
| `node_output` | 2 | `_poll_node_output()` | 节点输出检测 |
| `app_state` | 5 | `_poll_app_state()` | 应用状态检测 |

**信号定义**:

| 信号 | 参数 | 触发时机 |
|------|------|----------|
| `node_status_changed` | `(node_name, new_status)` | 节点状态变更 |
| `log_file_changed` | `(node_path, log_filename)` | 节点日志文件变化 |
| `global_log_changed` | `(log_file, content)` | 全局日志文件变化 |
| `config_file_changed` | `(node_path)` | 节点配置变化 |
| `global_config_changed` | `(config_file)` | 全局配置变化 |
| `output_json_changed` | `(node_path, content)` | 节点输出变化 |
| `app_state_changed` | `(state)` | 应用状态变化 |

---

### 3.3 项目管理层组件

#### 3.3.1 project_manager.py

**职责**: 项目管理（新建/打开/刷新项目，扫描并加载节点数据）

**核心函数**:

| 函数 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `project_new()` | 新建项目 | `main_window`: 主窗口实例 | 无 |
| `project_open()` | 打开项目 | `main_window`: 主窗口实例 | 无 |
| `project_refresh()` | 刷新节点列表 | `main_window`: 主窗口实例 | 无 |

**项目结构**:
```
project_dir/
├── nodes/           # 节点目录
│   ├── node1/       # 节点文件夹
│   │   ├── config.json
│   │   ├── listener.py
│   │   └── ...
│   └── node2/
├── node_registry.json  # 节点注册表
└── canvas_layout.json  # 画布布局
```

---

#### 3.3.2 node_registry.py

**职责**: 节点注册表组件，记录节点名称和路径

**核心类**: `NodeRegistry`

**方法**:

| 方法 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `load()` | 从文件加载注册表 | 无 | `bool` - 加载是否成功 |
| `save()` | 保存注册表到文件 | 无 | `bool` - 保存是否成功 |
| `register_node()` | 注册或更新节点 | `node_name`, `node_path`, `mount_root` | 无 |
| `unregister_node()` | 移除节点 | `node_name` | 无 |
| `sync_from_scan()` | 同步扫描结果 | `scan_results`: {name: path} | 无 |
| `get_active_nodes()` | 获取活跃节点 | 无 | `dict` - 节点信息 |
| `get_mounted_nodes()` | 获取挂载节点 | 无 | `dict` - 节点信息 |

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
    },
    "updated_at": "2025-01-01T00:00:00"
}
```

---

#### 3.3.3 external_node_manager.py

**职责**: 外部节点的挂载和卸载管理

**核心函数**:

| 函数 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `mount_node()` | 挂载外部节点 | `main_window`: 主窗口实例 | 无 |
| `unmount_node()` | 卸载外部节点 | `main_window`: 主窗口实例, `node_name`: 节点名 | 无 |

**挂载特性**:
- 外部节点存储在项目外部目录
- 通过注册表记录挂载关系
- 自动创建锁定组（橙色标识）

---

#### 3.3.4 json_node_starter.py

**职责**: 从JSON配置文件读取并启动节点

**核心类**: `JsonNodeStarter`

**方法**:

| 方法 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `load_config()` | 加载JSON配置 | `config_path`: 配置文件路径 | `(bool, str, list)` |
| `start_node()` | 启动单个节点 | `node_info`: 节点信息 | `(bool, str)` |
| `start_nodes_from_config()` | 从配置启动所有节点 | `config_path`: 配置文件路径 | `(dict, str)` |
| `start_nodes()` | 启动多个节点 | `nodes`: 节点列表 | `(dict, str)` |

**配置文件格式**:
```json
{
    "nodes": [
        {
            "name": "node_name",
            "path": "/path/to/node",
            "config": {}
        }
    ]
}
```

---

### 3.4 UI组件

#### 3.4.1 main_window.py

**职责**: 主窗口，包含完整界面布局和核心功能

**核心特性**:
- PS式布局（固定中心画布 + 左右停靠面板）
- 自定义标题栏（无边框窗口）
- CanvasHost作为中央控件
- 多画布Tab支持

**主要方法**:

| 方法 | 功能 |
|------|------|
| `init_ui()` | 初始化界面布局 |
| `new_project()` | 新建项目 |
| `open_project()` | 打开项目 |
| `refresh_nodes()` | 刷新节点列表 |
| `start_selected_node()` | 启动选中节点 |
| `stop_selected_node()` | 停止选中节点 |
| `show_toast()` | 显示Toast通知 |
| `closeEvent()` | 窗口关闭处理 |

**面板管理**:
- 节点列表面板（浮动/Dock版）
- 节点监测面板（浮动/Dock版）
- 资源监测面板（浮动/Dock版）

---

#### 3.4.2 canvas_view.py

**职责**: 节点画布（VueFlow风格的无限画布）

**核心特性**:
- 无限画布支持（5000x5000像素）
- 节点拖拽、锚点连线、贝塞尔曲线
- 缩放平移（滚轮/触控板/空格拖拽）
- 框选模式
- 画布中心坐标持久化

**交互模式**:
- **空格平移**: 按住空格进入快捷键模式，再按左键进入平移模式
- **框选**: 鼠标拖拽选择多个节点
- **连线**: 从输出锚点拖拽到输入锚点

---

#### 3.4.3 canvas_host.py

**职责**: 画布宿主窗口，管理多个画布Dock

**核心特性**:
- 空白缓冲层设计（启动时显示）
- 每个画布独立维护节点数据和连接
- 画布切换时自动同步数据

**方法**:

| 方法 | 功能 |
|------|------|
| `add_canvas_dock()` | 添加新画布Dock |
| `get_active_canvas()` | 获取当前活动画布 |
| `sync_canvas_data_to_main_window()` | 同步画布数据到主窗口 |
| `update_canvas_data_from_main_window()` | 从主窗口更新画布数据 |
| `save_all_layouts()` | 保存所有画布布局 |

---

### 3.5 工具组件

#### 3.5.1 app_config.py

**职责**: 应用配置管理，单例模式

**管理的配置项**:

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| `window_geometry` | 窗口几何信息 | `{x:100, y:100, width:1400, height:900}` |
| `splitter_sizes` | 分割器比例 | `[250, 1150]` |
| `last_project` | 最后打开的项目 | `None` |
| `language` | 语言设置 | `"cn"` |
| `panel_positions` | 面板位置 | 各面板坐标 |
| `panel_visibility` | 面板可见性 | 各面板状态 |

**方法**:
- `load()` - 加载配置
- `save()` - 保存配置
- `get(key, default)` - 获取配置项
- `set(key, value)` - 设置配置项

---

#### 3.5.2 logger.py

**职责**: 全局日志配置

**特性**:
- 双输出：控制台(INFO) + 文件(DEBUG)
- 日志格式：时间戳 + 级别 + 消息
- 文件保留完整调试信息

**用法**:
```python
from ui.core.logger import logger
logger.info("节点已启动")
logger.debug("调试信息")
logger.warning("警告信息")
logger.error("错误信息")
```

---

#### 3.5.3 shortcut_manager.py

**职责**: 全局快捷键管理

**默认快捷键**:

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+N` | 新建项目 |
| `Ctrl+O` | 打开项目 |
| `Ctrl+,` | 打开设置 |
| `Ctrl+R` | 重启应用 |
| `Ctrl+Q` | 退出应用 |
| `F5` | 刷新节点 |
| `Ctrl+Shift+O` | 挂载外部节点 |
| `Ctrl+Shift+S` | 启动节点 |
| `Ctrl+Shift+X` | 停止节点 |
| `Ctrl+Shift+M` | 节点监测 |
| `Ctrl+Shift+R` | 资源监测 |
| `Ctrl+T` | 新建画布标签 |

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
创建画布Dock（通过CanvasHost）
        │
        ▼
扫描nodes/目录加载节点
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
更新UI（画布+面板）
```

### 节点启动流程

```
用户点击"启动节点"
        │
        ▼
获取选中节点信息
        │
        ▼
检查节点状态（非running/idle）
        │
        ▼
清理残留孤儿进程
        │
        ▼
读取start.json配置
        │
        ▼
定位虚拟环境Python
        │
        ▼
启动listener.py进程
        │
        ▼
写入PID文件
        │
        ▼
更新节点状态为idle
        │
        ▼
更新UI显示
```

---

## 5. 进程通信机制

### IPC架构

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
| 进程扫描 | 最高 | 通过系统命令查找Python进程 |
| PID文件 | 次高 | 读取.pid文件获取PID |
| Process对象 | 次低 | 检查subprocess.Popen对象 |

### 孤儿进程处理

当PID文件丢失或进程异常退出时：
1. 通过`_find_node_processes()`扫描系统进程
2. 找到属于该节点的Python进程
3. 通过`_kill_all_node_processes()`强制终止
4. 更新节点状态为`stopped`

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
| 根目录 | 17 | 6,240 |
| ui/ 目录 | 77 | ~17,800 |
| tools/ 目录 | 7 | ~2,435 |
| tests/ 目录 | 3 | 100 |
| **总计** | **104** | **~26,575** |

### 根目录文件

| 文件 | 行数 | 说明 |
|------|------|------|
| `launcher.py` | 251 | 闪屏启动器 |
| `bnos_console.py` | 100 | 主入口 |
| `app_config.json` | 80 | 应用配置 |
| `canvas_layout.json` | 13 | 画布布局 |
| `color_settings.json` | 9 | 颜色设置 |
| `build_bnos.spec` | 47 | PyInstaller 打包配置 |
| `start_bnos_console.bat` | 78 | Windows 启动脚本 |
| `start_bnos_console.sh` | 153 | Linux/macOS 启动脚本 |
| `start_bnos_console.vbs` | 16 | 静默启动脚本 |
| `requirements.txt` | 16 | Python 依赖 |
| `README.md` | 812 | 英文 README |
| `README_CN.md` | 792 | 中文 README |
| `UPDATE_CN.md` | 1,798 | 中文更新日志 |
| `UPDATE_EN.md` | 844 | 英文更新日志 |
| `TECHNICAL_DOCUMENTATION.md` | 696 | 技术文档 |
| `DEVELOPMENT_GUIDELINES.md` | 364 | 开发规范 |
| `CODE_ANALYSIS_REPORT.md` | 163 | 代码分析报告 |
| `下一步计划.md` | 24 | 下一步计划 |

### ui/ 顶层

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | 4 | 模块入口 |
| `main_window.py` | 1,133 | 主窗口 |
| `canvas_widget.py` | 15 | 画布兼容层（Facade） |
| `app_config.json` | 19 | UI 层配置 |

### ui/canvas/ — 画布模块

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | 17 | 画布模块入口 |
| `canvas_view.py` | 935 | 画布主视图 |
| `canvas_layout.py` | 393 | 布局持久化 Mixin |
| `draw_layer.py` | 317 | 绘图层管理 |
| `graphic_items.py` | 299 | 图形项（5 种图形） |
| `draw_toolbar.py` | 204 | PS 风格绘图工具栏 |
| `canvas_colors.py` | 180 | 颜色管理 Mixin |
| `canvas_menus.py` | 170 | 右键菜单 Mixin |
| `canvas_batch_ops.py` | 166 | 批量操作 Mixin |
| `canvas_connections.py` | 162 | 连线管理 Mixin |
| `canvas_process.py` | 116 | 画布子进程入口 |
| `canvas_box_select.py` | 31 | 框选 Mixin |
| `CANVAS_SPLIT_REPORT.md` | 305 | 画布拆分报告 |

### ui/canvas/items/ — 画布图形项

| 文件 | 行数 | 说明 |
|------|------|------|
| `edge_item.py` | 587 | 连线项（直角直线+折叠点） |
| `node_item.py` | 352 | 节点容器项 |
| `node_style.py` | 314 | 节点样式系统（方形/圆形） |
| `anchor_item.py` | 76 | 锚点项（I/O 端口） |
| `__init__.py` | 15 | 图形项模块入口 |

### ui/core/ — 核心业务模块

| 文件 | 行数 | 说明 |
|------|------|------|
| `polling_manager.py` | 520 | 统一轮询管理器（单例） |
| `canvas_host.py` | 484 | 画布宿主窗口 |
| `node_process.py` | 484 | 节点进程生命周期管理 |
| `json_node_starter.py` | 329 | JSON 配置启动节点 |
| `connection_inferrer.py` | 257 | 连线 config.json 兜底校验 |
| `project_manager.py` | 233 | 项目管理 |
| `node_registry.py` | 242 | 节点注册表 |
| `file_operation_manager.py` | 216 | 文件操作管理器 |
| `packager.py` | 203 | 节点/项目打包导出 |
| `import_export_manager.py` | 198 | 导入导出管理器 |
| `strings_cn.json` | 540 | 中文语言包 |
| `strings_en.json` | 532 | 英文语言包 |
| `dark_title_bar.py` | 171 | 自定义深色标题栏 |
| `floating_panel.py` | 171 | 浮动面板基类 |
| `theme.py` | 68 | 深色 QSS 主题 |
| `bnos_dock.py` | 166 | Dock 组件 |
| `ipc.py` | 150 | 进程通信（QLocalSocket） |
| `dock_manager.py` | 142 | Dock 管理器 |
| `node_creation_worker.py` | 134 | 异步节点创建 Worker |
| `process_manager.py` | 128 | UI 子进程管理 |
| `external_node_manager.py` | 120 | 外部节点挂载管理 |
| `splash_screen.py` | 112 | PyQt6 启动闪屏 |
| `app_config.py` | 107 | 应用配置管理 |
| `window_state_manager.py` | 71 | 窗口状态管理器 |
| `core_process.py` | 72 | 核心业务后台进程 |
| `shortcut_manager.py` | 68 | 快捷键管理 |
| `i18n.py` | 61 | 国际化模块 |
| `logger.py` | 55 | 全局日志模块 |

### ui/core/toast/ — Toast 通知

| 文件 | 行数 | 说明 |
|------|------|------|
| `toast_notification.py` | 238 | Toast 通知组件 |

### ui/core/utils/ — 工具函数

| 文件 | 行数 | 说明 |
|------|------|------|
| `dialog_utils.py` | 814 | 统一对话框组件 |
| `file_utils.py` | 74 | 文件操作工具 |
| `log_viewer.py` | 33 | 日志查看器工具 |
| `__init__.py` | 1 | 空文件 |

### ui/dialogs/ — 对话框

| 文件 | 行数 | 说明 |
|------|------|------|
| `node_config_dialog.py` | 580 | 节点配置对话框 |
| `color_settings_dialog.py` | 443 | 颜色设置对话框 |
| `file_browser_dialog.py` | 347 | 文件浏览器对话框 |
| `settings_dialog.py` | 306 | 设置对话框 |
| `__init__.py` | 2 | 模块入口 |

### ui/panels/ — 面板模块

| 文件 | 行数 | 说明 |
|------|------|------|
| `node_list_panel.py` | 1,099 | 节点列表悬浮面板 |
| `node_list_dock.py` | 776 | 节点列表 Dock 面板 |
| `resource_monitor.py` | 508 | 资源监测悬浮面板 |
| `node_monitor.py` | 497 | 节点监测悬浮面板 |
| `node_expand_panel.py` | 447 | 节点展开面板 |
| `resource_monitor_dock.py` | 412 | 资源监测 Dock 面板 |
| `node_monitor_dock.py` | 371 | 节点监测 Dock 面板 |
| `node_group_manager.py` | 344 | 节点分组管理 |
| `property_panel.py` | 301 | 属性面板 |
| `node_list_drag.py` | 262 | 节点拖拽功能 |
| `node_list_context.py` | 248 | 右键菜单上下文 |
| `panel_process.py` | 83 | 面板子进程入口 |

### ui/menu/ — 菜单系统

| 文件 | 行数 | 说明 |
|------|------|------|
| `menu_manager.py` | 220 | 菜单栏管理器 |

### ui/creators/ — 节点创建器

| 文件 | 行数 | 说明 |
|------|------|------|
| `node_creator_manager.py` | 268 | 多语言节点创建管理器 |

### ui/icons/ — 图标系统

| 文件 | 行数 | 说明 |
|------|------|------|
| `codicon.py` | 708 | Codicon 图标管理器（597 图标） |
| `__init__.py` | 3 | 图标模块入口 |

### ui/docs/ — 文档

| 文件 | 行数 | 说明 |
|------|------|------|
| `TOAST_MODULE_README.md` | 185 | Toast 模块文档 |

### tools/ — 节点生成工具

| 文件 | 行数 | 说明 |
|------|------|------|
| `rust_create_node.py` | 1,155 | Rust 节点模板生成器 |
| `python_create_node.py` | 144 | Python 节点模板生成器 |
| `README_CN.md` | 480 | 工具中文说明 |
| `README.md` | 438 | 工具英文说明 |
| `Node_Generator_Guidelines_EN.md` | 204 | 新语言节点开发准则（EN） |
| `节点生成器开发准则.md` | 204 | 新语言节点开发准则（CN） |

### tests/ — 测试

| 文件 | 行数 | 说明 |
|------|------|------|
| `test_panel_process.py` | 34 | 面板进程测试 |
| `test_canvas_process.py` | 33 | 画布进程测试 |
| `test_core_process.py` | 33 | 核心进程测试 |