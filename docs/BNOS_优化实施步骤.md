# 📋 BNOS 项目优化实施步骤

## 文档说明

本文档详细记录了 BNOS 项目优化的完整实施步骤，按照优先级（P0 → P1 → P2）顺序编排，便于团队按计划推进。

---

## 目录

1. [P0 级别优化（本周内完成）](#p0-级别优化本周内完成)
   - 1.1 移除主窗口最大尺寸限制
   - 1.2 配置文件原子性写入
   - 1.3 subprocess 路径白名单校验
   - 1.4 Logger 配置日志轮转

2. [P1 级别优化（1-2 周完成）](#p1-级别优化1-2-周完成)
   - 2.1 画布视口更新模式优化
   - 2.2 PollingManager 分层轮询优化
   - 2.3 节点名称验证器
   - 2.4 面板统一 Host 模式（NodeMonitor）
   - 2.5 对话框工具函数重构

3. [P2 级别优化（2-4 周完成）](#p2-级别优化2-4-周完成)
   - 3.1 ApplicationContext 聚合全局状态
   - 3.2 主窗口拆分
   - 3.3 建立测试体系
   - 3.4 i18n 字符串键规范化

---

## 一、P0 级别优化（本周内完成）

### 1.1 移除主窗口最大尺寸限制

**问题描述**：`setMaximumSize(1920, 1080)` 限制窗口尺寸，对高分辨率显示器用户不友好。

**文件路径**：`ui/main_window.py`

**修改步骤**：
1. 打开文件，定位到第 91-92 行
2. 删除或注释掉 `self.setMaximumSize(1920, 1080)`
3. 保留 `self.setMinimumSize(1024, 768)`

**修改前**：
```python
self.setMinimumSize(1024, 768)
self.setMaximumSize(1920, 1080)
```

**修改后**：
```python
self.setMinimumSize(1024, 768)
# 移除最大尺寸限制，支持高分辨率显示器
```

**验证**：运行程序，窗口可拉伸超过 1920×1080。

---

### 1.2 配置文件原子性写入

**问题描述**：配置写入过程崩溃会导致配置文件损坏。

**文件路径**：`ui/core/app_config.py`

**修改步骤**：
1. 打开文件，定位到 `save()` 方法
2. 修改为原子性写入逻辑

**修改前**：
```python
def save(self):
    with open(self.config_file, 'w', encoding='utf-8') as f:
        json.dump(self.config, f, indent=2, ensure_ascii=False)
```

**修改后**：
```python
def save(self):
    tmp_path = self.config_file + ".tmp"
    bak_path = self.config_file + ".bak"
    
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        
        if os.path.exists(self.config_file):
            os.replace(self.config_file, bak_path)
        
        os.replace(tmp_path, self.config_file)
        
        if os.path.exists(bak_path):
            os.remove(bak_path)
    except Exception as e:
        if os.path.exists(bak_path):
            os.replace(bak_path, self.config_file)
        raise e
```

**验证**：手动中断写入过程，检查配置文件是否完整。

---

### 1.3 subprocess 路径白名单校验

**问题描述**：节点启动命令来自配置文件，无校验可执行任意命令。

**文件路径**：`ui/core/node_process.py`、`ui/core/json_node_starter.py`

**修改步骤**：
1. 在 `node_process.py` 中添加验证方法
2. 在启动前调用验证

**修改内容**：
```python
# 在 NodeProcess 类中添加
def _validate_executable_path(self, python_exe, script_path):
    python_exe = os.path.normpath(python_exe)
    script_path = os.path.normpath(script_path)
    
    allowed_dirs = [
        self._venv_path,
        self._project_path,
        os.path.dirname(sys.executable)
    ]
    
    for allowed in allowed_dirs:
        if python_exe.startswith(allowed):
            return True
    
    logger.warning(f"非法路径检测: {python_exe}")
    return False
```

**验证**：尝试配置恶意路径，确认被拒绝执行。

---

### 1.4 Logger 配置日志轮转

**问题描述**：日志文件无限增长，占用磁盘空间。

**文件路径**：`ui/core/logger.py`

**修改步骤**：
1. 导入 `RotatingFileHandler`
2. 修改 Handler 配置

**修改前**：
```python
file_handler = logging.FileHandler(log_dir / "bnos_console.log", encoding='utf-8')
```

**修改后**：
```python
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler(
    log_dir / "bnos_console.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding='utf-8'
)
```

**验证**：运行程序一段时间，检查日志文件是否自动轮转。

---

## 二、P1 级别优化（1-2 周完成）

### 2.1 画布视口更新模式优化

**问题描述**：`FullViewportUpdate` 导致画布拖动时帧率低。

**文件路径**：`ui/canvas/canvas_view.py`

**修改步骤**：
1. 修改视口更新模式为 `SmartViewportUpdate`
2. 设置初始场景范围

**修改前**：
```python
self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
```

**修改后**：
```python
self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
self.scene().setSceneRect(-500, -500, 1000, 1000)
```

**验证**：拖动画布，检查帧率是否提升（目标：≥50 FPS）。

---

### 2.2 PollingManager 分层轮询优化

**问题描述**：每秒轮询所有节点，约 100+ 次磁盘 IO/秒。

**文件路径**：`ui/core/polling_manager.py`

**修改步骤**：
1. 分层设置轮询间隔
2. 使用 `QFileSystemWatcher` 替代部分轮询

**修改内容**：
```python
class PollingManager:
    def __init__(self):
        self._process_timer = QTimer()
        self._process_timer.setInterval(2000)
        
        self._config_timer = QTimer()
        self._config_timer.setInterval(5000)
        
        self._file_watcher = QFileSystemWatcher()
        self._file_watcher.fileChanged.connect(self._on_file_changed)
```

**验证**：使用工具监测磁盘 IO，确认空闲时 IO 显著减少。

---

### 2.3 节点名称验证器

**问题描述**：节点名称用于路径拼接，存在路径穿越风险。

**文件路径**：`ui/core/validators.py`（新建）

**创建步骤**：
1. 新建文件 `ui/core/validators.py`
2. 实现 `NodeNameValidator` 类

**文件内容**：
```python
import re

class NodeNameValidator:
    MAX_LENGTH = 64
    ALLOWED_CHARS = r'^[A-Za-z0-9_\u4e00-\u9fa5]+$'
    
    @staticmethod
    def validate(name):
        if not name:
            return False, "节点名称不能为空"
        
        if len(name) > NodeNameValidator.MAX_LENGTH:
            return False, f"节点名称不能超过 {NodeNameValidator.MAX_LENGTH} 个字符"
        
        if not re.match(NodeNameValidator.ALLOWED_CHARS, name):
            return False, "节点名称只能包含字母、数字、下划线和中文"
        
        if any(c in name for c in ('/', '\\', ':', '*', '?', '"', '<', '>', '|')):
            return False, "节点名称不能包含特殊字符"
        
        return True, ""
```

**验证**：测试输入包含特殊字符的节点名称，确认被拒绝。

---

### 2.4 面板统一 Host 模式（NodeMonitor）

**问题描述**：NodeMonitor 存在 Dock/Float 双实现，约 250 行重复代码。

**文件路径**：
- `ui/panels/node_monitor_core.py`（新建）
- `ui/panels/node_monitor.py`（修改）
- `ui/panels/node_monitor_dock.py`（修改）

**实施步骤**：

#### 步骤 1：创建核心 Widget
```python
# ui/panels/node_monitor_core.py
class NodeMonitorCore(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sub_panels = {}
        self._init_ui()
    
    def _init_ui(self):
        # 核心内容布局
        layout = QVBoxLayout(self)
        # ... 子面板容器等
```

#### 步骤 2：修改浮动版
```python
# ui/panels/node_monitor.py
class NodeMonitor(FloatingPanel):
    def __init__(self, parent=None):
        super().__init__(parent, title=t("k_info_monitor"))
        self._core = NodeMonitorCore(parent)
        self.content_layout.addWidget(self._core)
        # 保留浮动特性
```

#### 步骤 3：简化 Dock 版
```python
# ui/panels/node_monitor_dock.py
class NodeMonitorDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(NodeMonitorCore(parent))
```

**验证**：确认两个版本功能一致，代码不再重复。

---

### 2.5 对话框工具函数重构

**问题描述**：`dialog_utils.py` 中三个文件选择函数共享约 60% 逻辑。

**文件路径**：`ui/core/utils/dialog_utils.py`

**修改步骤**：
1. 提取基类 `BaseFilePickerDialog`
2. 子类化 `FolderPickerDialog` 和 `FilePickerDialog`

**修改内容**：
```python
class BaseFilePickerDialog(QDialog):
    def __init__(self, parent, title, mode='folder'):
        super().__init__(parent)
        self.mode = mode
        self._init_common_ui()
    
    def _init_common_ui(self):
        # 共享的导航栏、目录树
        pass

class FolderPickerDialog(BaseFilePickerDialog):
    pass

class FilePickerDialog(BaseFilePickerDialog):
    def __init__(self, parent, title, filter_ext=None):
        super().__init__(parent, title, mode='file')
        self.filter_ext = filter_ext
```

**验证**：测试文件/文件夹选择功能，确认正常工作。

---

## 三、P2 级别优化（2-4 周完成）

### 3.1 ApplicationContext 聚合全局状态

**问题描述**：8 个独立全局状态持有者，状态分散难以维护。

**文件路径**：`ui/core/application_context.py`（新建）

**创建步骤**：
1. 新建文件，实现 `ApplicationContext` 单例类
2. 在主窗口中使用

**文件内容**：
```python
class ApplicationContext:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_services()
        return cls._instance
    
    def _init_services(self):
        self.config = AppConfig()
        self.project = ProjectManager()
        self.node_control = NodeControlService()
        self.event_bus = EventBus()
        self.polling = PollingManager()
        self.process = ProcessManager()
        self.di = DIContainer()
```

**验证**：确认所有模块通过 `ApplicationContext` 访问服务。

---

### 3.2 主窗口拆分

**问题描述**：`BNOSMainWindow` 单文件约 1100+ 行，职责过多。

**文件路径**：
- `ui/main_window.py`（修改）
- `ui/main_window_state.py`（新建）
- `ui/main_window_lifecycle.py`（新建）
- `ui/main_window_actions.py`（新建）

**拆分策略**：

| 文件 | 职责 | 预计行数 |
|------|------|---------|
| `main_window.py` | 窗口构建、UI 初始化 | ~300 |
| `main_window_state.py` | 状态持久化 | ~200 |
| `main_window_lifecycle.py` | 启动/关闭编排 | ~250 |
| `main_window_actions.py` | 业务操作 | ~200 |

**实施步骤**：
1. 提取状态管理方法到 `main_window_state.py`
2. 提取生命周期方法到 `main_window_lifecycle.py`
3. 提取业务操作到 `main_window_actions.py`
4. 修改 `main_window.py` 仅保留 UI 构建

**验证**：确认所有功能正常，文件长度符合预期。

---

### 3.3 建立测试体系

**问题描述**：项目无单元测试，回归风险高。

**文件路径**：`tests/` 目录（新建）

**创建步骤**：
1. 创建测试目录结构
2. 编写各模块测试用例

**目录结构**：
```
tests/
├── __init__.py
├── test_polling_manager.py
├── test_app_config.py
├── test_di_container.py
├── test_event_bus.py
└── test_validators.py
```

**测试内容**：

| 模块 | 测试项 |
|------|-------|
| `polling_manager.py` | 轮询间隔、文件监听 |
| `app_config.py` | 配置读写、原子性写入 |
| `di.py` | 依赖注入、服务注册 |
| `validators.py` | 节点名称校验 |

**验证**：运行测试套件，确保所有测试通过。

---

### 3.4 i18n 字符串键规范化

**问题描述**：字符串键命名风格不一致。

**文件路径**：
- `resources/i18n/strings_cn.json`
- `resources/i18n/strings_en.json`

**规范化规则**：
```
{domain}.{object}.{action}
例如:
- node.start.title
- dialog.btn.ok
- canvas.menu.edit
```

**修改步骤**：
1. 遍历所有字符串键
2. 按新规则重命名
3. 更新所有引用位置

**示例**：

| 旧键 | 新键 |
|------|------|
| `k_node_select_first` | `node.select.first` |
| `_k_btn_up` | `dialog.btn.up` |
| `_k_file_too_large` | `dialog.file.too_large` |

**验证**：运行程序，确认所有文本正常显示。

---

## 四、验证清单

### P0 验证项
- [ ] 窗口可拉伸超过 1920×1080
- [ ] 配置文件写入中断后可恢复
- [ ] 非法路径被拒绝执行
- [ ] 日志文件自动轮转（5MB/个，保留3个）

### P1 验证项
- [ ] 画布拖动帧率 ≥50 FPS
- [ ] 空闲磁盘 IO ≤10 次/秒
- [ ] 节点名称特殊字符被拒绝
- [ ] NodeMonitor 两个版本功能一致
- [ ] 文件选择对话框正常工作

### P2 验证项
- [ ] 所有模块通过 ApplicationContext 访问服务
- [ ] 主窗口各文件行数 ≤500
- [ ] 单元测试覆盖率 ≥15%
- [ ] 所有字符串键符合命名规范

---

## 五、风险缓解

| 风险 | 缓解措施 |
|------|---------|
| 主窗口拆分引入 Bug | 渐进式拆分，每步回归测试 |
| 面板重构影响功能 | 保留浮动版特性，仅提取核心逻辑 |
| QFileSystemWatcher 兼容性 | 保留轮询作为 fallback |
| 线程池并发问题 | 限制最大线程数，添加同步锁 |

---

## 六、时间预估

| 阶段 | 时间 | 完成标志 |
|------|------|---------|
| P0 优化 | 1 周 | 4 项验证全部通过 |
| P1 优化 | 1-2 周 | 5 项验证全部通过 |
| P2 优化 | 2-4 周 | 4 项验证全部通过 |

---

**文档版本**：v1.0  
**创建日期**：2026-06-12  
**最后更新**：2026-06-12