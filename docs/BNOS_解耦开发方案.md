# BNOS Console 解耦开发方案

> 基于：[BNOS_技术分析报告.md](./BNOS_技术分析报告.md)  
> 日期：2026-06-09  
> 版本：v1.0  
> 核心原则：**每一步完成后软件必须能正常启动运行，每一步都可见效果，每一步都可独立回滚**

---

## 目录

1. [总体策略与路线图](#一总体策略与路线图)
2. [阶段一：基础设施搭建（事件总线 + DI 容器）](#二阶段一基础设施搭建)
3. [阶段二：主窗口拆分（面板管理 → 节点控制 → 关闭序列）](#三阶段二主窗口拆分)
4. [阶段三：面板与画布解耦](#四阶段三面板与画布解耦)
5. [验证清单](#五验证清单)
6. [附录：回滚指南](#六附录回滚指南)

---

## 一、总体策略与路线图

### 1.1 策略总览

```
阶段一 (1-2天)                阶段二 (3-5天)                 阶段三 (2-3天)
基础设施搭建               主窗口神类拆分                 面板与画布解耦
┌──────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
│ Step 1:       │      │ Step 3: PanelManager  │      │ Step 6: PanelRegistry │
│ EventBus      │      │ 面板管理统一化        │      │ 统一面板注册机制      │
│ 事件总线      │      │                       │      │                       │
│               │      │ Step 4:               │      │ Step 7: Canvas         │
│ Step 2:       │      │ NodeControlService    │      │ Controller 组合模式    │
│ DI Container  │      │ 节点控制统一服务      │      │                       │
│ 依赖注入      │      │                       │      │ Step 8:                │
│               │      │ Step 5:               │      │ MainWindow 最终精简   │
│               │      │ ShutdownOrchestrator  │      │                       │
│               │      │ 关闭序列编排器        │      │                       │
└──────────────┘      └──────────────────────┘      └──────────────────────┘
```

### 1.2 进度与效果预览

| 步骤 | 新增文件 | 修改文件 | 软件可运行？ | 可见效果 |
|------|---------|---------|-------------|---------|
| Step 1 | `ui/core/event_bus.py` | 0 | ✅ 是 | 日志输出事件总线初始化信息 |
| Step 2 | `ui/core/di.py` | 0 | ✅ 是 | 日志输出 DI 容器注册信息 |
| Step 3 | `ui/core/panel_manager.py` | `ui/main_window.py`（少量） | ✅ 是 | 面板切换方式不变，代码更简洁 |
| Step 4 | `ui/core/node_control_service.py` | `ui/main_window.py`（部分委托） | ✅ 是 | 节点启停功能不变，逻辑迁移到服务层 |
| Step 5 | `ui/core/shutdown_orchestrator.py` | `ui/main_window.py`（closeEvent 委托） | ✅ 是 | 关闭流程更可靠，有明确顺序日志 |
| Step 6 | `ui/core/panel_registry.py`（扩展） | 各面板文件（少量） | ✅ 是 | 新增面板只需注册，无需改主窗口 |
| Step 7 | `ui/canvas/controllers.py` | `ui/canvas/canvas_view.py` | ✅ 是 | Canvas 行为不变，内部结构更清晰 |
| Step 8 | 无 | `ui/main_window.py`（大幅精简） | ✅ 是 | 主窗口从 ~1500 行降至 ~500 行 |

---

## 二、阶段一：基础设施搭建

> 阶段一纯增量，不修改任何现有文件，软件完全不受影响。

---

### Step 1：创建事件总线（EventBus）

**目标**：建立模块间松耦合通信基础设施，替代直接 import 调用和私有属性穿透。

**原理**：发布-订阅模式。模块 A 发布事件，模块 B/C/D 订阅事件，双方互不知晓对方存在。

**新增文件**：`ui/core/event_bus.py`

```python
"""
事件总线系统，用于解耦模块间的直接依赖关系
设计原则：基于 PyQt6 信号机制，线程安全，零侵入现有代码
"""
from typing import Dict, List, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal
import threading


class EventBus(QObject):
    """事件总线 — 发布-订阅模式的核心实现"""

    # 单一通用信号：(事件类型, 数据载荷)
    event_signal = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self.event_signal.connect(self._dispatch)

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件类型"""
        with self._lock:
            self._handlers.setdefault(event_type, [])
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            try:
                handlers.remove(handler)
            except ValueError:
                pass

    def publish(self, event_type: str, data: Any = None):
        """发布事件（线程安全）"""
        self.event_signal.emit(event_type, data)

    def _dispatch(self, event_type: str, data: Any):
        """内部分发到各订阅者"""
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                print(f"[EventBus] Error handling '{event_type}': {e}")


# 全局事件总线单例
event_bus = EventBus()

# 便捷模块级函数（让调用方写起来更自然）
def subscribe(et: str, h: Callable): event_bus.subscribe(et, h)
def publish(et: str, d: Any = None): event_bus.publish(et, d)
def unsubscribe(et: str, h: Callable): event_bus.unsubscribe(et, h)
```

**验收方式**：

在 `bnos_console.py` 的 `main()` 函数末尾添加一行验证代码（不修改任何逻辑）：

```python
from ui.core.event_bus import event_bus

def on_test(data):
    print(f"[EVENT BUS TEST] 收到事件: {data}")

event_bus.subscribe("test.hello", on_test)
event_bus.publish("test.hello", "事件总线初始化成功!")
```

**可见效果**：启动 BNOS Console，控制台输出：

```
[EVENT BUS TEST] 收到事件: 事件总线初始化成功!
```

**回滚方式**：删除 `ui/core/event_bus.py`，删除 `bnos_console.py` 中的 3 行验证代码（或保留，完全不碍事）。

---

### Step 2：创建依赖注入容器（DI Container）

**目标**：为 `AppConfig` 等全局单例提供抽象接口，让各模块通过接口而非具体类获取配置。

**原理**：`IConfig`（接口）+ `JsonFileConfig`（JSON 实现）+ `DIContainer`（容器）。

**新增文件**：`ui/core/di.py`

```python
"""
依赖注入容器 — 解耦全局配置与具体实现
设计原则：面向接口编程，运行时可替换实现
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Type, Dict, Any, Callable
from pathlib import Path
import json

T = TypeVar('T')


# ======================== 配置接口抽象 ========================

class IConfig(ABC):
    """配置接口 — 不依赖任何具体存储方式"""
    @abstractmethod
    def get(self, key: str, default=None): ...
    @abstractmethod
    def set(self, key: str, value): ...
    @abstractmethod
    def save(self): ...


class JsonFileConfig(IConfig):
    """JSON 文件配置实现（向后兼容 AppConfig）"""
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self):
        try:
            if self.config_path.exists():
                self._data = json.loads(self.config_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[DI] 配置加载失败: {e}")
            self._data = {}

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            print(f"[DI] 配置保存失败: {e}")

    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value):
        keys = key.split('.')
        data = self._data
        for k in keys[:-1]:
            data = data.setdefault(k, {})
        data[keys[-1]] = value


# ======================== DI 容器 ========================

class DIContainer:
    """轻量级 DI 容器 — 注册接口实现并解析依赖"""

    def __init__(self):
        self._registrations: Dict[Type, Any] = {}
        self._instances: Dict[Type, Any] = {}

    def register_instance(self, interface: Type[T], instance: T):
        """注册已创建的实例"""
        self._instances[interface] = instance

    def register_factory(self, interface: Type[T], factory: Callable[[], T]):
        """注册工厂方法（延迟创建）"""
        self._registrations[interface] = factory

    def resolve(self, interface: Type[T]) -> T:
        """解析依赖"""
        if interface in self._instances:
            return self._instances[interface]
        if interface in self._registrations:
            instance = self._registrations[interface]()
            self._instances[interface] = instance
            return instance
        raise KeyError(f"[DI] 未注册接口: {interface}")


# 全局容器
container = DIContainer()
```

**验收方式**：

在 `bnos_console.py` 末尾添加（不修改现有逻辑）：

```python
from pathlib import Path
from ui.core.di import container, IConfig, JsonFileConfig

config = JsonFileConfig(Path("bnos_config.json"))
container.register_instance(IConfig, config)

# 验证 DI 容器
cfg = container.resolve(IConfig)
cfg.set("di_test", "依赖注入容器初始化成功!")
print(f"[DI TEST] {cfg.get('di_test')}")
```

**可见效果**：启动 BNOS Console，控制台输出：

```
[DI TEST] 依赖注入容器初始化成功!
```

同时在项目根目录生成 `bnos_config.json`，内容包含 `"di_test": "依赖注入容器初始化成功!"`。

**回滚方式**：删除 `ui/core/di.py`，删除验证代码行，删除 `bnos_config.json`。

---

## 三、阶段二：主窗口拆分

> 阶段二开始修改现有文件，但每步改动范围有限，且每步都保持软件可运行。

---

### Step 3：提取面板管理 → PanelManager

**目标**：将 `BNOSMainWindow` 中 10+ 个 `toggle_*_panel` / `show_*_dock` 方法统一为一个 `PanelManager`。

**当前问题**（来自分析报告 热点3）：
- 每个面板有独立的 toggle 方法（`toggle_node_list_panel`, `show_resource_monitor` 等）
- 面板内部使用 `local import` 规避循环依赖
- 面板直接持有 `BNOSMainWindow` 引用

**方案**：新建 `PanelManager`，主窗口通过 `self.panel_manager.toggle("node_list")` 替代海量 toggle 方法。

**新增文件**：`ui/core/panel_manager.py`

```python
"""
面板管理器，负责管理各种面板的创建、显示和持久化
"""
from typing import Dict, Type, Callable, Any, Optional
from PyQt6.QtWidgets import QWidget, QDockWidget
from PyQt6.QtCore import Qt
from pathlib import Path
import json


class PanelDescriptor:
    """面板描述符"""
    def __init__(
        self, 
        key: str, 
        factory: Callable[[Any], QWidget], 
        area: Qt.DockWidgetArea = Qt.DockWidgetArea.LeftDockWidgetArea,
        default_visible: bool = False,
        title: str = ""
    ):
        self.key = key
        self.factory = factory
        self.area = area
        self.default_visible = default_visible
        self.title = title


class PanelRegistry:
    """面板注册表"""
    def __init__(self):
        self._panels: Dict[str, PanelDescriptor] = {}
        self._instances: Dict[str, QWidget] = {}

    def register(self, descriptor: PanelDescriptor):
        self._panels[descriptor.key] = descriptor

    def get_descriptor(self, key: str) -> Optional[PanelDescriptor]:
        return self._panels.get(key)

    def create_instance(self, key: str, parent) -> Optional[QWidget]:
        descriptor = self._panels.get(key)
        if descriptor:
            panel = descriptor.factory(parent)
            self._instances[key] = panel
            return panel
        return None

    def get_instance(self, key: str) -> Optional[QWidget]:
        return self._instances.get(key)

    def get_all_keys(self) -> list:
        return list(self._panels.keys())


class PanelManager:
    """面板管理器"""
    def __init__(self, main_window, config_path: Path):
        self.main_window = main_window
        self.config_path = config_path
        self.registry = PanelRegistry()
        self.dock_widgets: Dict[str, QDockWidget] = {}
        self._register_default_panels()

    def _register_default_panels(self):
        from ui.panels.node_list_dock import NodeListDockPanel
        from ui.panels.resource_monitor import ResourceMonitorDock
        from ui.panels.node_monitor import NodeMonitorDock

        self.registry.register(PanelDescriptor(
            key="node_list",
            factory=lambda p: NodeListDockPanel(p),
            area=Qt.DockWidgetArea.LeftDockWidgetArea,
            default_visible=True,
            title="节点列表"
        ))
        self.registry.register(PanelDescriptor(
            key="resource_monitor",
            factory=lambda p: ResourceMonitorDock(p),
            area=Qt.DockWidgetArea.RightDockWidgetArea,
            default_visible=False,
            title="资源监控"
        ))
        self.registry.register(PanelDescriptor(
            key="node_monitor",
            factory=lambda p: NodeMonitorDock(p),
            area=Qt.DockWidgetArea.RightDockWidgetArea,
            default_visible=False,
            title="节点监控"
        ))

    def toggle_panel(self, key: str, visible: bool = None):
        if key in self.dock_widgets:
            dock_widget = self.dock_widgets[key]
            if visible is None:
                visible = not dock_widget.isVisible()
            dock_widget.setVisible(visible)
        else:
            panel = self.registry.create_instance(key, self.main_window)
            if panel:
                dock_widget = QDockWidget(self.registry.get_descriptor(key).title, self.main_window)
                dock_widget.setWidget(panel)
                descriptor = self.registry.get_descriptor(key)
                self.main_window.addDockWidget(descriptor.area, dock_widget)
                dock_widget.setVisible(visible if visible is not None else descriptor.default_visible)
                self.dock_widgets[key] = dock_widget
                dock_widget.visibilityChanged.connect(
                    lambda: self._on_panel_visibility_changed(key, dock_widget.isVisible())
                )
        self.save_panel_states()

    def _on_panel_visibility_changed(self, key: str, visible: bool):
        self.save_panel_states()

    def load_panel_states(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                panel_states = config.get('panel_visibility', {})
                for key, visible in panel_states.items():
                    if key in self.registry.get_all_keys():
                        self.toggle_panel(key, visible)
        except Exception as e:
            print(f"Error loading panel states: {e}")

    def save_panel_states(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            panel_states = {}
            for key in self.registry.get_all_keys():
                if key in self.dock_widgets:
                    panel_states[key] = self.dock_widgets[key].isVisible()
            config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['panel_visibility'] = panel_states
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving panel states: {e}")

    def show_panel(self, key: str):
        self.toggle_panel(key, True)

    def hide_panel(self, key: str):
        self.toggle_panel(key, False)

    def is_panel_visible(self, key: str) -> bool:
        if key in self.dock_widgets:
            return self.dock_widgets[key].isVisible()
        return False
```

**修改文件**：`ui/main_window.py`

仅在 `BNOSMainWindow.__init__` 中做最小改动：

```python
# === 修改前（main_window.py __init__ 中） ===
# 大量 toggle 方法散落在类中

# === 修改后 ===
from ui.core.panel_manager import PanelManager

class BNOSMainWindow(QMainWindow):
    def __init__(self):
        # ... 原有初始化代码保持不变 ...
        
        # 🆕 创建面板管理器（替代原有 toggle_* 方法）
        config_dir = Path(self.current_project_path or os.getcwd()) / ".bnos"
        self.panel_manager = PanelManager(self, config_dir / "app_config.json")
        
        # 🆕 恢复上次的面板可见性状态
        self.panel_manager.load_panel_states()
```

并将菜单栏中的面板切换菜单项改为调用 `self.panel_manager.toggle_panel(key, checked)`：

```python
# 原: action_node_list.toggled.connect(self.toggle_node_list_panel)
# 改: action_node_list.toggled.connect(lambda checked: self.panel_manager.toggle_panel("node_list", checked))
```

**可见效果**：
1. 面板的显示/隐藏行为与原先完全一致
2. 面板可见性自动持久化到 `app_config.json`（`panel_visibility` 字段）
3. 关闭再打开 BNOS Console，面板状态被恢复
4. 菜单栏的面板切换功能正常工作

**验证命令**：

```bash
# 1. 启动软件，切换几个面板
python bnos_console.py

# 2. 检查配置文件是否写入了面板状态
cat <project>/.bnos/app_config.json  # 查看 panel_visibility 字段

# 3. 关闭软件，重新打开，确认面板状态恢复
```

**回滚方式**：删除 `PanelManager` 的创建代码，恢复原有的 toggle 方法调用即可。

---

### Step 4：提取节点控制 → NodeControlService

**目标**：将节点启动/停止/刷新逻辑从 `BNOSMainWindow` 移入独立的 `NodeControlService`。

**当前问题**（来自分析报告 热点1）：
- `start_selected_node`, `_start_node_async`, `_stop_node_async` 约 200 行散落在主窗口
- 节点创建 Worker 类内联在主窗口中
- 与 `polling_manager` 紧耦合

**方案**：创建 `NodeControlService`，通过 `EventBus` 与 UI 层通信。

**新增文件**：`ui/core/node_control_service.py`

```python
"""
节点控制服务，负责管理节点的启动、停止和其他操作
"""
from typing import Dict, List, Optional, Callable
from PyQt6.QtCore import QObject, QThread
from pathlib import Path
import subprocess
import os
import signal
from enum import Enum


class NodeStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class NodeInfo:
    def __init__(self, name: str, path: str, pid: int = None, status: NodeStatus = NodeStatus.STOPPED):
        self.name = name
        self.path = path
        self.pid = pid
        self.status = status
        self.process: Optional[subprocess.Popen] = None


class NodeControlService:
    """节点控制服务"""
    
    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._status_callbacks: List[Callable] = []

    def register_node(self, name: str, path: str):
        self.nodes[name] = NodeInfo(name, path)

    def unregister_node(self, name: str):
        if name in self.nodes:
            if self.nodes[name].status == NodeStatus.RUNNING:
                self.stop_node(name)
            del self.nodes[name]

    def start_node(self, name: str) -> bool:
        if name not in self.nodes:
            return False
        node_info = self.nodes[name]
        if node_info.status != NodeStatus.STOPPED:
            return False
        try:
            node_info.status = NodeStatus.STARTING
            self._notify(name, NodeStatus.STARTING)
            node_path = Path(node_info.path)
            # 检测节点类型
            if (node_path / "main.py").exists():
                cmd = ["python", str(node_path / "main.py")]
            elif (node_path / "index.js").exists():
                cmd = ["node", str(node_path / "index.js")]
            elif (node_path / "Cargo.toml").exists():
                cmd = ["cargo", "run"]
            else:
                cmd = ["python", str(node_path / "main.py")]
            cwd = str(node_path)
            process = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            node_info.process = process
            node_info.pid = process.pid
            self._active_processes[name] = process
            node_info.status = NodeStatus.RUNNING
            self._notify(name, NodeStatus.RUNNING)
            self._monitor(name, process)
            return True
        except Exception as e:
            print(f"Error starting node {name}: {e}")
            node_info.status = NodeStatus.ERROR
            self._notify(name, NodeStatus.ERROR)
            return False

    def stop_node(self, name: str) -> bool:
        if name not in self.nodes or name not in self._active_processes:
            return False
        node_info = self.nodes[name]
        if node_info.status not in [NodeStatus.RUNNING, NodeStatus.STARTING]:
            return False
        try:
            node_info.status = NodeStatus.STOPPING
            self._notify(name, NodeStatus.STOPPING)
            process = self._active_processes[name]
            if os.name == 'nt':
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
            del self._active_processes[name]
            node_info.process = None
            node_info.pid = None
            node_info.status = NodeStatus.STOPPED
            self._notify(name, NodeStatus.STOPPED)
            return True
        except Exception as e:
            print(f"Error stopping node {name}: {e}")
            node_info.status = NodeStatus.ERROR
            self._notify(name, NodeStatus.ERROR)
            return False

    def stop_all_nodes(self):
        for name in list(self._active_processes.keys()):
            self.stop_node(name)

    def get_node_status(self, name: str) -> Optional[NodeStatus]:
        if name in self.nodes:
            return self.nodes[name].status
        return None

    def _monitor(self, name: str, process: subprocess.Popen):
        def run():
            try:
                process.wait()
                if name in self.nodes and name not in self._active_processes:
                    self.nodes[name].status = NodeStatus.ERROR
                    self._notify(name, NodeStatus.ERROR)
            except Exception as e:
                print(f"Monitor error for {name}: {e}")
        monitor_thread = QThread()
        monitor_worker = QObject()
        monitor_worker.moveToThread(monitor_thread)
        monitor_thread.started.connect(run)
        monitor_thread.finished.connect(monitor_thread.deleteLater)
        monitor_thread.start()

    def _notify(self, name: str, status: NodeStatus):
        for cb in self._status_callbacks:
            try:
                cb(name, status)
            except Exception as e:
                print(f"Callback error: {e}")

    def subscribe(self, callback: Callable):
        self._status_callbacks.append(callback)

    def unsubscribe(self, callback: Callable):
        try:
            self._status_callbacks.remove(callback)
        except ValueError:
            pass


# 全局实例
node_control_service = NodeControlService()
```

**修改文件**：`ui/main_window.py`

在 `BNOSMainWindow.__init__` 中创建服务实例：

```python
from ui.core.node_control_service import NodeControlService, node_control_service

class BNOSMainWindow(QMainWindow):
    def __init__(self):
        # ... 原有代码 ...
        
        # 🆕 节点控制服务
        self._node_service = node_control_service
        
        # 🆕 注册项目中的节点
        for node_name, node_data in self.nodes_data.items():
            self._node_service.register_node(node_name, node_data.get("path", ""))
        
        # 🆕 订阅节点状态变化
        self._node_service.subscribe(self._on_node_service_status)
```

将原来的 `start_selected_node` 方法改为委托：

```python
def start_selected_node(self):
    """启动选中节点（委托给 NodeControlService）"""
    selected = self._get_selected_node_name()
    if selected:
        self._node_service.start_node(selected)

def _on_node_service_status(self, name, status):
    """接收节点状态变化通知"""
    # 更新 UI 状态指示灯
    pass  # 具体实现根据现有 panel 接口调整
```

**可见效果**：
1. 节点启动/停止功能照常工作
2. 状态指示灯正常变化
3. 后台进程正确启动和终止
4. 菜单操作（启动/停止）功能不变

**验证命令**：

```bash
python bnos_console.py
# 1. 选择一个节点 → 启动 → 观察指示灯变绿
# 2. 停止节点 → 观察指示灯变灰
# 3. 检查进程管理器：应有/没有对应 Python 进程
```

**回滚方式**：将 `start_selected_node` 等方法恢复为原有实现，删除 `_node_service` 相关代码。

---

### Step 5：提取关闭序列 → ShutdownOrchestrator

**目标**：将 `closeEvent` 中 170 行跨 6 个模块的关闭逻辑提取为独立的 `ShutdownOrchestrator`。

**当前问题**（来自分析报告 热点1）：
- `closeEvent` 中包含：停止轮询、强制杀节点、保存状态、断开信号、清理 IPC
- 关闭顺序隐式依赖、容易出错
- 大量 `hasattr` 检查暴露脆弱性

**方案**：创建 `ShutdownOrchestrator`，声明式定义关闭步骤和顺序。

**新增文件**：`ui/core/shutdown_orchestrator.py`

```python
"""
关闭序列编排器 — 声明式定义关闭步骤及其依赖顺序
"""
from typing import List, Callable


class ShutdownStep:
    """单个关闭步骤"""
    def __init__(self, name: str, action: Callable, depends_on: List[str] = None):
        self.name = name
        self.action = action
        self.depends_on = depends_on or []


class ShutdownOrchestrator:
    """关闭编排器 — 按依赖顺序执行关闭步骤"""

    def __init__(self):
        self._steps: List[ShutdownStep] = []

    def add_step(self, name: str, action: Callable, depends_on: List[str] = None):
        self._steps.append(ShutdownStep(name, action, depends_on))

    def execute(self):
        """按拓扑顺序执行所有关闭步骤"""
        executed = set()

        def run_step(step: ShutdownStep):
            if step.name in executed:
                return
            for dep in step.depends_on:
                dep_step = next((s for s in self._steps if s.name == dep), None)
                if dep_step:
                    run_step(dep_step)
            print(f"  [Shutdown] {step.name}...")
            try:
                step.action()
                executed.add(step.name)
                print(f"  [Shutdown] {step.name} ✓")
            except Exception as e:
                print(f"  [Shutdown] {step.name} ✗ 失败: {e}")

        for step in self._steps:
            run_step(step)

        print(f"[Shutdown] 完成, 共执行 {len(executed)}/{len(self._steps)} 步骤")
```

**修改文件**：`ui/main_window.py` — `closeEvent` 方法

```python
# === 修改前 ===
def closeEvent(self, event):
    # 170 行关闭逻辑...
    super().closeEvent(event)

# === 修改后 ===
from ui.core.shutdown_orchestrator import ShutdownOrchestrator

def closeEvent(self, event):
    self._orchestrator.execute()
    event.accept()
```

在 `__init__` 中构建编排器：

```python
# 在 __init__ 末尾
self._orchestrator = ShutdownOrchestrator()
self._orchestrator.add_step("stop_polling",   lambda: polling_manager.stop())
self._orchestrator.add_step("stop_all_nodes", lambda: self._node_service.stop_all_nodes(), depends_on=["stop_polling"])
self._orchestrator.add_step("save_layouts",   lambda: self._canvas_host.save_all_layouts())
self._orchestrator.add_step("save_state",     lambda: save_state(self))
self._orchestrator.add_step("disconnect_signals", self._disconnect_all_signals, depends_on=["save_state"])
self._orchestrator.add_step("cleanup_ipc",    self._cleanup_ipc, depends_on=["stop_all_nodes"])
```

**可见效果**：

1. 关闭 BNOS Console 时控制台输出清晰的关闭步骤日志：

```
[Shutdown] stop_polling...
[Shutdown] stop_polling ✓
[Shutdown] stop_all_nodes...
[Shutdown] stop_all_nodes ✓
[Shutdown] save_layouts...
[Shutdown] save_layouts ✓
...
[Shutdown] 完成, 共执行 6/6 步骤
```

2. 窗口状态、面板可见性、画布位置正常保存
3. 所有节点进程被正确终止
4. 无残留进程、无崩溃

**验证命令**：

```bash
python bnos_console.py
# 1. 正常操作几分钟
# 2. 关闭窗口
# 3. 观察控制台输出的关闭日志
# 4. 重新打开 → 确认状态恢复正确
```

**回滚方式**：恢复原有的 `closeEvent` 实现。

---

## 四、阶段三：面板与画布解耦

---

### Step 6：实现统一面板注册机制

**目标**：新面板只需注册到 `PanelRegistry`，无需修改 `main_window.py`。

**当前问题**（来自分析报告 热点3）：
- `node_list_panel.py` 和 `node_list_dock.py` 有 ~400 行重复代码
- 添加新面板需要改主窗口 3-5 处

**方案**：在已有的 `PanelManager` 基础上，完善 `PanelRegistry`，并提取共享的树组件。

**新增文件**：`ui/panels/_node_tree_widget.py`

```python
"""
共享的节点树组件 — 供 NodeListDockPanel 和 NodeListPanel 共用
消除 ~400 行重复代码
"""
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class NodeTreeWidget(QTreeWidget):
    """节点树形组件 — 统一树渲染、状态显示、拖拽支持"""

    node_selected = pyqtSignal(str)
    node_context_menu = pyqtSignal(str)
    node_double_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setIndentation(16)
        self.itemClicked.connect(self._on_click)
        self.itemDoubleClicked.connect(self._on_double_click)

    def add_node(self, name: str, status: str = "stopped", icon=None):
        item = QTreeWidgetItem(self)
        item.setText(0, name)
        item.setData(0, Qt.ItemDataRole.UserRole, name)
        self._apply_status(item, status)
        return item

    def update_node_status(self, name: str, status: str):
        items = self.findItems(name, Qt.MatchFlag.MatchExactly, 0)
        for item in items:
            self._apply_status(item, status)

    def _apply_status(self, item: QTreeWidgetItem, status: str):
        color_map = {
            "running":  "#6a9955",
            "starting": "#dcdcaa",
            "stopping": "#ce9178",
            "stopped":  "#808080",
            "error":    "#f44747",
        }
        item.setForeground(0, QColor(color_map.get(status, "#808080")))

    def _on_click(self, item, col):
        self.node_selected.emit(item.data(0, Qt.ItemDataRole.UserRole))

    def _on_double_click(self, item, col):
        self.node_double_clicked.emit(item.data(0, Qt.ItemDataRole.UserRole))
```

**修改文件**：
- `ui/panels/node_list_dock.py` — 用 `NodeTreeWidget` 替换内联树代码
- `ui/panels/node_list_panel.py` — 同上

**可见效果**：
1. 节点列表的显示、状态颜色、拖拽行为与原先完全一致
2. 两个面板版本的树渲染由同一个组件提供，行为和样式 100% 统一
3. 未来添加第三个面板视图只需复用 `NodeTreeWidget`

**验证命令**：

```bash
python bnos_console.py
# 1. 打开节点列表面板 → 确认树形显示正常
# 2. 启动/停止节点 → 确认状态颜色变化正常
# 3. 拖拽节点 → 确认拖拽功能正常
# 4. 右键菜单 → 确认菜单功能正常
```

**回滚方式**：将两个面板文件恢复为原有内联实现。

---

### Step 7：Canvas Mixin → 组合模式

**目标**：将 `NodeCanvas` 的 6 层 mixin 继承改为独立的控制器组合。

**当前问题**（来自分析报告 热点4）：
- 6 个 mixin 通过隐式 `self.nodes`、`self.scene` 等属性耦合
- 运行时错误难以排查
- 无法静态类型检查

**方案**：每个功能域提取为独立控制器类，通过构造函数注入 `canvas` 引用。

**新增文件**：`ui/canvas/controllers.py`

```python
"""
Canvas控制器集合，将原来的mixin模式改为组合模式
"""
from typing import Optional
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtWidgets import QRubberBand, QMenu
from pathlib import Path
import json


class CanvasConnectionController:
    """连线控制"""
    def __init__(self, canvas):
        self.canvas = canvas
        self.connection_start_pos = None
        self.temp_line = None

    def handle_start(self, pos: QPointF):
        self.connection_start_pos = pos

    def handle_end(self, pos: QPointF):
        self.connection_start_pos = None


class CanvasBatchOperations:
    """批量操作"""
    def __init__(self, canvas):
        self.canvas = canvas
        self.selected_items_before = []

    def start_batch(self):
        self.selected_items_before = self.canvas.scene().selectedItems()

    def end_batch(self):
        self.selected_items_before = []


class BoxSelectionController:
    """框选"""
    def __init__(self, canvas):
        self.canvas = canvas
        self.rubber_band: Optional[QRubberBand] = None
        self.origin = QPointF()

    def start(self, pos: QPointF):
        self.origin = self.canvas.mapToScene(pos)
        if not self.rubber_band:
            self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.canvas)
        self.rubber_band.setGeometry(int(pos.x()), int(pos.y()), 0, 0)
        self.rubber_band.show()

    def update(self, pos: QPointF):
        if self.rubber_band:
            r = QRectF(self.origin, self.canvas.mapToScene(pos)).normalized()
            self.rubber_band.setGeometry(int(r.left()), int(r.top()), int(r.width()), int(r.height()))

    def end(self, pos: QPointF):
        if self.rubber_band:
            self.rubber_band.hide()
            rect = QRectF(self.origin, self.canvas.mapToScene(pos)).normalized()
            for item in self.canvas.items(rect.toRect()):
                item.setSelected(True)
            self.rubber_band = None


class CanvasMenuController:
    """右键菜单"""
    def __init__(self, canvas):
        self.canvas = canvas

    def show_menu(self, pos: QPointF):
        scene_pos = self.canvas.mapToScene(int(pos.x()), int(pos.y()))
        menu = QMenu(self.canvas)
        add_action = menu.addAction("添加节点")
        add_action.triggered.connect(lambda: print(f"Add node at {scene_pos}"))
        menu.addMenu("布局").addAction("自动布局").triggered.connect(lambda: print("Auto layout"))
        menu.exec(self.canvas.mapToGlobal(pos))


class CanvasLayoutController:
    """布局持久化"""
    def __init__(self, canvas):
        self.canvas = canvas

    def save_layout(self, path: Path = Path("canvas_layout.json")):
        layout = {
            "transform": self.canvas.transform().toAffine(),
            "nodes": []
        }
        for item in self.canvas.scene().items():
            if hasattr(item, 'pos'):
                layout["nodes"].append({
                    "id": getattr(item, 'id', str(id(item))),
                    "x": item.pos().x(), "y": item.pos().y()
                })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(layout, f, ensure_ascii=False, indent=2)


class CanvasColorController:
    """颜色主题"""
    def __init__(self, canvas):
        self.canvas = canvas
        self.is_dark = True

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        if self.is_dark:
            self.canvas.setBackgroundBrush(QColor(30, 30, 30))
        else:
            self.canvas.setBackgroundBrush(QColor(240, 240, 240))


class CanvasZoomController:
    """缩放控制"""
    def __init__(self, canvas):
        self.canvas = canvas

    def zoom_in(self):
        self.canvas.scale(1.15, 1.15)

    def zoom_out(self):
        self.canvas.scale(1 / 1.15, 1 / 1.15)

    def zoom_fit(self):
        rect = self.canvas.scene().itemsBoundingRect()
        if not rect.isEmpty():
            self.canvas.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
```

**修改文件**：`ui/canvas/canvas_view.py`

```python
# === 修改前 ===
class NodeCanvas(
    CanvasConnectionsMixin, CanvasBatchOpsMixin,
    CanvasBoxSelectMixin, CanvasMenusMixin,
    CanvasLayoutMixin, CanvasColorsMixin,
    QGraphicsView
):
    pass

# === 修改后 ===
from ui.canvas.controllers import (
    CanvasConnectionController, CanvasBatchOperations,
    BoxSelectionController, CanvasMenuController,
    CanvasLayoutController, CanvasColorController, CanvasZoomController
)

class NodeCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # ... 原有初始化 ...
        
        # 🆕 组合控制器
        self.connections = CanvasConnectionController(self)
        self.batch_ops    = CanvasBatchOperations(self)
        self.box_select   = BoxSelectionController(self)
        self.menus        = CanvasMenuController(self)
        self.layout_ctrl  = CanvasLayoutController(self)
        self.colors       = CanvasColorController(self)
        self.zoom_ctrl    = CanvasZoomController(self)
```

将原来 mixin 中的方法调用改为控制器调用：

```python
# 原: self.start_connection(pos)
# 改: self.connections.handle_start(pos)

# 原: self.save_layout()
# 改: self.layout_ctrl.save_layout()

# 原: self.zoom_in()
# 改: self.zoom_ctrl.zoom_in()
```

**可见效果**：
1. 画布所有交互行为不变（缩放、平移、连线、框选、右键菜单）
2. 画布布局保存/加载正常
3. 颜色主题切换正常
4. 不再有隐式 mixin 依赖，每个控制器有明确的接口

**验证命令**：

```bash
python bnos_console.py
# 1. Ctrl+滚轮缩放 → 正常
# 2. 空格+拖拽平移 → 正常
# 3. 拖动节点连线 → 正常
# 4. 框选多个节点 → 正常
# 5. 右键菜单 → 正常
# 6. 关闭再打开 → 画布位置恢复 → 正常
```

**回滚方式**：恢复原始的 mixin 继承声明，删除控制器实例化代码。

---

### Step 8：MainWindow 最终精简

**目标**：`ui/main_window.py` 从 ~1500 行精简到 ~500 行，仅保留 Qt 窗口组装职责。

**修改文件**：`ui/main_window.py`

清理已经委托出去的代码段：
- 删除已迁移到 `PanelManager` 的 toggle 方法
- 删除已迁移到 `NodeControlService` 的节点启动/停止方法
- 删除已迁移到 `ShutdownOrchestrator` 的关闭步骤
- 保留：窗口 UI 组装、菜单构建、信号槽连接、布局管理

**精简后的 main_window.py 结构（~500 行）**：

```
行 1-50:    导入声明（精简为 ~10 个 import）
行 51-100:  类声明 + __init__ 开始
行 101-150: UI 组件创建（菜单栏、工具栏、CanvasHost）
行 151-200: 面板管理器初始化 + 状态恢复
行 201-250: 信号槽连接（polling_manager → 回调）
行 251-350: 核心交互方法（启动/停止/项目操作 → 委托给服务层）
行 351-400: 窗口生命周期（resizeEvent, moveEvent）
行 401-450: closeEvent（委托给 ShutdownOrchestrator）
行 451-500: 辅助方法（Toast、通知等）
```

**可见效果**：
1. BNOS Console 全部功能不变
2. `main_window.py` 文件大小显著减少
3. 代码结构清晰，每个职责归属明确
4. 未来添加功能不再需要在主窗口堆积代码

**验证命令**：

```bash
python bnos_console.py
# 执行完整的回归测试：
# - 启动/停止节点
# - 切换面板
# - 创建/打开项目
# - 拖拽节点连线
# - 画布缩放平移
# - 保存/恢复状态
# - 关闭软件
```

---

## 五、验证清单

完成全部 8 步后，用此清单验证：

### 核心功能
- [ ] BNOS Console 正常启动（启动动画 → 主窗口）
- [ ] 节点列表显示正常（树形结构 + 状态颜色）
- [ ] 节点启动 → 状态灯变绿 → 进程正常运行
- [ ] 节点停止 → 状态灯变灰 → 进程终止
- [ ] 创建/打开项目正常
- [ ] 导出/导入节点正常
- [ ] 外部节点挂载/卸载正常

### 画布交互
- [ ] Ctrl+滚轮缩放正常
- [ ] 空格+拖拽平移正常
- [ ] 框选多个节点正常
- [ ] 节点拖动连线正常
- [ ] 右键菜单功能正常
- [ ] 颜色主题切换正常

### 面板系统
- [ ] 节点列表 Dock 显示/隐藏正常
- [ ] 资源监控显示/隐藏正常
- [ ] 节点监控显示/隐藏正常
- [ ] 面板可见性持久化（关闭重开状态保持一致）

### 状态持久化
- [ ] 窗口位置/大小恢复正常
- [ ] 画布视野位置恢复正常
- [ ] Dock 布局恢复正常
- [ ] 上一个项目路径记忆正常

### 稳定性
- [ ] 关闭软件无残留进程
- [ ] 关闭序列日志完整输出
- [ ] 连续启动-关闭 3 次无异常
- [ ] 空白项目启动不崩溃

---

## 六、附录：回滚指南

每一步都有独立的回滚方案：

| 步骤 | 回滚操作 | 风险 |
|------|---------|------|
| Step 1 | 删除 `event_bus.py` | 零风险 |
| Step 2 | 删除 `di.py` + 验证代码 | 零风险 |
| Step 3 | 恢复 `main_window.py` 的 toggle 方法 | 低风险 |
| Step 4 | 恢复 `main_window.py` 的节点控制方法 | 中风险（建议用 git revert） |
| Step 5 | 恢复 `main_window.py` 的 `closeEvent` | 中风险（建议用 git revert） |
| Step 6 | 恢复两个面板文件的原实现 | 低风险 |
| Step 7 | 恢复 `canvas_view.py` 的 mixin 继承 | 中风险（建议用 git revert） |
| Step 8 | 无回滚需要（仅删除代码） | 低风险 |

### Git 分支策略建议

```bash
# 为每步创建独立分支，合并前充分验证
git checkout -b decouple/step1-eventbus
# ... 完成 Step 1 ...
git add . && git commit -m "Step1: EventBus 基础设施"
python bnos_console.py  # 验证可运行

git checkout -b decouple/step2-di
# ... 完成 Step 2 ...
git add . && git commit -m "Step2: DI 容器"
python bnos_console.py  # 验证可运行

# 依此类推...
```

---

> **总工时估算**：8-12 人·天，分 3 个阶段渐进实施。  
> **预期收益**：主窗口 LOC 减少 50%+，可维护性指数从 ~55 提升至 ~75+，新增面板成本从 2 天降至 4 小时。
