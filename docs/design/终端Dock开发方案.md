# BNOS 终端 Dock 开发方案

> **文档版本**：v1.0  
> **创建日期**：2026-06-07  
> **适用版本**：BNOS v3.x  
> **状态**：待审核 → 已批准 → 进行中 → 已完成

---

## 📋 目录

1. [项目概述](#项目概述)
2. [现状分析](#现状分析)
3. [目标设计](#目标设计)
4. [架构方案](#架构方案)
5. [实施计划](#实施计划)
6. [详细设计](#详细设计)
7. [测试计划](#测试计划)
8. [风险评估](#风险评估)
9. [资源需求](#资源需求)

---

## 1. 项目概述

### 1.1 背景

BNOS 系统目前缺少内置的终端功能，用户需要打开项目时需要切换到外部终端，导致工作流断裂。随着项目已有完善的 Dock 系统（通过 `BnosDock` 和 `CanvasHost`，为集成终端提供了良好基础。

### 1.2 问题定义

| 问题 | 影响 | 严重程度 |
|-----|------|---------|
| 无内置终端 | 需切换外部终端 | ⭐⭐⭐ 高 |
| 工作流断裂 | 影响效率低 | ⭐⭐ 中 |
| 无法直接操作项目 | 开发体验差 | ⭐⭐ 中 |

### 1.3 项目目标

| 目标 | 量化指标 | 时间线 |
|-----|---------|--------|
| 支持多种终端类型 | PowerShell, Cmd, Bash | Phase 2 |
| 多标签页支持 | 多个并行终端 | Phase 3 |
| 工作目录同步 | 随项目自动切换 | Phase 2 |
| 完整终端历史 | 命令历史记录 | Phase 3 |

### 1.4 范围

**包含**：
- ✅ 终端 Dock 窗口（复用 BnosDock）
- ✅ 简单终端界面（QTextEdit + QProcess）
- ✅ 工作目录自动同步
- ✅ 多种终端类型选择

**不包含**：
- ❌ 完整的 IDE 级终端（如 VS Code 集成）
- ❌ 远程 SSH 支持
- ❌ 分屏终端

---

## 2. 现状分析

### 2.1 当前架构基础

```
┌─────────────────────────────────────────────────────────────┐
│                   BNOS Dock 系统                                │
├─────────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │  BnosDock      │  │  CanvasHost     │             │
│  │  (Dock基类)     │  │  (画布Dock管理) │             │
│  └──────────────────┘  └──────────────────┘             │
│           │                     │                        │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │  CanvasDock    │  │  ❓ TerminalDock │             │
│  │  (已实现)      │  │  (待开发)        │             │
│  └──────────────────┘  └──────────────────┘             │
│                                                           │
│  目标：集成终端到现有 Dock 系统！                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 已有基础组件

| 组件 | 位置 | 状态 |
|-----|------|------|
| `BnosDock` | `ui/core/bnos_dock.py` | ✅ 已实现 |
| `CanvasHost` | `ui/core/canvas_host.py` | ✅ 已实现 |
| i18n 系统 | `ui/core/i18n.py` | ✅ 已实现 |
| 深色主题 | 已集成 | ✅ 已实现 |
| Codicon 图标 | `ui/icons/codicon.py` | ✅ 已实现 |

---

## 3. 目标设计

### 3.1 目标架构

```
┌───────────────────────────────────────────────────────────────────────────┐
│                  目标架构：终端 Dock 集成到 CanvasHost                     │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                           主窗口                                      │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │                      CanvasHost (画布宿主)                       │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐ │ │  │
│  │  │  │  顶部停靠区：画布Dock (CanvasDock 1 | CanvasDock 2 | ...) │ │  │
│  │  │  ├─────────────────────────────────────────────────────────┤ │ │  │
│  │  │  │  ┌───────────────────────────────────────────────────┐ │ │ │
│  │  │  │  │  画布工作区                                  │ │ │ │
│  │  │  │  │  ┌───────────────────────────────────────────┐ │ │ │ │
│  │  │  │  │  │  当前画布节点/连线                         │ │ │ │ │
│  │  │  │  │  │  ...                                   │ │ │ │ │
│  │  │  │  │  └───────────────────────────────────────────┘ │ │ │ │
│  │  │  │  └───────────────────────────────────────────────────┘ │ │ │
│  │  │  ├─────────────────────────────────────────────────────────┤ │ │
│  │  │  │  底部停靠区：终端 Dock (TerminalDock)                  │ │ │
│  │  │  │  ┌─────────────────────────────────────────────────┐ │ │ │
│  │  │  │  │  工具栏： [+] 新终端  终端类型：▼               │ │ │ │
│  │  │  │  ├─────────────────────────────────────────────────┤ │ │ │
│  │  │  │  │  标签页：终端 1 | 终端 2 | +                  │ │ │ │
│  │  │  │  ├─────────────────────────────────────────────────┤ │ │ │
│  │  │  │  │  > cd project_dir                             │ │ │ │
│  │  │  │  │  > python script.py                          │ │ │ │
│  │  │  │  │  ... 输出 ...                               │ │ │ │
│  │  │  │  │  >                                         │ │ │ │
│  │  │  │  └─────────────────────────────────────────────────┘ │ │ │
│  │  │  └─────────────────────────────────────────────────────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  核心：将 TerminalDock 停靠在 CanvasHost 的底部区域！                        │
└───────────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心设计原则

| 原则 | 说明 |
|-----|------|
| **复用现有组件** | 基于 `BnosDock` 作为基础 |
| **渐进式开发** | 从简单到复杂 |
| **跨平台兼容** | Windows/Linux/macOS 支持 |
| **工作目录同步** | 随项目自动切换 |
| **i18n 支持** | 完整国际化 |

### 3.3 用户体验目标

- ✅ **一体化：无需离开 BNOS 即可操作终端
- ✅ **可预测性：用户知道如何使用
- ✅ **高效性**：快速打开/切换终端
- ✅ **可发现性**：易于发现功能

---

## 4. 架构方案

### 4.1 模块结构

```
ui/core/terminal/
├── __init__.py
├── terminal_dock.py              # 终端 Dock（核心）
├── terminal_widget.py         # 终端界面组件
├── terminal_process.py       # QProcess 封装
├── terminal_tab_widget.py        # 标签页管理
└── README.md                 # 使用文档

ui/core/canvas_host.py         #（集成到 CanvasHost 内部）
```

### 4.2 核心类设计

#### 4.2.0 持久化机制设计
终端 Dock 的持久化与其他面板一致，使用：
- `panel_visibility.terminal_dock` - 保存可见性状态
- `panel_positions.terminal_dock` - 保存位置（如果浮动）
- 在 CanvasHost 的初始化和关闭时处理状态

#### 4.2.1 TerminalProcess（终端进程封装）

```python
# ui/core/terminal/terminal_process.py
import subprocess
import platform
from PySide6.QtCore import QProcess, QObject, Signal

class TerminalProcess(QObject):
    """终端进程 - 封装 QProcess
    
    output_received = Signal(str)
    error_received = Signal(str)
    process_started = Signal()
    process_finished = Signal(int)
    
    def __init__(self, working_dir: str = None):
        super().__init__()
        self.process = QProcess()
        self.working_dir = working_dir
        
        # 连接信号
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.started.connect(self.process_started)
        self.process.finished.connect(self.process_finished)
    
    def start(self, terminal_type: str = "powershell"):
        """启动终端"""
        system = platform.system()
        
        if system == "Windows":
            if terminal_type == "powershell":
                self.process.start("powershell.exe")
            elif terminal_type == "cmd":
                self.process.start("cmd.exe")
        elif system == "Darwin":
            self.process.start("bash")
        else:
            self.process.start("bash")
        
        if self.working_dir:
            self.process.setWorkingDirectory(self.working_dir)
    
    def write(self, command: str):
        """写入命令到终端"""
        self.process.write((command + "\n").encode()
    
    def _on_stdout(self):
        """处理标准输出"""
        data = self.process.readAllStandardOutput().data().decode()
        self.output_received.emit(data)
    
    def _on_stderr(self):
        """处理标准错误"""
        data = self.process.readAllStandardError().data().decode()
        self.error_received.emit(data)
```

#### 4.2.2 TerminalWidget（终端界面）

```python
# ui/core/terminal/terminal_widget.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLineEdit, QSplitter
)
from PySide6.QtCore import Qt
from ui.core.i18n import t
from .terminal_process import TerminalProcess

class TerminalWidget(QWidget):
    """终端界面组件"""
    
    def __init__(self, working_dir: str = None, parent=None):
        super().__init__(parent)
        self.working_dir = working_dir
        self.process = TerminalProcess(working_dir)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        
        # 终端输出区域
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        
        # 终端输入区域
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(t("k_terminal_input_hint"))
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252526;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        
        layout.addWidget(self.output_edit)
        layout.addWidget(self.input_edit)
    
    def _connect_signals(self):
        """连接信号"""
        self.process.output_received.connect(self._on_output)
        self.process.error_received.connect(self._on_error)
        self.input_edit.returnPressed.connect(self._on_input)
    
    def start_terminal(self, terminal_type: str = "powershell"):
        """启动终端"""
        self.process.start(terminal_type)
    
    def _on_output(self, data: str):
        """处理输出"""
        self.output_edit.append(data)
    
    def _on_error(self, data: str):
        """处理错误"""
        self.output_edit.append(data)
    
    def _on_input(self):
        """处理输入"""
        command = self.input_edit.text()
        self.process.write(command)
        self.input_edit.clear()
```

#### 4.2.3 TerminalDock（终端 Dock）

```python
# ui/core/terminal/terminal_dock.py
from PySide6.QtWidgets import QToolBar, QComboBox
from ui.core.bnos_dock import BnosDock
from ui.core.i18n import t
from .terminal_widget import TerminalWidget
from ui.icons.codicon import get_icon

#### 4.2.4 AppConfig 默认配置更新

```python
# ui/core/app_config.py 中的默认配置更新（节选）
self.config = {
    "window_geometry": {
        "x": 100, "y": 100, "width": 1400, "height": 900,
        "maximized": False
    },
    "splitter_sizes": [250, 1150],
    "last_project": None,
    "canvas_view_state": {
        "scale": 1.0, "scroll_x": 0, "scroll_y": 0
    },
    "language": "cn",
    "process_mode": False,
    "panel_positions": {
        "node_list_floating": {"x": 10, "y": 100},
        "resource_monitor_floating": {"x": 10, "y": 100},
        "node_monitor_floating": {"x": 10, "y": 100},
        "node_list_dock": {"x": 0, "y": 0},
        "resource_monitor_dock": {"x": 0, "y": 0},
        "node_monitor_dock": {"x": 0, "y": 0},
        "terminal_dock": {"x": 0, "y": 0}  # ✅ 新增：终端 Dock 位置
    },
    "panel_visibility": {
        "node_list": False,
        "resource_monitor": False,
        "node_monitor": False,
        "node_list_dock": False,
        "resource_monitor_dock": False,
        "node_monitor_dock": False,
        "node_list_floating": False,
        "resource_monitor_floating": False,
        "node_monitor_floating": False,
        "terminal_dock": False  # ✅ 新增：终端 Dock 可见性
    }
}
```

class TerminalDock(BnosDock):
    """终端 Dock"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(t("k_terminal_dock_title"), parent)
        self.main_window = main_window
        self._canvas_host = parent  # parent 是 CanvasHost
        
        # 工具栏
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        # 终端类型选择
        self.terminal_type_combo = QComboBox()
        self.terminal_type_combo.addItems([
            t("k_terminal_type_powershell"),
            t("k_terminal_type_cmd"),
            t("k_terminal_type_bash")
        ])
        
        # 打开新终端按钮
        new_terminal_action = toolbar.addAction(
            get_icon("plus"), t("k_terminal_new")
        )
        new_terminal_action.triggered.connect(self._open_new_terminal)
        
        toolbar.addWidget(self.terminal_type_combo)
        
        # 设置工具栏到 Dock
        self.set_title_bar_widget(toolbar)
        
        # 第一个终端
        self._open_new_terminal()
    
    def _get_current_project_path(self):
        """获取当前活动画布的项目路径"""
        if self._canvas_host and hasattr(self._canvas_host, 'get_active_canvas'):
            active_canvas = self._canvas_host.get_active_canvas()
            if active_canvas and hasattr(self._canvas_host, 'get_canvas_data'):
                canvas_data = self._canvas_host.get_canvas_data(active_canvas)
                return canvas_data.get('project_path')
        # 回退到主窗口的项目路径
        if self.main_window and hasattr(self.main_window, 'current_project_path'):
            return self.main_window.current_project_path
        return None
    
    def _open_new_terminal(self):
        """打开新终端"""
        working_dir = self._get_current_project_path()
        
        terminal = TerminalWidget(working_dir, self)
        self.set_content_widget(terminal)
        
        terminal_type = self.terminal_type_combo.currentText()
        if terminal_type == t("k_terminal_type_powershell"):
            terminal.start_terminal("powershell")
        elif terminal_type == t("k_terminal_type_cmd"):
            terminal.start_terminal("cmd")
        else:
            terminal.start_terminal("bash")
```

---

## 5. 实施计划

### 5.1 阶段概览

| 阶段 | 时间 | 工作内容 | 状态 |
|-----|------|---------|------|
| Phase 1 | 第1周 | 基础终端界面 + 单终端 | ⏳ 待开始 |
| Phase 2 | 第2周 | 多终端类型 + 工作目录同步 | ⏳ 待开始 |
| Phase 3 | 第3周 | 多标签页 + 完善优化 | ⏳ 待开始 |

### 5.2 详细里程碑

#### Phase 1: 基础终端（第1周）

**目标**：建立基础框架，实现单终端功能

| 任务 | 子任务 | 负责人 | 预计工时 | 验收标准 |
|-----|-------|-------|---------|---------|
| T1.1 | 创建终端目录结构 | AI | 0.5h | 目录创建完成 |
| T1.2 | 实现 TerminalProcess | AI | 3h | 进程正常启动/停止 |
| T1.3 | 实现 TerminalWidget | AI | 4h | 输入输出正常 |
| T1.4 | 实现 TerminalDock | AI | 3h | 集成到 BnosDock |
| T1.5 | 添加 i18n 翻译 | AI | 1h | 中英文支持 |
| T1.6 | 集成到 CanvasHost | AI | 2h | 可在 CanvasHost 内部打开/关闭终端 Dock |
| T1.7 | 添加持久化能力 | AI | 1.5h | 终端 Dock 可见性状态保存/恢复 |
| T1.8 | 更新 AppConfig 默认配置 | AI | 0.5h | 添加 terminal_dock 配置项 |

**交付物**：
- ✅ 核心模块代码
- ✅ 基础终端功能
- ✅ i18n 翻译

---

#### Phase 2: 多终端类型（第2周）

**目标**：支持多种终端类型，工作目录同步

| 任务 | 子任务 | 负责人 | 预计工时 | 验收标准 |
|-----|-------|-------|---------|---------|
| T2.1 | 支持 PowerShell/Cmd/Bash | AI | 3h | 各终端正常工作 |
| T2.2 | 工作目录自动同步 | AI | 2h | 打开项目自动切换目录 |
| T2.3 | 终端类型选择 | AI | 2h | 用户可选择终端类型 |
| T2.4 | 跨平台测试 | AI | 2h | Windows/Linux/macOS 正常 |

**交付物**：
- ✅ 多终端类型支持
- ✅ 工作目录同步
- ✅ 跨平台测试报告

---

#### Phase 3: 多标签页与优化（第3周）

**目标**：多标签页，完善优化

| 任务 | 子任务 | 负责人 | 预计工时 | 验收标准 |
|-----|-------|-------|---------|---------|
| T3.1 | 多标签页支持 | AI | 4h | 多个终端并行 |
| T3.2 | 命令历史记录 | AI | 3h | 上下键浏览历史 |
| T3.3 | 完善文档 | AI | 2h | 文档完整清晰 |
| T3.4 | 最终测试 | AI | 3h | 全功能正常 |

**交付物**：
- ✅ 多标签页终端
- ✅ 完整测试报告
- ✅ 开发者文档

---

## 6. 详细设计

### 6.1 i18n 翻译示例

```json
// ui/core/strings_cn.json
{
  "k_terminal_dock_title": "终端",
  "k_terminal_new": "新终端",
  "k_terminal_type_powershell": "PowerShell",
  "k_terminal_type_cmd": "Cmd",
  "k_terminal_type_bash": "Bash",
  "k_terminal_input_hint": "输入命令..."
}
```

```json
// ui/core/strings_en.json
{
  "k_terminal_dock_title": "Terminal",
  "k_terminal_new": "New Terminal",
  "k_terminal_type_powershell": "PowerShell",
  "k_terminal_type_cmd": "Cmd",
  "k_terminal_type_bash": "Bash",
  "k_terminal_input_hint": "Enter command..."
}
```

### 6.2 CanvasHost 集成示例

```python
# ui/core/canvas_host.py 中的集成（节选）
from ui.core.terminal.terminal_dock import TerminalDock

class CanvasHost(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_window = parent
        
        # 画布Dock存储
        self._canvas_docks = []
        self._active_canvas = None
        
        # 画布数据存储
        self._canvas_data_map = {}
        
        # 空白缓冲层
        self._blank_placeholder = None
        
        # 初始化时显示空白缓冲层
        self._init_blank_placeholder()
        
        # 设置样式
        self._setup_styles()
        
        # ===== 终端 Dock 集成 =====
        self._init_terminal_dock()
        
        # ===== 恢复面板状态 =====
        self._restore_panel_state()
    
    def _init_terminal_dock(self):
        """初始化终端 Dock，停靠在底部区域"""
        self._terminal_dock = TerminalDock(self, self._parent_window)
        
        # 停靠在底部区域
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, 
            self._terminal_dock
        )
        
        # 连接可见性变化信号，用于持久化
        self._terminal_dock.visibility_changed.connect(
            self._on_terminal_dock_visibility_changed
        )
        
        # 默认先隐藏，用户可通过菜单或快捷键显示
        self._terminal_dock.hide()
    
    def _restore_panel_state(self):
        """从配置恢复终端 Dock 的状态"""
        if not self._parent_window:
            return
        
        visibility = self._parent_window.app_config.get('panel_visibility', {})
        show_terminal = visibility.get('terminal_dock', False)
        
        if show_terminal:
            self._terminal_dock.show()
    
    def _save_terminal_visibility_state(self, visible):
        """保存终端 Dock 的可见性状态"""
        if not self._parent_window:
            return
        
        visibility = self._parent_window.app_config.get('panel_visibility', {})
        visibility['terminal_dock'] = visible
        self._parent_window.app_config.set('panel_visibility', visibility)
        self._parent_window.app_config.save()
    
    def _on_terminal_dock_visibility_changed(self, visible):
        """终端 Dock 可见性变化处理"""
        self._save_terminal_visibility_state(visible)
    
    def toggle_terminal(self):
        """切换终端 Dock 的显示/隐藏"""
        if self._terminal_dock.isVisible():
            self._terminal_dock.hide()
        else:
            self._terminal_dock.show()
            # 显示时确保在第一个画布创建后（如果需要）
            if not self._canvas_docks:
                # 没有画布时也可以显示终端
                pass
```

---

## 7. 测试计划

### 7.1 测试策略

| 测试类型 | 目标 | 执行时机 |
|---------|------|---------|
| 单元测试 | 验证核心模块功能 | 每个阶段完成后 |
| 集成测试 | 验证终端功能集成 | 每个阶段完成后 |
| 跨平台测试 | 验证各平台终端 | Phase 2 结束 |

### 7.2 测试用例

| ID | 用例描述 | 预期结果 |
|----|---------|---------|
| UT-001 | TerminalProcess 启动/停止 | 进程正常启动/停止 |
| UT-002 | TerminalWidget 输入输出 | 输入命令，输出正确 |
| IT-001 | 终端 Dock 打开/关闭 | 正常显示/隐藏 |
| IT-002 | 终端类型切换 | 各终端正常工作 |
| IT-003 | 工作目录同步 | 打开项目自动切换目录 |
| IT-004 | 终端 Dock 持久化 | 重启应用后可见性状态恢复 |

---

## 8. 风险评估

| 风险 | 概率 | 影响 | 风险等级 | 缓解策略 |
|-----|------|------|---------|---------|
| 跨平台兼容性 | 中 | 中 | ⭐⭐ 中 | 充分测试各平台 |
| QProcess 异常 | 低 | 高 | ⭐⭐ 中 | 错误处理与日志 |
| 性能问题 | 低 | 低 | ⭐ 低 | 优化终端限制并发数量 |

---

## 9. 资源需求

### 9.1 人力资源

| 角色 | 工作量 | 说明 |
|-----|-------|------|
| 开发工程师 | 3周 | 全时参与 |

### 9.2 工具资源

| 工具 | 用途 |
|-----|------|
| Git | 版本控制 |
| Python/PySide6 | 开发环境 |
| VS Code/Trae AI | 代码编辑器 |

---

## 变更记录

| 版本 | 日期 | 作者 | 变更说明 |
|-----|------|------|---------|
| v1.0 | 2026-06-07 | Trae AI | 初始版本 |

---

**文档结束**

*此方案将根据实际进展持续更新和调整。*
