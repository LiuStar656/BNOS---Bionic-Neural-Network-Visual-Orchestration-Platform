# IDE 自动扫描与右键菜单 Action 集成

## 📋 更新概述

本次更新完成了 Phase 10：IDE 工作区集成功能。新增 `IDEScanner` 自动扫描器，检测本地已安装的 VSCode / Trae IDE，并提供统一的打开逻辑。IDE 功能键全部通过 Action 系统注册，画布右键菜单、节点配置对话框统一调用。

---

## 🎯 核心功能

### 1. IDEScanner 自动扫描器

**新增 `ui/core/ide_scanner.py`（214 行）**

- 跨平台 IDE 检测（Windows / Linux / macOS）
- 四层检测链路：**内存缓存 → app_config 持久化 → PATH 命令 → 环境变量/进程扫描 → 文件系统扫描**
- 环境变量推导：从 `TRAE_SANDBOX_CLI_PATH` 反向推导 Trae 安装根目录
- 进程扫描：PowerShell `Get-Process` 查找运行中 IDE 进程路径
- 覆盖非标准安装位置（如 `F:\Trae CN\` 等自定义盘符）
- 全局单例 `ide_scanner`，缓存结果到 `app_config.json`

**公开 API**：

| 方法 | 描述 |
|------|------|
| `find_vscode()` | 查找 VSCode 可执行文件路径 |
| `find_trae_ide()` | 查找 Trae IDE 可执行文件路径 |
| `open_vscode_workspace(node_name, node_path)` | 生成 `.code-workspace` 后用 VSCode 打开 |
| `open_in_vscode(workspace_path)` | 用 VSCode 打开指定路径 |
| `open_in_trae(workspace_path)` | 用 Trae IDE 打开指定路径 |
| `open_in_ide(workspace_path, ide_type)` | 统一 IDE 打开入口 |
| `add_buttons_to_layout(layout, node_name, node_path)` | 向对话框布局添加打开按钮 |

---

### 2. IDE Action 统一注册

**扩展 `builtin_node_actions.py`** — 新增 2 个节点 Action：

| Action ID | 名称 | 执行逻辑 |
|-----------|------|----------|
| `node.open_vscode` | 打开 VSCode | 生成 `.code-workspace` → 打开节点目录 |
| `node.open_trae_ide` | 打开 Trae IDE | 调用 `ide_scanner.open_in_trae()` |

**扩展 `builtin_canvas_actions.py`** — 新增 2 个画布 Action：

| Action ID | 名称 | 执行逻辑 |
|-----------|------|----------|
| `workspace.open_vscode` | 打开 VSCode | 用 VSCode 打开当前项目根目录 |
| `workspace.open_trae_ide` | 打开 Trae IDE | 用 Trae IDE 打开当前项目根目录 |

所有 IDE Action 通过 `ActionContext(extra={...})` 传递路径信息，与现有 Action 系统完全统一。

---

### 3. 右键菜单 Action 驱动

**重构 `ui/canvas/canvas_menus.py`**

- 单节点右键菜单：IDE 条目通过 `ActionFactory.create_action("node.open_vscode", ...)` 生成
- 画布空白区右键菜单：IDE 条目通过 `ActionFactory.create_action("workspace.open_vscode", ...)` 生成
- 移除 35 行硬编码 QAction 代码（`_open_in_ide()` / `_open_workspace_in_ide()`）

**重构 `ui/dialogs/node_config_dialog.py`**

- 移除 66 行重复 IDE 检测/打开代码（`_check_vscode_installed()` / `_check_trae_installed()` / `open_vscode_workspace()` / `open_trae_workspace()`）
- 统一调用 `ide_scanner.add_buttons_to_layout()` 生成对话框按钮

---

### 4. 国际化支持

| Key | 中文 | English |
|-----|------|---------|
| `k_open_vscode` | 打开VSCode | Open in VSCode |
| `_k_open_trae` | 打开 Trae IDE | Open in Trae IDE |

---

## 📁 修改文件汇总

### 新增文件

| 文件 | 行数 | 描述 |
|------|------|------|
| `ui/core/ide_scanner.py` | 214 | IDE 自动扫描器（检测 + 打开逻辑） |

### 修改文件

| 文件 | 变化 | 描述 |
|------|------|------|
| `ui/core/actions/builtin_node_actions.py` | +15 行 | 新增 `node.open_vscode` / `node.open_trae_ide` |
| `ui/core/actions/builtin_canvas_actions.py` | +30 行 | 新增 `workspace.open_vscode` / `workspace.open_trae_ide` |
| `ui/canvas/canvas_menus.py` | -35 行 | 移除硬编码 QAction，统一走 ActionFactory |
| `ui/dialogs/node_config_dialog.py` | -66 行 | 移除重复 IDE 代码，统一走 IDEScanner |
| `ui/main_window.py` | +2 行 | 注入 `app_config` 到 IDEScanner |
| `ui/core/strings_cn.json` | +1 行 | `_k_open_trae` |
| `ui/core/strings_en.json` | +1 行 | `_k_open_trae` |

---

## 🏗️ 架构设计

```
                    ┌──────────────────────────┐
                    │      ActionRegistry       │
                    │  node.open_vscode         │
                    │  node.open_trae_ide       │
                    │  workspace.open_vscode    │
                    │  workspace.open_trae_ide  │
                    └─────┬──────────┬──────────┘
                          │          │
              ┌───────────┘          └───────────┐
              ▼                                  ▼
┌──────────────────────┐            ┌──────────────────────┐
│  canvas_menus.py     │            │  node_config_dialog  │
│  ActionFactory       │            │  add_buttons_to_     │
│  .create_action()    │            │  layout()            │
└──────────┬───────────┘            └──────────┬───────────┘
           │                                   │
           └───────────────┬───────────────────┘
                           ▼
              ┌──────────────────────────┐
              │       IDEScanner          │
              │  ┌────────────────────┐   │
              │  │ 内存缓存           │   │
              │  │ app_config 持久化   │   │
              │  │ PATH 命令检测       │   │
              │  │ 环境变量推导        │   │
              │  │ 进程扫描            │   │
              │  │ 文件系统扫描        │   │
              │  └────────────────────┘   │
              │  .code-workspace 生成     │
              │  subprocess.Popen 启动    │
              └──────────────────────────┘
```

- **IDEScanner** 仅负责检测与打开，不参与菜单构建
- **Action 系统** 负责右键菜单条目生成（遵循统一规范）
- **对话框按钮** 因属于独立 UI 场景，保留 `add_buttons_to_layout()` 方法

---

## ⚠️ 注意事项

- Trae IDE 检测使用 `_find_from_runtime()` 优先于文件系统扫描，覆盖非标准安装路径
- 进程扫描依赖 PowerShell `Get-Process`，Windows 7+ 均可用
- `_find_from_runtime()` 仅在 Windows 平台生效，Linux/macOS 走文件系统扫描
- 生成的 `.code-workspace` 文件自动配置 Python 解释器路径（venv）

---

**更新日期**：2026-06-10
**更新人**：Trae AI
