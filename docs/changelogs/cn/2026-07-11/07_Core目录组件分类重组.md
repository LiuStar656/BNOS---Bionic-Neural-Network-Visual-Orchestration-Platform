# Core 目录组件分类重组

## 更新概述

`ui/core/` 目录中 45 个模块按功能拆分为 7 个子目录，消除根级文件堆积问题，同时修复重组过程中引入的编码损坏和 `UnboundLocalError`。

## 核心改动

### 1. 目录分类

| 子目录 | 说明 | 文件数 |
|--------|------|--------|
| `node/` | 节点管理：复合节点、进程控制、配置解析、注册表、启动队列、IDE 扫描 | 13 |
| `dock/` | Dock 系统：主 Dock、面板管理、悬浮窗口、CanvasHost、位置持久化 | 7 |
| `system/` | 基础设施：DI 容器、EventBus、IPC、线程池、轮询管理、快捷键、更新调度、窗口状态 | 8 |
| `services/` | 应用服务：应用上下文、生命周期管理、核心进程、关机编排 | 5 |
| `project/` | 项目管理：项目加载、导入导出、文件操作 | 4 |
| `config/` | 配置：应用配置、主题、状态、验证器 | 4 |
| `i18n/` | 国际化：翻译引擎、key 注册表、中英文 JSON | 4 |

**保留在根级**：`logger.py`（80 处引用，移动代价过高）、`packager.py`、`dark_title_bar.py`、`splash_screen.py`

### 2. 兼容性保障

- `from ui.core.i18n import t` — **不变**，`i18n/__init__.py` 透明代理所有公开 API
- 所有 150+ 处外部 import 路径自动更新到新子目录路径
- 3 处字符串路径引用同步修正（`core_process.py` 注册路径）

### 3. Bug 修复

**编码损坏修复**：重组过程中 Task agent 批量编辑文件时引入的编码损坏，导致 `node_config_dialog.py` 和 `lifecycle.py` 中文字符变为 `�?` 替换字符，Python 解析报 `SyntaxError: invalid character`。已用英文注释重写这两个文件。

**UnboundLocalError 修复**：[canvas_event_handlers.py](file:///f:/Bionic Neural Network Program Operating System/ui/canvas/mixins/canvas_event_handlers.py) 中 `AnchorItem` 仅在连线模式代码块内局部导入，Alt+框选路径也引用了该变量，导致 `UnboundLocalError`。已将其提升为顶层导入，与 `NodeItem`、`EdgeItem` 并列。

## 迁移统计

| 修复类型 | 数量 |
|----------|------|
| import 路径更新 | 150+ 处 |
| 字符串路径引用 | 3 处 |
| 编码损坏修复 | 2 个文件 |
| 顶层导入修复 | 1 处 |

## 涉及文件

| 文件 | 改动类型 |
|------|---------|
| `ui/core/node/` (14 文件) | 新增子目录，13 个模块移入 |
| `ui/core/dock/` (8 文件) | 新增子目录，7 个模块移入 |
| `ui/core/system/` (9 文件) | 新增子目录，8 个模块移入 |
| `ui/core/services/` (6 文件) | 新增子目录，5 个模块移入 |
| `ui/core/project/` (5 文件) | 新增子目录，4 个模块移入 |
| `ui/core/config/` (5 文件) | 新增子目录，4 个模块移入 |
| `ui/core/i18n/` (5 文件) | 新增子目录，4 个模块移入 + `__init__.py` 透明代理 |
| `ui/core/i18n/__init__.py` | 新增 — 透明代理，保障旧 `from ui.core.i18n import t` 兼容 |
| `ui/dialogs/node_config_dialog.py` | 修复 — 编码损坏整文件重写 |
| `ui/main_window/lifecycle.py` | 修复 — 编码损坏整文件重写 |
| `ui/canvas/mixins/canvas_event_handlers.py` | 修复 — AnchorItem 局部导入提升为顶层 |
| 37 个外部引用文件 | 修改 — import 路径更新 |
