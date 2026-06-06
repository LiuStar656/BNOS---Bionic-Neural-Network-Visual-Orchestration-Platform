# 🔧 GUI 架构重构与功能增强

## 🔧 GUI 架构重构与功能增强 (2026-05-21)

### 代码解耦重构 📦

**新建 10 个模块**，消除重复代码，降低耦合：

| 模块 | 职责 | 来源 |
|------|------|------|
| `ui/core/app_config.py` | 全局配置持久化 | 从 main_window 提取 |
| `ui/core/theme.py` | 深色 QSS 样式表 | 从 main_window 提取 |
| `ui/core/node_process.py` | 进程启动/停止/PID/健康检测 | 新建，消除 4 处重复 |
| `ui/canvas/canvas_colors.py` | 画布颜色管理 Mixin | 从 canvas_view 提取 |
| `ui/canvas/canvas_layout.py` | 画布布局持久化 Mixin | 从 canvas_view 提取 |
| `ui/canvas/canvas_menus.py` | 画布右键菜单 Mixin | 从 canvas_view 提取 |

- `main_window.py`：1491 → **935 行**（-556）
- `canvas_view.py`：1911 → **~1200 行**（-680）
- 消除 Toast 重复 170 行、进程管理重复 180 行

### 节点进程健康检测 🩺

- **PID 文件持久化**：`start_node_process` 写 `.pid`，`stop_node_process` 删 `.pid`
- **跨会话恢复**：重启 GUI 自动扫描 `.pid` 文件，检测后台运行进程并恢复 ● 状态
- **定期健康检查**：每 3 秒 `poll()` 运行中进程，崩溃节点自动标记为 ○ 已停止
- 修复 `subprocess.PIPE` 缓冲区死锁，改为 `DEVNULL`

### 选择系统统一 🖱️

- 删除 `selected_node` 单独属性
- 单选/框选/Ctrl+点击 全部统一使用 `box_selected_nodes`
- 框选节点自动 `setSelected(True)`，支持**群拖移动**
- 修复 lambda 闭包延迟绑定导致右键菜单颜色失效

### 节点防重叠 🧱

- 拖拽时自动检测并推开相邻节点
- 布局加载时 `setPos()` 也会触发防重叠

### 启动脚本修复 🔨

`tools/rust_create_node.py` 和 `tools/python_create_node.py`：
- 支持 `--no-pause` 参数（GUI 调用时静默运行）
- 使用 `start /b` / `nohup &` 后台启动，不再阻塞
- 启动后自动写入 `.pid` 文件
- 修复 Rust 双文件检测和自动构建逻辑

### 开发规范 📋

新增 `开发维护准则.md`（10 条规范 + 优先修复清单）和 `tools/节点生成器开发准则.md`（新语言节点标准模板）。

---