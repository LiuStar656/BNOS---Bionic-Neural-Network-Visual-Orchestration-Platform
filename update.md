# BNOS 更新日志

## 2026-05-23 更新

### 新增功能

**统一轮询管理器** (`ui/core/polling_manager.py`)
- 整合所有定时轮询任务到统一管理器，避免多个定时器并行运行
- 支持任务注册/注销机制，支持不同轮询间隔
- 内置任务包括：
  - `node_health` (2秒): 节点进程健康状态检测
  - `global_logs` (2秒): 全局日志文件监控
  - `global_config` (2秒): 全局配置文件监控
  - `node_logs` (2秒): 节点日志文件监控
  - `node_config` (2秒): 节点配置文件监控
  - `node_output` (2秒): 节点 output.json 监控
  - `app_state` (5秒): 应用状态检测

### 文件变更

**新增文件:**
- `ui/core/polling_manager.py` - 统一轮询管理器

**删除文件:**
- `ui/core/system_monitor.py` - 已被 polling_manager 取代
- `ui/core/global_detector.py` - 已被 polling_manager 取代

**修改文件:**
- `ui/main_window.py` - 使用 polling_manager 替代 SystemMonitor 和 GlobalDetector
- `ui/panels/node_monitor.py` - 使用 polling_manager 订阅日志变化
- `ui/panels/node_expand_panel.py` - 更新导入
- `ui/dialogs/node_config_dialog.py` - 使用 polling_manager 订阅配置和日志变化

### Bug 修复

（其他未提交的改动）
- `tools/python_create_node.py`
- `ui/canvas/canvas_view.py`
- `ui/core/strings_cn.json`
- `ui/core/strings_en.json`
- `ui/core/utils/dialog_utils.py`
- `ui/core/utils/file_utils.py`
- `ui/panels/node_group_manager.py`
- `ui/panels/node_list_context.py`
- `ui/panels/node_list_panel.py`
- `ui/panels/property_panel.py`

### 使用方式

```python
from ui.core.polling_manager import polling_manager

# 订阅信号
polling_manager.node_status_changed.connect(handle_status)
polling_manager.global_log_changed.connect(handle_log)

# 启动轮询
polling_manager.start(nodes_data)

# 查询信息
recent_logs = polling_manager.get_recent_logs(count=50)
state = polling_manager.get_app_state()
```