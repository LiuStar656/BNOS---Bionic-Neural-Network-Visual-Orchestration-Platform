


# BNOS 更新日志

> 📖 英文版：[UPDATE_EN.md](UPDATE_EN.md)

---

## 🌐 全局状态同步改造 (2026-05-23)

### 功能改进

**全局状态订阅机制**
- 所有面板订阅 `polling_manager.node_status_changed` 信号
- 实现真正的全局状态同步，确保所有面板显示一致
- 当节点状态变化时，所有面板自动同步更新

**修改的面板**
| 面板 | 文件路径 |
|------|---------|
| 节点列表面板（浮动版） | `ui/panels/node_list_panel.py` |
| 节点列表Dock面板 | `ui/panels/node_list_dock.py` |
| 资源监测面板（浮动版） | `ui/panels/resource_monitor.py` |
| 资源监测Dock面板 | `ui/panels/resource_monitor_dock.py` |
| 节点监测面板（浮动版） | `ui/panels/node_monitor.py` |
| 节点监测Dock面板 | `ui/panels/node_monitor_dock.py` |

### 技术实现

- **信号订阅机制**：所有面板订阅 `polling_manager.node_status_changed` 信号
- **状态更新回调**：各面板实现 `_on_node_status_changed` 回调方法
- **统一数据源**：所有面板从 PollingManager 获取节点状态
- **实时同步**：节点状态变化时，所有面板立即更新显示

### 修复问题

1. **节点状态显示不一致**：所有面板现在显示相同状态
2. **状态更新延迟**：面板响应更及时
3. **资源占用过高**：统一检测机制减少重复工作

### 代码变更

**节点列表面板**
- 订阅全局状态信号
- 实现状态更新回调
- 移除独立检测逻辑

**资源监测面板**
- 订阅全局状态信号
- 实现状态更新回调
- 使用统一数据源

**节点监测面板**
- 订阅全局状态信号
- 实现状态更新回调
- 显示实时状态信息

---

## 🖼️ 画布布局加载增强 (2026-05-23)

### 功能改进

**自动添加缺失节点**
- `load_layout` 方法现在能够自动添加缺失的节点到画布
- 从项目数据中获取节点信息，创建节点并应用布局配置
- 确保标签页切换时所有节点都能正确显示

**修复问题**
- 标签页切换时节点位置信息没有正确加载
- 画布布局文件中的节点未在画布上显示
- 颜色配置和样式信息加载不完整

### 技术实现

- **节点存在性检查**：遍历布局数据，检查节点是否已在画布上
- **自动创建节点**：当节点不存在但存在于项目数据中时，自动创建并添加
- **配置应用**：应用位置、样式、颜色等配置信息
- **异常处理**：完善异常处理机制，避免加载过程中的错误中断

### 代码变更

**画布布局模块** (`ui/canvas/canvas_layout.py`)
- 修改 `load_layout` 方法，增加自动节点添加逻辑
- 改进异常处理，修复语法错误
- 添加日志记录，便于调试和追踪

**修复细节**
- 修复了 `try-except` 语法错误
- 添加了缺失节点的自动创建功能
- 完善了颜色和样式配置的应用逻辑
- 增强了错误处理和日志记录

---

## 🛠️ 面板状态持久化与资源监测修复 (2026-05-23)

### 已修复的问题

**1. 面板自启冲突问题**
- 修复开机自启浮动面板导致Dock面板消失的问题
- 修复Dock面板自启时浮动面板无法自启的问题
- 修改文件：`ui/main_window.py`

**2. 空指针错误修复**
- 修复 `AttributeError: 'NoneType' object has no attribute 'update_node_status'`
- 在访问面板前添加空值检查
- 修改文件：`ui/main_window.py`

**3. 资源监测Dock面板节点数据加载**
- 修复节点资源占用信息未正常显示的问题
- 添加 `parent_window` 引用，实现自动获取节点数据
- 修改文件：`ui/panels/resource_monitor_dock.py`

**4. Dock面板关闭处理**
- 修复关闭Dock面板后访问已删除对象的问题
- 连接 `panel_closed` 信号，在关闭时清除引用
- 修改文件：`ui/main_window.py`

**5. 节点监测面板状态同步**
- 修复PID文件路径错误（优先读取 `.pid` 文件）
- 在资源监测时同步更新状态标题显示
- 修改文件：`ui/panels/node_monitor_dock.py`

### 功能改进

**面板状态持久化**
- 支持Dock版和浮动版面板的独立可见性状态保存
- 支持面板位置坐标持久化
- 重启后自动恢复之前打开的面板状态和位置

**资源监测布局优化**
- CPU、RAM、Disk 水平排列并居中显示
- 节点资源列表垂直排列
- Dock版和浮动版布局保持一致

### 修改的文件
- `ui/main_window.py` - 面板状态恢复、空值检查、Dock关闭处理
- `ui/panels/resource_monitor_dock.py` - 节点数据加载、状态同步
- `ui/panels/node_monitor_dock.py` - PID文件路径修复、状态同步
- `ui/core/app_config.py` - 单例模式
- `ui/core/dock_manager.py` - 重复创建防护

---

## 🖼️ 侧边工具栏尺寸放大与图标修复 (2026-05-23)

### 尺寸调整

**修改文件**: `ui/canvas/draw_toolbar.py`

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| 工具栏宽度 | 40px | **56px** |
| 按钮高度 | 34px | **44px** |
| 图标字体大小 | 14px | **18px** |

### 图标修复

修复了多个显示为感叹号 `!` 的无效图标：

| 功能 | 旧图标 | 新图标 | 说明 |
|------|--------|--------|------|
| 矩形工具 | `layout-panel` | ✅ `layout-panel` | 面板图标 |
| 圆角矩形 | `circle` | ✅ `circle` | 圆形图标 |
| 多边形 | `triangle-up` | ✅ `triangle-up` | 三角形图标 |
| 箭头工具 | `arrow-right` | ✅ `arrow-right` | 箭头图标 |
| 文本工具 | `file-text` | ✅ `file-text` | 文本文件图标 |
| 描边颜色 | `pencil` | ✅ `pencil` | 铅笔图标 |
| 填充颜色 | `paintcan` | ✅ `paintcan` | 油漆桶图标 |
| 锁定 | `lock` | ✅ `lock` | 锁图标 |
| 显示/隐藏 | `eye` | ✅ `eye` | 眼睛图标 |
| 撤销 | `arrow-left` → **`chevron-left`** | ✅ `chevron-left` | 左 Chevron |
| 重做 | `arrow-right` → **`chevron-right`** | ✅ `chevron-right` | 右 Chevron |
| 删除选中 | `trash` | ✅ `trash` | 垃圾桶图标 |
| 清空全部 | `clear-all` → **`close`** | ✅ `close` | 关闭图标 |

---

## 🎨 VS Code Codicon 图标系统集成 (2026-05-23)

### 图标资源管理

**新增图标源目录**: `codicon-source/`（原 `vscode-codicons-main`）

- 包含完整的 VS Code Codicon 图标库（MIT 许可证）
- 字体文件: `codicon.ttf`
- 图标定义: `codiconsLibrary.ts`

### 图标管理器

**更新**: `ui/icons/codicon.py`

- 图标映射从 527 个扩展至 **597 个**
- 新增 AI/调试/Git/终端/布局等类别图标
- 提供 `get_icon()` 和 `get_icon_font()` 便捷接口

### 新增图标类别

| 类别 | 新增图标 |
|------|---------|
| AI 助手 | `copilot`, `thinking`, `sparkle`, `openai`, `claude` |
| 调试 | `debug-all`, `debug-step-in`, `debug-step-out`, `debug-coverage` |
| Git | `git-compare`, `repo-clone`, `repo-pull`, `repo-push` |
| 终端 | `terminal-bash`, `terminal-cmd`, `terminal-powershell` |
| 布局 | `layout`, `layout-panel`, `layout-sidebar-left/right` |
| 运行 | `run-all`, `run-coverage`, `run-with-deps` |

### UI 图标替换

**修改文件**:
- `ui/menu/menu_manager.py` - 菜单图标
- `ui/canvas/draw_toolbar.py` - 绘图工具栏图标

### 使用示例

```python
from ui.icons import get_icon, get_icon_font

icon_char = get_icon('copilot')    # AI 助手图标
icon_char = get_icon('run-all')    # 运行图标
```

---

## 🔄 统一轮询管理器 + 全局状态监测重构 (2026-05-23)

### 统一轮询管理器

**新增**: `ui/core/polling_manager.py`（单例模式）

将所有需要定时轮询的任务统一管理：

| 轮询任务 | 间隔 | 描述 |
|---------|------|------|
| 节点健康检测 | 3s | 检测节点进程状态 |
| 全局日志监控 | 2s | 检测全局日志文件变化 |
| 全局配置监控 | 5s | 检测全局配置文件变化 |
| 节点日志监控 | 2s | 检测各节点日志变化 |
| 节点配置监控 | 5s | 检测各节点配置变化 |
| 节点输出 JSON | 1s | 检测 output.json 变化 |
| 应用状态监控 | 1s | 监测应用整体状态 |

**核心特性**：
- 单例模式，全局唯一实例
- 支持任务注册/取消/暂停/恢复
- 基于 QTimer 的精准定时
- 使用 PyQt 信号机制通知各面板

### 模块合并与重构

**删除冗余文件**：
- `ui/core/system_monitor.py` → 功能合并到 polling_manager
- `ui/core/global_detector.py` → 功能合并到 polling_manager

### 面板适配更新

| 面板 | 修改内容 |
|------|---------|
| `ui/main_window.py` | 替换 SystemMonitor/GlobalDetector 为 polling_manager |
| `ui/panels/node_monitor.py` | 订阅 polling_manager 日志信号 |
| `ui/panels/node_expand_panel.py` | 订阅 polling_manager 配置/输出信号 |
| `ui/dialogs/node_config_dialog.py` | 订阅 polling_manager 配置变化信号 |

### 影响文件

`polling_manager.py`(新增)、`main_window.py`、`node_monitor.py`、`node_expand_panel.py`、`node_config_dialog.py`、`system_monitor.py`(删除)、`global_detector.py`(删除)

---

## 🔄 独立启动器 + 三态状态灯 + Ctrl+D 删除 + 颜色设置修复 (2026-05-23)

### 独立 tkinter 启动器

**替换**内嵌 PyQt6 闪屏为独立 `launcher.py`（251 行）：
- 纯 tkinter 实现，系统 Python 零依赖，可独立打包 EXE
- 闪屏立即弹出 → 后台启动 venv pythonw bnos_console.py → 实时读取进度文件
- 进度条平滑动画，与主程序加载精准同步，100% 后 0.2 秒关闭
- 启动脚本：`.vbs` 零窗口静默启动，`.bat` 备用
- 无 venv 时闪屏显示安装指引后退出

### 三态状态指示灯

| 颜色 | 状态 | 检测逻辑 |
|------|------|---------|
| 灰色 `#888` | 停止 | listener PID 不存在 |
| 绿色 `#44FF44` | 空闲 | listener 运行，无 main 子进程 |
| 红色 `#FF4444` | 运行 | listener + main 子进程都在运行 |

基于 `psutil` 进程树检测，零侵入节点代码。健康检测每 3 秒轮询，UI 全局适配 idle/running/stopped 三态。

### Ctrl+D 统一删除快捷键

`Ctrl+D` 根据焦点上下文：
- 节点列表面板 → 批量删除节点/组
- 画布框选节点 → 从画布移除
- 画布框选图形 → 删除绘图图形

右键删除与右键菜单冲突已移除，改为 Ctrl+D 统一删除。

### 颜色设置修复

- **画布背景**：`drawBackground` 直接 `painter.fillRect` 读取 `canvas_bg_color`，`resetCachedContent` + `repaint` 即时生效
- **颜色对话框**：改为 BNOS 深色主题 Frameless 窗口，可拖动，边框可见
- **key 名对齐**：`choose_color` 的 `canvas_bg` 与 `collect_settings` 的 `temp_canvas_bg_color` 统一

### 快捷键管理系统

新增 `ui/core/shortcut_manager.py`：11 个快捷键中心定义 + 持久化到 `app_config.json` + 设置面板可视化编辑 + 双击捕获新按键。

### 语言切换修复

修复 Python `from import LANG` 值拷贝 bug（新增 `get_lang()`）+ 重启改用 `exit(42)` 退出码驱动 + `AppConfig` 支持新键持久化。

### 影响文件

`launcher.py`(新增)、`node_process.py`、`node_style.py`、`canvas_colors.py`、`canvas_view.py`、`shortcut_manager.py`(新增)、`color_settings_dialog.py`、`settings_dialog.py`、`menu_manager.py`、`main_window.py`、`i18n.py`、`app_config.py`、`start_bnos_console.vbs`(新增)、启动脚本

---

## 🚀 启动动画 + 品牌重命名 BnosConsole + README 重构 (2026-05-23)

### 启动闪屏

新增 `ui/core/splash_screen.py`（114 行）：
- **ASCII 艺术 BNOS**：6 行 █ 字符拼成，Consolas 13pt 加粗，全黑白配色
- **BNOS CONSOLE** 副标题 + 项目描述（i18n）
- **左下角实时日志**：QTextEdit 80px，启动步骤追加滚动
- **底部进度条**：0→100%，灰色 chunk
- **延迟关闭**：主窗口打开 2 秒后自动消失

### 品牌重命名：BnosGui → BnosConsole

| 旧名称 | 新名称 |
|--------|--------|
| `bnos_gui.py` | `bnos_console.py` |
| `start_bnos_gui.bat` | `start_bnos_console.bat` |
| `start_bnos_gui.sh` | `start_bnos_console.sh` |
| `requirements_gui.txt` | `requirements.txt` |
| `"BnosGui"` 窗口标题 | `"BnosConsole"` |
| `logs/bnos_gui.log` | `logs/bnos_console.log` |
| `_k_app_name` | `"BNOS Console"` (中/英统一) |

影响文件 25+ 个，含 `main_window.py`、`dark_title_bar.py`、`logger.py`、`build_bnos.spec`、README、UPDATE、tests 等。

### 影响文件

`splash_screen.py`(新增)、`bnos_console.py`(重命名+闪屏延迟)、`strings_cn/en.json`、`main_window.py`、`dark_title_bar.py`、`logger.py`、`build_bnos.spec`、启动脚本、README、UPDATE、tests

---

## 🔧 ComfyUI 风格连线重构 + 人工折叠交互 (2026-05-22)

### 贝塞尔曲线 → 直角直线 + 人工折叠 📏

**完全重写**: `ui/canvas/items/edge_item.py`

- **直线替换贝塞尔**：连线路径从三次贝塞尔曲线改为直线段连接
- **折叠点系统**：每条直线段中点渲染可拖拽的折叠手柄（蓝色圆点），始终可见
- **折叠机制**：已在折叠点（橙色圆点）支持直接拖拽调整角度，无需长按
- **相对坐标存储**：折叠点内部存储为 `(t, off_x, off_y)` 相对投影坐标，节点移动时折叠点自动跟随
- **选中变色不加粗**：选中线条 → 亮蓝 `#2aaaff`，悬停 → 颜色提亮 140%，宽度不变
- **双击删除**：双击已有折叠点即可删除，线段合并

**交互分层**：
| 元素 | 颜色 | 交互 |
|------|------|------|
| 线段中点手柄 | 蓝色 | 短按=选中线，长按250ms+拖拽=新建折叠点 |
| 已有折叠点 | 橙色 | 直接拖拽调整位置，双击删除 |

**序列化**：`canvas_layout.json` 中 `edges` 新增 `waypoints` 字段，兼容新旧格式。

### 临时连线同步 ✨

`canvas_view.py` 拖拽连线时同步渲染直线临时路径（虚线），与最终连线风格一致。

---

## 🆕 节点注册表 + 挂载外部节点 (2026-05-22)

### 节点注册表组件 📋

**新增**: `ui/core/node_registry.py`

- **持久化文件**：`<project>/node_registry.json`
- **扫描优先原则**：每次 `refresh_nodes()` 扫描 nodes/ 目录为主，注册表为辅
- **自动同步**：扫描到的节点标记 active，扫描不到的本地节点标记 missing
- **挂载节点支持**：新增 `mount_root` 字段标记外部挂载来源

### 挂载外部节点 🔗

**新增功能**：编辑菜单 → 「挂载外部节点」(Ctrl+Shift+O)

- **选择外部文件夹** → 读取 `config.json` → 挂载到当前项目（不复制文件）
- **自动创建锁定组**：以挂载根目录绝对路径命名的组，显示 🔒 标记
- **锁定规则**：
  - ❌ 挂载组内节点禁止移出到其他组
  - ❌ 外部节点禁止移入挂载组
  - ❌ 挂载组禁止重命名/删除
  - ✅ 同挂载组内节点可自由二次建子组
- **重启恢复**：`refresh_nodes()` 自动从注册表恢复挂载节点
- **卸载**：右键节点 → 「卸载外部节点」（保留源文件）

### NodeGroupManager 锁定组

**修改**: `ui/panels/node_group_manager.py`

- 新增 `_locked_groups` 集合 + `lock_group()`/`unlock_group()`/`is_group_locked()` 方法
- 持久化到 `node_groups.json` 的 `locked_groups` 字段
- 空锁定的组不会被自动清理

---

## 🔗 连线反推校验 + 连线交互修复 (2026-05-21)

### 连线关系 config.json 兜底校验 🔍

**新增组件**: `ui/core/connection_inferrer.py`

`canvas_layout.json` 加载时静默执行兜底校验，确保连线数据与各节点 `config.json` 完全一致：

- **反推机制**：解析每个节点 `config.json` 的 `listen_upper_file` 路径，自动提取上游节点名称
- **路径兼容**：支持绝对路径（`F:/project/nodes/A/output.json`）、相对路径（`../A/output.json`）、Windows 路径
- **自动修复**：config 中有但画布缺失的连线 → 自动补充（日志: `[Config兜底] 补充缺失连线`）
- **可疑警告**：画布有但 config 中无 `listen_upper_file` 对应 → 仅日志警告，不自动删除（保守策略）
- **完全静默**：校验过程用户无感知，日志带 `[Config兜底]` 标记

**影响文件**: `ui/core/connection_inferrer.py`(新增), `ui/canvas/canvas_layout.py`(修改)

### 连线选中与删除修复 🔧

**修改文件**: `ui/canvas/items/edge_item.py`, `ui/canvas/canvas_menus.py`

- **启用选中**：`EdgeItem` 设置 `ItemIsSelectable` 标志，左键点击选中，选中时加宽 4px + 高亮显示
- **加宽点击区**：`shape()` 返回 8px 描边路径，点击贝塞尔曲线不再困难
- **箭头子项化**：箭头改为 EdgeItem 子项 `QGraphicsPolygonItem(self)`，禁鼠标事件，点击穿透到父
- **右键菜单**：画布 `contextMenuEvent` 新增 `EdgeItem` 识别，右键菜单 → [删除连线] [修改连线颜色] [清除选择]
- **修复死代码**：删除 `scene.items()` 中搜索 `NodeCanvas` 的无效逻辑（`NodeCanvas` 是 `QGraphicsView` 不在 scene 中）
- **emoji 清理**：连线右键菜单移除 emoji

---

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

## 🎯 节点样式系统 (2026-05-21)

### 核心架构

**新增文件**: `ui/canvas/items/node_style.py`

实现完整的节点样式抽象系统，将方形节点和圆形节点的外观、布局、交互逻辑完全分离：

| 类 | 说明 |
|-----|------|
| `NodeStyle` | 抽象基类，定义 `style_key`、选中边框宽度、选中颜色等通用属性 |
| `RectNodeStyle` | 方形节点样式（默认），完整锚点、展开按钮、状态指示灯、IN/OUT 标签 |
| `DarkRectNodeStyle` | 深色方形样式（继承 `RectNodeStyle`），当前默认样式 |
| `DotNodeStyle` | 圆形节点样式，三层 z 轴架构，隐藏所有方形特有组件 |

### 圆形节点三层 z 轴架构

```
z=6  状态指示灯（顶层）
z=5  输入锚点（中层）  
z=4  输出锚点（底层）
```

- 圆形节点隐藏：锚点标签（IN/OUT）、状态指示灯、展开按钮 `>>`
- 节点名称左对齐显示在圆形下方，紧贴底部
- 选中时在节点上方显示 **浮动选中环**（`QGraphicsEllipseItem`，z=10），不遮挡节点本体

### 样式切换与持久化

- 画布右键菜单「节点样式」子菜单提供"方形"和"圆形"两种选项
- 所有菜单动作使用 `functools.partial` 绑定，避免 lambda 闭包延迟绑定 bug
- 样式切换调用 `_save_timer.start(500)` 触发自动保存
- `canvas_layout.json` 中存储每个节点的 `"style"` 字段（`"rect"` 或 `"dot"`）
- 加载布局时通过 `STYLES.get(style_key)()` 恢复样式

### Bug 修复

- 修复 lambda 闭包延迟绑定导致右键菜单动作错误
- 修复锚点位置叠加（构造时 + setPos 双重偏移）
- 修复 `setRect(w, h)` 参数错误 → `setRect(0, 0, w, h)`
- 修复 `setBrush(Qt.BrushStyle.NoBrush)` 类型错误 → `setBrush(QBrush())`
- 修复 `QLabel(self.node_name)` bool 类型错误 → `QLabel(str(self.node_name))`
- 修复圆形节点 rect 过小导致画布网格渲染异常 → 扩展至 80×80 并调用 `prepareGeometryChange()`

**影响文件**: `ui/canvas/items/node_style.py`(新增), `ui/canvas/items/node_item.py`(修改), `ui/canvas/canvas_menus.py`(修改), `ui/canvas/canvas_layout.py`(修改)

---

## ⚡ 画布可视区域渲染优化 (2026-05-21)

**修改文件**: `ui/canvas/canvas_view.py`

- 视口更新模式从 `FullViewportUpdate` 改为 `SmartViewportUpdate`：只重绘变化区域，大幅减少无效绘制
- 新增 `CacheBackground`：网格背景缓存，拖拽/缩放时无需重新绘制网格
- 新增 `DontSavePainterState` / `DontClipPainter` 优化标志，减少 Qt 绘图管线开销
- 画布平移、缩放、节点移动等操作的帧率和响应速度显著提升

---

## 🎨 VSCode 风格深色无边框窗口 (2026-05-21)

**新增组件**: `ui/core/dark_title_bar.py`

- 主窗口改为无边框设计，自定义 40px 黑色标题栏（`#1e1e1e`）
- 菜单栏嵌入标题栏同行：`[BnosGui] [文件] [编辑] [工具] [帮助] ←→ [─] [□] [✕]`
- 全局深色 QSS 主题：菜单、滚动条、输入框、按钮、表格等全部深色风格
- 无边框窗口支持边缘拖拽调整大小（6px 敏感区域）
- 自定义最小化/最大化/关闭按钮，关闭按钮 hover 变红（`#e81123`）
- 双击标题栏切换最大化/还原，拖动标题栏移动窗口

---

## 🆕 四项重大计划实施 (2026-05-21)

### **计划1: 节点展开面板** 📤

**新增组件**: `ui/panels/node_expand_panel.py`

- 画布节点右上角新增 `>>` 展开按钮，点击后以节点中心为基准展开浮动面板
- 左侧 output.json 编辑器（深色主题/可编辑/自动刷新）
- 右侧 启动/停止、节点配置、删除节点 三个操作按钮
- 右键菜单新增「展开节点」入口
- 窗口中心与节点中心坐标重合

### **计划2: 节点监测面板** 📊

**新增组件**: `ui/panels/node_monitor.py`

- 全局日志实时查看器，父窗口 + 可折叠子面板架构
- 每 3 秒同步画布节点变化，每 2 秒自动检测日志文件 mtime 变化刷新
- 菜单栏新增「工具(&T)」→「节点监测」(Ctrl+Shift+M)
- 画布右键菜单新增「节点监测」
- 窗口类型与节点列表一致，跟随主窗口移动

### **计划3: print → logging 迁移** 📝

**新增模块**: `ui/core/logger.py`

- 控制台 INFO + 文件 DEBUG 双通道输出
- 9 个文件、211 处 `print()` 全部迁移到 `logger`
- 日志文件: `logs/bnos_gui.log`（已被 .gitignore 排除）

### **计划4: 浮动面板窗口类型统一** 🪟

**新增基类**: `ui/core/floating_panel.py`

- 统一所有浮动窗口的无边框、半透明、拖动、标题栏
- `NodeListPanel` → 继承 `FloatingPanel`
- `NodeConfigDialog` → 继承 `FloatingPanel`（去掉 QDialogButtonBox）
- `NodeMonitor` → 继承 `FloatingPanel`
- `NodeExpandPanel` → 继承 `FloatingPanel`
- 视觉风格完全统一: `rgba(30,30,30,220)` 半透明深色容器

---

## 🎨 UI 精简与优化 (2026-05-21)

### **Emoji 全面清除 + 名称精简** 🧹

- 所有 UI 按钮、菜单、对话框标题中的 Emoji 图案已移除
- 按键名称精简为 2-4 字为主（如「清空所有连线」→「清空连线」）
- 涉及 6 个文件: canvas_view.py、property_panel.py、node_list_panel.py、main_window.py、menu_manager.py、bnos_gui.py

### **按钮颜色统一黑白灰** ⚫

- 所有按钮彩色背景改为黑白灰三阶（`#333`/`#555`/`#666`）
- 涉及 `property_panel.py` 14 处

### **画布右键菜单增强** 📋

- 画布空白区域右键新增「新建节点」子菜单（7 种语言）
- 画布空白区域右键新增「节点监测」

### **框选判定逻辑修复** 🎯

- 点击节点子元素（状态灯、文字、展开按钮）不再误触框选
- 使用 `parentItem()` 链上溯替代平面 `isinstance` 检查

### **Bug 修复** 🔧

- 修复画布单节点右键启动/停止崩溃（缺少 `start_single_node`/`stop_single_node` 方法）
- `.gitignore` 添加 `logs/` 排除日志目录

---

## 🏗️ 导入路径修复与代码质量优化 (2026-05-21 晚)

### **核心修复概览** 🔧

本次更新完成了全面的导入路径修复和代码质量提升：

1. **导入路径统一** - 所有模块导入使用正确的子目录路径
2. **工具栏→菜单栏迁移完成** - MenuManager 全面接管菜单
3. **新建节点功能修复** - NodeCreatorManager 路径计算修复
4. **代码质量提升** - 移除冗余导入，添加缺失导入

---

### **1. 导入路径全面修复** 📁

**问题**：`ui/` 目录重组后，多个模块的导入路径使用了错误的平坦路径而非子目录路径。

| 文件 | 错误导入 | 正确导入 |
|------|---------|---------|
| `main_window.py` | `from ui.property_panel import` | `from ui.panels.property_panel import` |
| `main_window.py` | `from ui.node_list_panel import` | `from ui.panels.node_list_panel import` |
| `main_window.py` | `from ui.node_creator_manager import` | `from ui.creators.node_creator_manager import` |
| `node_list_panel.py` | `from ui.node_group_manager import` | `from ui.panels.node_group_manager import` |

**影响文件**：
- `ui/__init__.py` - 移除不存在的 `NodeStyleDialog` 导入
- `ui/main_window.py` - 3 处导入路径修正
- `ui/panels/node_list_panel.py` - 2 处导入路径修正

---

### **2. 工具栏彻底移除，MenuManager 接管** 📋

**改动**：
- ✅ 删除 `init_toolbar()` 方法（原 68 行代码）
- ✅ 删除旧的 `init_menu()` 方法
- ✅ `MenuManager.init_menu(self)` 统一管理菜单栏
- ✅ 新增 `create_new_node_with_language(language)` 方法
- ✅ 补全 `show_about()` 方法体

**菜单结构**：
```
文件(&F)    编辑(&E)         帮助(&H)
├ 新建项目  ├ 新建节点 >     └ 关于
├ 打开项目  │  ├ Python
├ 节点列表  │  ├ Node.js
├ 颜色设置  │  ├ Go
└ 退出      │  ├ Java
            │  ├ C++
            │  ├ Rust
            │  └ Shell
            ├ 刷新节点
            ├ 清空连线
            ├ 启动节点
            └ 停止节点
```

---

### **3. 新建节点功能修复** 🔧

**问题**：点击菜单「新建节点」无法调用 tools/ 目录下的创建脚本。

**根因**：`node_creator_manager.py` 中 `base_dir` 路径只取了 2 级目录：
- 当前：`os.path.dirname(os.path.dirname(__file__))` → `ui/` ❌
- 正确：`os.path.dirname(os.path.dirname(os.path.dirname(__file__)))` → 项目根 ✅

**修复**：增加一级 `os.path.dirname()`，正确指向项目根目录。

---

### **4. 代码质量优化** 🧹

| 优化项 | 位置 | 说明 |
|--------|------|------|
| 添加缺失导入 | `main_window.py` | `QThread`, `signal`, `QApplication` 移至顶部 |
| 移除冗余导入 | `main_window.py` | `__init__` 中重复的 `NodeCreatorManager` 导入 |
| 移除方法内导入 | `main_window.py` | `show_toast`, `update_position` 中的 `QApplication` |
| 移除方法内导入 | `main_window.py` | `stop_selected_node`, `_force_stop_all_nodes` 中的 `signal` |
| 移除方法内导入 | `main_window.py` | `_start_async_node_creation` 中的 Qt 组件 |
| Lambda 修复 | `menu_manager.py` | `checked` 参数改为默认参数 `None` |
| Windows 进程终止 | `main_window.py` | 统一使用 `taskkill /F /T /PID` 替代 `terminate()` |

---

### **5. Windows 进程管理统一** 🪟

所有 3 个进程终止方法统一为可靠方案：

```python
# 统一使用 taskkill 强制终止进程树
subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
               capture_output=True, timeout=10)
```

影响方法：`stop_selected_node`, `stop_selected_node_by_name`, `_force_stop_all_nodes`

---

## 🏗️ 重大架构重构：UI 组件模块化与菜单栏整合 (2026-05-21)

### **核心改进概览** 🎯

本次更新完成了三大核心重构，显著提升了代码的可维护性、可扩展性和用户体验：

1. **工具栏整合进菜单栏** - 简化界面，符合桌面应用习惯
2. **Toast 通知系统组件化** - 完全解耦，支持跨模块复用
3. **UI 目录结构重组** - 按功能分层，职责清晰

---

### **1. 工具栏整合进菜单栏** 📋

**设计理念**: 采用纯菜单栏设计，移除独立工具栏，所有功能整合至标准菜单中。

**具体改动**:
- ✅ 移除顶部工具栏，释放垂直空间
- ✅ 所有功能整合到"文件"、"编辑"、"帮助"三个主菜单
- ✅ 高频操作使用子菜单分组（如"新建节点"下的7种语言选项）
- ✅ 每个菜单项配置清晰的快捷键和视觉标识（Emoji/Icon）
- ✅ 保持原有业务逻辑不变，仅改变访问入口

**优势**:
- 🎨 **界面简洁** - 减少视觉干扰，聚焦画布工作区
- ⚡ **操作高效** - 键盘快捷键 + 层级菜单，快速定位功能
- 📱 **符合习惯** - 遵循桌面应用标准交互模式
- 🔧 **易于维护** - 菜单逻辑集中在 `MenuManager` 类

**相关文件**:
- `ui/menu/menu_manager.py` - 菜单管理器（新增）
- `ui/main_window.py` - 委托调用 MenuManager

---

### **2. Toast 通知系统组件化** 🔔

**设计理念**: 将 Toast 通知从主窗口中提取为独立模块，实现完全解耦。

**核心特性**:
- ✅ **完全解耦** - Toast 不依赖主窗口，可独立测试
- ✅ **堆叠管理** - 自动处理多个通知的堆叠显示
- ✅ **60fps 动画** - 流畅的淡入淡出效果
- ✅ **四种类型** - success、error、warning、info
- ✅ **自定义时长** - 支持动态设置显示时间
- ✅ **边界检测** - 智能调整位置避免超出屏幕

**新增文件**:
- `ui/core/toast/toast_notification.py` - Toast 核心类
- `ui/core/toast/toast_manager.py` - Toast 管理器（堆叠管理）
- `ui/docs/toast_examples.py` - 使用示例

**迁移策略**:
- ✅ 保留源码备份（main_window.py 中的原始类定义）
- ✅ 渐进式迁移，先导入新模块再删除旧代码
- ✅ 向后兼容，现有调用代码无需修改

---

### **3. UI 目录结构重组** 📁

**设计理念**: 按功能领域分层组织，每个模块职责单一，便于维护和扩展。

**重组后结构**:
```
ui/
├── __init__.py                      # 统一入口
├── main_window.py                   # 主窗口
│
├── core/                            # 核心组件
│   ├── app_config.py                # 应用配置管理
│   └── toast/                       # Toast 通知系统
│       ├── toast_notification.py
│       └── toast_manager.py
│
├── menu/                            # 菜单系统
│   └── menu_manager.py              # 菜单栏管理器
│
├── canvas/                          # 画布系统
│   ├── canvas_view.py               # 画布视图
│   └── items/                       # 画布元素
│       ├── node_item.py             # 节点项
│       ├── edge_item.py             # 连线项
│       └── anchor_item.py           # 锚点项
│
├── panels/                          # 面板组件
│   ├── node_list_panel.py           # 节点列表面板
│   ├── property_panel.py            # 属性面板
│   └── node_group_manager.py        # 节点组管理
│
├── creators/                        # 创建器
│   └── node_creator_manager.py      # 节点创建管理器
│
└── docs/                            # 文档
    └── toast_examples.py
```

**导入方式对比**:

```python
# 旧方式（仍然可用）
from ui.toast_notification import ToastNotification
from ui.menu_manager import MenuManager

# 新方式（推荐）
from ui.core import AppConfig, ToastManager, ToastNotification
from ui.menu import MenuManager
from ui.panels import NodeListPanel
from ui.canvas import NodeCanvas
from ui.creators import NodeCreatorManager
```

**验证结果**:
```
总测试数: 20
通过: 20 ✅
失败: 0 ❌
🎉 所有测试通过！UI 重组成功！
```

**核心价值**:
- 🎯 **结构清晰** - 一眼看出组件归属
- 🔧 **易于维护** - 相关文件集中管理
- ♻️ **支持复用** - 跨模块导入更方便
- 📚 **文档完善** - 每个模块都有详细说明
- 🛡️ **安全可靠** - 充分测试，向后兼容

---

#### **修复问题：新建节点功能** 🔧

**问题**: 新建节点功能失效

**原因**: NodeCreatorManager 路径计算错误

**修复**: 增加一层 dirname 调用到达项目根目录

**结果**:
- ✅ Python 节点创建正常
- ✅ Rust 节点创建正常
- ✅ 自动刷新节点列表

---

#### **性能表现** ⚡

| 指标 | 数值 | 评价 |
|------|------|------|
| 启动时间 | < 2秒 | ⚡ 快速 |
| 节点加载 | 4个节点 < 1秒 | ⚡ 快速 |
| 画布渲染 | 流畅无卡顿 | ⚡ 优秀 |
| 内存占用 | 正常 | ✅ 合理 |
| CPU 占用 | < 5% | ✅ 低 |

---

### **相关文档** 📚

- [UI_REFACTORING_COMPLETE.md](UI_REFACTORING_COMPLETE.md) - UI 重组完整报告
- [IMPORT_PATH_FIXES.md](IMPORT_PATH_FIXES.md) - 导入路径修复记录
- [FIX_NODE_CREATION.md](FIX_NODE_CREATION.md) - 新建节点功能修复
- [TEST_REPORT_UI_REFACTORING.md](TEST_REPORT_UI_REFACTORING.md) - 测试报告

---




## 🆕 最近更新 (2026-05-20)

### 🏗️ 重大架构重构：Canvas Widget 模块化拆分

#### **Canvas Widget 拆分为分层架构** 🎨
- **概述**：成功将单体 canvas_widget.py（91.9KB）重构为模块化四层架构，显著提升了代码的可维护性、可测试性和可扩展性
- **动机**：
  - 单文件超过2200行，难以维护和扩展
  - 职责混合（UI渲染 + 业务逻辑 + 事件处理）
  - 紧密耦合导致可测试性差
  - 违反SOLID原则

##### **新架构设计**

**第一层：Items层** (ui/canvas/items/)
- **职责**：纯UI渲染组件，不包含业务逻辑
- **组件**：
  - nchor_item.py：节点端口（输入/输出锚点），支持悬停高亮和连接状态显示
  - 
ode_item.py：节点容器，管理标题、标签、选中状态
  - edge_item.py：连线条，绘制贝塞尔曲线，支持动态更新
- **设计原则**：
  - 不持有canvas引用
  - 通过回调函数通信
  - 专注于视觉呈现和交互反馈

**第二层：Core层** (ui/canvas/canvas_view.py)
- **职责**：画布核心管理和业务逻辑
- **包含**：
  - NodeCanvas类：主画布控制器（74.5KB，约1763行）
  - 节点/连线管理（CRUD操作）
  - 鼠标/键盘事件处理
  - 布局保存/加载
  - 缩放/平移控制
  - 框选/多选功能
- **关键特性**：
  - QGraphicsView + QGraphicsScene架构
  - VueFlow风格的无限画布体验
  - 支持5000x5000像素画布空间
  - 网格背景渲染
  - 自动保存机制（防抖500ms）

**第三层：兼容层** (ui/canvas_widget.py)
- **职责**：保持向后兼容性
- **实现**：Facade模式，重定向到新模块
- **代码量**：仅15行
- **迁移策略**：
  `python
  # 旧代码（仍然有效）
  from ui.canvas_widget import NodeCanvas
  
  # 新代码（推荐）
  from ui.canvas import NodeCanvas
  `

**第四层：模块导出** (ui/canvas/__init__.py, ui/canvas/items/__init__.py)
- **职责**：统一的导入接口
- **优势**：简化调用方代码，隐藏内部结构

##### **重构成果**

**代码指标对比**：

| 指标 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| **单文件大小** | 91.9KB | 74.5KB (core) + 分散items | ⬇️ 19% |
| **模块数量** | 1个 | 5个核心模块 | ⬆️ 5倍 |
| **代码行数** | ~2200行 | ~1763行 (core) + items | 持平 |
| **职责清晰度** | 混合 | 清晰分层 | ✅ 大幅提升 |
| **可测试性** | 困难 | 易于单元测试 | ✅ 显著提升 |
| **可维护性** | 低 | 高 | ✅ 显著提升 |

##### **验证结果**

**功能完整性检查**：
- ✅ 节点拖拽功能正常
- ✅ 锚点连线功能正常
- ✅ 贝塞尔曲线渲染正常
- ✅ 缩放/平移功能正常
- ✅ 框选/多选功能正常
- ✅ 布局保存/加载正常
- ✅ 右键菜单功能正常
- ✅ 节点配置对话框正常

**兼容性检查**：
- ✅ 旧导入方式仍可用：rom ui.canvas_widget import NodeCanvas
- ✅ 新导入方式可用：rom ui.canvas import NodeCanvas
- ✅ 所有现有功能无破坏性变更

**性能检查**：
- ✅ 画布渲染帧率无明显变化
- ✅ 内存占用无明显增加
- ✅ 节点操作响应速度保持一致

##### **影响文件**：
- ui/canvas/__init__.py - **新增**：模块导出接口
- ui/canvas/canvas_view.py - **新增**：核心视图和业务逻辑（1763行）
- ui/canvas/items/__init__.py - **新增**：图形项模块导出
- ui/canvas/items/anchor_item.py - **新增**：锚点项（输入/输出端口）
- ui/canvas/items/node_item.py - **新增**：节点容器项
- ui/canvas/items/edge_item.py - **新增**：连线条（贝塞尔曲线）
- ui/canvas_widget.py - **修改**：缩减至15行（Facade模式）
- ui/canvas/CANVAS_SPLIT_REPORT.md - **新增**：详细重构报告

##### **用户影响**：
- ✅ **零破坏性变更**：所有现有功能保持不变
- ✅ **稳定性提升**：更好的代码组织降低bug风险
- ✅ **未来开发更快**：模块化架构支持快速功能添加
- ✅ **文档更清晰**：清晰的分离使代码更易理解

##### **文档**：
- 完整技术细节：[ui/canvas/CANVAS_SPLIT_REPORT.md](ui/canvas/CANVAS_SPLIT_REPORT.md)


---

## 🆕 最近更新 (2026-05-20)

### 🏗️ 重大架构重构：Canvas Widget 模块化拆分

#### **Canvas Widget 拆分为分层架构** 🎨
- **概述**：成功将单体 canvas_widget.py（91.9KB）重构为模块化四层架构，显著提升了代码的可维护性、可测试性和可扩展性
- **动机**：
  - 单文件超过2200行，难以维护和扩展
  - 职责混合（UI渲染 + 业务逻辑 + 事件处理）
  - 紧密耦合导致可测试性差
  - 违反SOLID原则

##### **新架构设计**

**第一层：Items层** (ui/canvas/items/)
- **职责**：纯UI渲染组件，不包含业务逻辑
- **组件**：
  - nchor_item.py：节点端口（输入/输出锚点），支持悬停高亮和连接状态显示
  - 
ode_item.py：节点容器，管理标题、标签、选中状态
  - edge_item.py：连线条，绘制贝塞尔曲线，支持动态更新
- **设计原则**：
  - 不持有canvas引用
  - 通过回调函数通信
  - 专注于视觉呈现和交互反馈

**第二层：Core层** (ui/canvas/canvas_view.py)
- **职责**：画布核心管理和业务逻辑
- **包含**：
  - NodeCanvas类：主画布控制器（74.5KB，约1763行）
  - 节点/连线管理（CRUD操作）
  - 鼠标/键盘事件处理
  - 布局保存/加载
  - 缩放/平移控制
  - 框选/多选功能
- **关键特性**：
  - QGraphicsView + QGraphicsScene架构
  - VueFlow风格的无限画布体验
  - 支持5000x5000像素画布空间
  - 网格背景渲染
  - 自动保存机制（防抖500ms）

**第三层：兼容层** (ui/canvas_widget.py)
- **职责**：保持向后兼容性
- **实现**：Facade模式，重定向到新模块
- **代码量**：仅15行
- **迁移策略**：
  `python
  # 旧代码（仍然有效）
  from ui.canvas_widget import NodeCanvas
  
  # 新代码（推荐）
  from ui.canvas import NodeCanvas
  `

**第四层：模块导出** (ui/canvas/__init__.py, ui/canvas/items/__init__.py)
- **职责**：统一的导入接口
- **优势**：简化调用方代码，隐藏内部结构

##### **重构成果**

**代码指标对比**：

| 指标 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| **单文件大小** | 91.9KB | 74.5KB (core) + 分散items | ⬇️ 19% |
| **模块数量** | 1个 | 5个核心模块 | ⬆️ 5倍 |
| **代码行数** | ~2200行 | ~1763行 (core) + items | 持平 |
| **职责清晰度** | 混合 | 清晰分层 | ✅ 大幅提升 |
| **可测试性** | 困难 | 易于单元测试 | ✅ 显著提升 |
| **可维护性** | 低 | 高 | ✅ 显著提升 |

##### **验证结果**

**功能完整性检查**：
- ✅ 节点拖拽功能正常
- ✅ 锚点连线功能正常
- ✅ 贝塞尔曲线渲染正常
- ✅ 缩放/平移功能正常
- ✅ 框选/多选功能正常
- ✅ 布局保存/加载正常
- ✅ 右键菜单功能正常
- ✅ 节点配置对话框正常

**兼容性检查**：
- ✅ 旧导入方式仍可用：rom ui.canvas_widget import NodeCanvas
- ✅ 新导入方式可用：rom ui.canvas import NodeCanvas
- ✅ 所有现有功能无破坏性变更

**性能检查**：
- ✅ 画布渲染帧率无明显变化
- ✅ 内存占用无明显增加
- ✅ 节点操作响应速度保持一致

##### **影响文件**：
- ui/canvas/__init__.py - **新增**：模块导出接口
- ui/canvas/canvas_view.py - **新增**：核心视图和业务逻辑（1763行）
- ui/canvas/items/__init__.py - **新增**：图形项模块导出
- ui/canvas/items/anchor_item.py - **新增**：锚点项（输入/输出端口）
- ui/canvas/items/node_item.py - **新增**：节点容器项
- ui/canvas/items/edge_item.py - **新增**：连线条（贝塞尔曲线）
- ui/canvas_widget.py - **修改**：缩减至15行（Facade模式）
- ui/canvas/CANVAS_SPLIT_REPORT.md - **新增**：详细重构报告

##### **用户影响**：
- ✅ **零破坏性变更**：所有现有功能保持不变
- ✅ **稳定性提升**：更好的代码组织降低bug风险
- ✅ **未来开发更快**：模块化架构支持快速功能添加
- ✅ **文档更清晰**：清晰的分离使代码更易理解

##### **文档**：
- 完整技术细节：[ui/canvas/CANVAS_SPLIT_REPORT.md](ui/canvas/CANVAS_SPLIT_REPORT.md)

---

## 🆕 最近更新 (2026-05-19)

### 🔧 关键问题修复与增强

#### 1. **Rust 节点语言检测修复** 🦀
- **问题**：画布上的 Rust 节点显示为 "Unknown" 而非 "Rust"
- **根本原因**：`detect_language()` 方法只检查根目录下的 `main.rs`，但 Rust 项目使用 `src/main.rs` 结构
- **解决方案**：增强语言检测逻辑，同时检查 `src/main.rs` 和 `Cargo.toml` 文件
- **技术实现**：
  ```python
  # 修复前：只检查根目录
  elif os.path.exists(os.path.join(node_path, "main.rs")):
      return "Rust"
  
  # 修复后：检查标准 Rust 项目结构
  elif os.path.exists(os.path.join(node_path, "src", "main.rs")) or \
       os.path.exists(os.path.join(node_path, "Cargo.toml")):
      return "Rust"
  ```
- **影响文件**：
  - `ui/canvas_widget.py` - `NodeCanvas.detect_language()` 方法
- **用户影响**：✅ Rust 节点现在在画布上正确显示 "Rust" 标签

#### 2. **节点文件夹路径解析修复** 📁
- **问题**：点击"打开节点文件夹"时打开了错误的目录（如文档文件夹），而非实际的节点文件夹
- **根本原因**：节点路径未正确规范化，可能存储为相对路径，受工作目录变化影响
- **解决方案**：实现三层路径验证和规范化机制

##### **第一层：节点加载时的路径规范化** (`ui/main_window.py`)
- **增强的 `refresh_nodes()` 方法**：
  ```python
  # 确保项目路径是绝对路径
  project_path = os.path.abspath(self.current_project_path)
  nodes_dir = os.path.join(project_path, "nodes")
  
  # 规范化每个节点路径
  node_path = os.path.join(nodes_dir, item)
  node_path = os.path.abspath(node_path)  # 转换为绝对路径
  node_path = os.path.normpath(node_path)  # 规范化（处理 ..\ 等）
  ```
- **新增功能**：
  - ✅ 每个节点的详细加载日志（路径、存在状态）
  - ✅ 路径一致性验证
  - ✅ 自动修正不一致的路径
  - ✅ 显示加载的节点总数

##### **第二层：配置对话框中的路径验证** (`ui/property_panel.py`)
- **增强的 `NodeConfigDialog.open_node_folder()` 方法**：
  ```python
  # 确保路径是绝对路径且规范化
  original_path = self.node_path
  corrected_path = os.path.abspath(original_path)
  corrected_path = os.path.normpath(corrected_path)
  
  if original_path != corrected_path:
      print(f"⚠️  路径已修正:")
      print(f"   原始: {original_path}")
      print(f"   修正: {corrected_path}")
      self.node_path = corrected_path
  
  # 备用方案：从父窗口的 nodes_data 获取正确路径
  if not os.path.exists(self.node_path):
      if self.parent_window and hasattr(self.parent_window, 'nodes_data'):
          node_info = self.parent_window.nodes_data.get(self.node_name)
          if node_info and 'path' in node_info:
              correct_path = os.path.abspath(node_info['path'])
              correct_path = os.path.normpath(correct_path)
              if os.path.exists(correct_path):
                  self.node_path = correct_path
  ```
- **新增功能**：
  - ✅ 自动检测和修正路径
  - ✅ 从父窗口进行备用路径恢复
  - ✅ 全面的调试日志（路径类型、存在性、父目录等）
  - ✅ 用户友好的错误消息和故障排除提示

##### **第三层：节点列表中的路径验证** (`ui/node_list_panel.py`)
- **增强的 `NodeListPanel.open_node_folder()` 方法**：
  - 与配置对话框相同的路径验证和修正逻辑
  - 从主窗口的 nodes_data 进行备用路径恢复
  - 完整的调试信息输出

- **调试日志示例**：
  ```
  ============================================================
  🔍 [NodeConfigDialog] 打开节点文件夹
  🔍 节点名称: node_rust_test
  🔍 原始路径: D:\Project\nodes\node_rust_test
  🔍 最终路径: D:\Project\nodes\node_rust_test
  🔍 路径是否存在: True
  🔍 是否为目录: True
  🔍 父目录: D:\Project\nodes
  🔍 文件夹名称: node_rust_test
  🔍 当前工作目录: D:\Project
  🔍 期望的文件夹名: node_rust_test
  🔍 实际的文件夹名: node_rust_test
  🔍 名称匹配: True
  ✅ 已打开节点文件夹: D:\Project\nodes\node_rust_test
  ============================================================
  ```

- **修复前后对比**：
  | 方面 | 修复前 | 修复后 |
  |------|--------|--------|
  | **路径类型** | 可能是相对路径 | 强制绝对路径 + 规范化 |
  | **路径一致性** | 可能不一致 | 自动验证和修正 |
  | **错误恢复** | 无 | 多层级备用路径 |
  | **调试信息** | 无 | 详细的控制台日志 |
  | **用户体验** | 打开错误的文件夹 | 始终打开正确的节点文件夹 |

- **影响文件**：
  - `ui/main_window.py` - `MainWindow.refresh_nodes()` 方法
  - `ui/property_panel.py` - `NodeConfigDialog.open_node_folder()` 方法
  - `ui/node_list_panel.py` - `NodeListPanel.open_node_folder()` 方法
  - `diagnose_rust_node.py` - 新增 Rust 节点诊断工具
  - `RUST_NODE_PATH_FIX.md` - 详细的修复文档

- **使用说明**：
  1. 启动程序后，点击"刷新节点列表"按钮
  2. 查看控制台输出，确认所有节点路径正确加载
  3. 双击节点或右键 → "编辑配置"
  4. 点击"📁 打开节点文件夹"按钮
  5. 验证调试日志（以 🔍 开头的行）显示正确的路径

- **用户影响**：
  - ✅ 所有节点（Python、Rust、Node.js 等）现在都能打开正确的文件夹
  - ✅ 路径始终是绝对路径且规范化，不受工作目录影响
  - ✅ 路径缺失时的智能错误恢复
  - ✅ 全面的调试信息便于故障排除

---

## 🆕 之前的更新 (2026-05-18)

### ✨ 新增功能与优化

#### 1. **画布节点右键菜单增强 - 启动/停止节点** ⚡
- **功能**：在画布上右键点击节点时，添加动态的启动/停止节点选项，根据节点当前状态智能显示相应操作
- **设计理念**：**上下文感知的快捷操作**，让用户在画布上直接控制节点生命周期，无需切换到列表面板或配置对话框
- **核心特性**：
  - **状态感知菜单**：根据节点运行状态动态显示"▶️ 启动节点"或"⏹️ 停止节点"
  - **复用现有逻辑**：完全调用主窗口的 [start_selected_node_by_name](file://d:\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main\ui\main_window.py#L1010-L1064) 和 `stop_selected_node_by_name` 方法
  - **即时反馈**：操作完成后通过控制台日志和 Toast 通知告知用户结果
  - **异常处理**：完善的错误捕获和用户友好的提示信息
  
- **技术实现**：
  - **菜单重构**：在 `NodeCanvas.contextMenuEvent()` 中为节点菜单添加条件判断
  - **状态检测**：检查 `node_info['status'] == 'running'` 决定显示哪个选项
  - **新增方法**：
    - `start_single_node(node_name)` - 启动单个节点，复用主窗口启动逻辑
    - `stop_single_node(node_name)` - 停止单个节点，复用主窗口停止逻辑
  - **安全验证**：
    - 检查节点是否存在于 [nodes_data](file://d:\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main\ui\main_window.py#L0-L0)
    - 防止重复启动（已在运行时提示）
    - 防止无效停止（未运行时提示）
  
- **用户体验提升**：
  - ✅ **操作便捷**：在画布上直接右键即可启动/停止节点，减少操作步骤
  - ✅ **视觉清晰**：菜单项带有图标和明确文字，一目了然
  - ✅ **状态同步**：操作后立即更新节点指示灯颜色和状态文本
  - ✅ **容错性强**：误操作时有明确的提示信息，不会导致程序崩溃
  - ✅ **一致性高**：与节点列表、配置对话框中的启动/停止功能保持完全一致
  
- **使用场景**：
  ```
  场景 1：快速测试节点
  1. 在画布上找到需要测试的节点
  2. 右键点击 → 选择"▶️ 启动节点"
  3. 观察节点状态灯变为绿色
  4. 查看日志输出确认运行正常
  
  场景 2：批量管理节点
  1. 依次右键多个节点
  2. 根据需要启动或停止
  3. 实时观察各节点状态变化
  ```
  
- **影响文件**：
  - `ui/canvas_widget.py` - `NodeCanvas.contextMenuEvent()` 方法（修改节点右键菜单）
  - `ui/canvas_widget.py` - 新增 `start_single_node()` 和 `stop_single_node()` 方法

#### 2. **节点配置对话框全新布局设计** 🎨
- **功能**：重新设计节点配置对话框，采用横向矩形窗口布局，左侧上下两个窗口分别显示完整的 config.json 和 output.json（可编辑），右侧为节点信息和控制按钮
- **设计理念**：**直观JSON编辑 + 快速操作分离**，将配置数据和输出数据以纯文本形式展示，提升编辑灵活性和可视化程度
- **核心特性**：
  - **横向宽屏布局**：窗口尺寸调整为 1200x700px，更适合现代显示器
  - **左右分栏设计**：左侧占 2/3 空间用于 JSON 编辑，右侧占 1/3 空间用于控制和信息展示
  - **完整JSON编辑**：不再使用分散的表单字段，直接编辑完整的 JSON 文件内容
  - **深色主题编辑器**：Consolas 字体，VSCode 风格配色（#1e1e1e 背景，#d4d4d4 文字）
  
- **左侧区域详解**：
  - **上半部分 - config.json 编辑器**：
    - 📝 **完整配置编辑**：直接查看和修改所有配置项（node_name、listen_upper_file、output_file、output_type、filter 等）
    - 🔄 **实时刷新**：从磁盘重新加载最新的 config.json 文件
    - 💾 **智能保存**：
      - 自动格式化 JSON（2空格缩进，ensure_ascii=False）
      - JSON 格式验证，错误时提供警告但仍允许强制保存
      - 同步更新内存数据（nodes_data）
      - 自动同步画布上的节点显示
    
  - **下半部分 - output.json 编辑器**：
    - 📊 **输出数据监控**：实时查看节点处理结果
    - ✏️ **可编辑模式**：支持手动修改输出数据进行测试
    - 🔄 **快速刷新**：一键重新加载文件内容
    - 💾 **安全保存**：格式验证 + 用户确认机制
  
- **右侧区域详解**：
  - **ℹ️ 节点信息卡片**：
    - 节点名称（粗体显示）
    - 节点路径（自动换行，适应长路径）
  
  - **🎮 节点控制组**：
    - ▶️ **启动节点**：绿色按钮，大号字体（13px），加粗
    - ⏹️ **停止节点**：红色按钮，醒目提示
    - *(间距 10px)*
  
  - **🔧 快捷操作组**：
    - 📁 **打开节点文件夹**：橙色按钮
    - 💻 **打开命令行**：蓝色按钮，自动激活虚拟环境
    - 🔧 **打开 VSCode**：深蓝色按钮 (#007ACC)，创建工作区文件
  
- **技术实现**：
  - **布局重构**：
    - 主容器：`QHBoxLayout` 实现左右分栏
    - 左侧：`QVBoxLayout` 包含两个 `QGroupBox`（config.json 和 output.json）
    - 右侧：`QVBoxLayout` 包含三个 `QGroupBox`（信息、控制、快捷操作）
    - 弹性比例：左侧 stretch=2，右侧 stretch=1
  
  - **新增方法**：
    - `load_config_json()` - 从磁盘加载并格式化显示 config.json
    - `save_config_from_editor()` - 从编辑器保存 config.json，包含格式验证和内存同步
  
  - **删除的方法**：
    - ❌ `add_filter_rule()` - 不再需要表格管理 Filter
    - ❌ `delete_filter_rule()` - 直接在 JSON 中编辑
    - ❌ 旧的表单字段（`listen_file_edit`, `output_type_edit`, `filter_table`）
  
  - **导入修复**：添加缺失的 `QHBoxLayout` 导入
  
- **用户体验提升**：
  - ✅ **灵活性增强**：可以直接复制粘贴配置块，批量修改多个字段
  - ✅ **可视化提升**：完整的 JSON 结构一目了然，便于理解配置关系
  - ✅ **效率提高**：无需在多个表单字段间切换，直接文本编辑更快速
  - ✅ **容错性强**：JSON 格式错误时提供警告，但仍允许保存（适用于特殊场景）
  - ✅ **布局合理**：横向宽屏更适合现代显示器，减少滚动次数
  - ✅ **操作集中**：右侧控制按钮垂直排列，快速访问常用功能
  
- **影响文件**：
  - `ui/property_panel.py` - `NodeConfigDialog` 类（完全重构 init_ui 方法）
  - `ui/canvas_widget.py` - 添加 `mouseDoubleClickEvent()` 方法触发配置对话框

#### 3. **节点列表拖拽移动与智能分组** 🎯
- **功能**：在节点列表中支持拖拽移动节点到不同组，画布上节点重叠时自动生成新组，节点嵌套操作自动转换为创建新组，空组自动删除
- **设计理念**：**类似Photoshop图层管理**，节点组之间是平行关系，没有嵌套结构。用户看似在进行嵌套操作，系统自动转换为创建新组
- **核心特性**：
  - **拖拽移动**：在节点列表中直接拖拽节点到目标组或根级别
  - **智能分组**：画布上两个节点重叠超过50%时，自动创建新的节点组并将它们加入
  - **嵌套转分组**：当用户尝试将节点拖到另一个节点上（嵌套）时，根据目标节点状态智能处理：
    - 目标节点在组中 → 直接融入该组
    - 目标节点不在组中 → 创建新组包含所有节点
  - **空组清理**：检测到空节点组时自动删除，无需用户确认
  - **防堆叠限制**：画布上严格禁止节点堆叠，拖动节点时如果会与其他节点重叠则阻止移动
  
- **拖拽移动实现**（完全自主控制）：
  - **启用拖拽**：为 `QTreeWidget` 启用 `DragEnabled`、`InternalMove` 和 `AcceptDrops`
  - **重写dropEvent**：拦截所有拖放操作，不依赖 `rowsMoved` 信号
  - **智能处理**：
    - 拖入组标题：调用 `add_nodes_to_group()` 将节点添加到目标组
    - 拖到空白处：从原组移除节点，变为独立节点
    - 拖到组内节点：检查目标节点的组归属，直接融入或创建新组
    - 拖到根级别节点：创建新组包含所有涉及的节点
  - **原子性操作**：先完成所有数据变更，最后统一刷新一次UI，避免中间状态
  - **实时反馈**：移动完成后刷新列表，显示Toast通知
  
- **嵌套转分组逻辑**（核心创新）：
  - **拦截拖放**：重写 `dropEvent`，在拖放发生前检查目标类型
  - **智能判断**：
    ```python
    if 目标是节点:
        if 目标节点在某个组中:
            直接将拖拽节点加入该组  # 融入现有组
        else:
            创建新组包含所有节点  # 创建平行组
    elif 目标是空白处:
        将节点移出所有组  # 成为独立节点
    ```
  - **用户体验**：用户感觉像是在创建嵌套，实际上得到了更合理的平行组结构
  - **防抖机制**：使用定时器延迟创建，避免频繁操作
  
- **自动创建组逻辑**（画布重叠检测）：
  - **重叠检测**：在 `NodeItem.itemChange()` 中监听位置变化
  - **面积计算**：计算两个节点的重叠面积比例（阈值50%）
  - **去重判断**：检查重叠节点是否已在同一组，避免重复创建
  - **智能命名**：自动生成唯一组名（Group_1, Group_2, ...）
  - **随机配色**：为新组分配随机颜色，便于视觉区分
  - **即时同步**：创建后立即刷新节点列表和画布显示
  - **防抖优化**：使用定时器延迟500ms执行，等待用户停止拖拽
  
- **防堆叠限制**（新增）：
  - **前置检测**：在 `ItemPositionChange` 阶段检测新位置是否会导致堆叠
  - **精确计算**：计算节点在新位置的scene坐标矩形，与其他节点进行碰撞检测
  - **阻止移动**：如果检测到会堆叠，返回当前位置，拒绝位置改变
  - **智能添加**：从节点列表添加节点到画布时，自动计算不重叠的位置
    - **多策略候选位置生成**：优先在现有节点周围放置，其次使用网格扫描
    - **实时碰撞检测**：遍历所有现有节点，确保新位置不会重叠
    - **保底方案**：如果所有候选位置都重叠，自动放置在最右下角
  - **用户体验**：拖动节点时无法与其他节点重叠，添加节点时自动避开现有节点，保持画布整洁有序
  
- **空组清理机制**（自动化）：
  - **触发时机**：每次节点移动后自动检查
  - **智能识别**：遍历所有组，找出节点数为0的空组
  - **自动删除**：检测到空组时立即自动删除，无需用户确认
  - **统一刷新**：先执行所有数据操作，最后统一刷新一次列表
  - **友好提示**：通过Toast显示删除的空组数量
  
- **技术实现**：
  - 新增/修改方法：
    - `_intercept_drop_event()` - 拦截并智能处理所有拖放操作（核心方法）
    - `_get_dragged_nodes_from_event()` - 从拖拽事件中提取节点列表
    - `_create_group_for_dragged_nodes()` - 为拖拽涉及的节点创建新组
    - `on_nodes_moved()` - 处理节点拖拽移动事件（备用，主要逻辑在_intercept_drop_event）
    - `_move_nodes_to_group()` - 将节点移动到指定组（优化刷新策略）
    - `_move_nodes_to_ungrouped()` - 将节点移出组（优化刷新策略）
    - `_cleanup_empty_groups(refresh=True)` - 清理空节点组（支持控制刷新）
    - `_check_node_overlap_and_create_group()` - 检测节点重叠（NodeItem类，添加防抖）
    - `_delayed_create_group()` - 延迟创建组（NodeItem类，防抖执行）
    - `_create_group_for_overlapping_nodes()` - 为重叠节点创建组（NodeItem类）
  - 架构优化：
    - **完全自主控制**：不依赖Qt的默认拖拽行为，所有逻辑自己处理
    - **原子性操作**：先完成所有数据变更，再统一刷新UI，避免中间状态
    - **参数化刷新**：`_cleanup_empty_groups()` 支持 `refresh` 参数，由调用者决定何时刷新
    - **异常处理**：使用try-except包裹拖拽处理逻辑，确保稳定性
  - 非侵入式设计：仅在现有方法中添加新功能调用，不修改原有核心逻辑
  
- **用户体验提升**：
  - ✅ 直观的拖拽操作，无需右键菜单即可完成节点分组
  - ✅ 智能的嵌套转换，用户操作简单，系统自动优化数据结构
  - ✅ 自动清理空组，保持节点列表整洁有序，无需手动维护
  - ✅ 清晰的视觉反馈和操作提示，每个步骤都有日志输出
  - ✅ 原子性刷新，避免界面闪烁和中间状态
  
- **影响文件**：
  - `ui/node_list_panel.py` - `NodeListPanel` 类（拖拽拦截、智能分组、空组清理）
  - `ui/canvas_widget.py` - `NodeItem` 类（重叠检测、防抖创建组）

#### 4. **节点列表多选右键菜单优化** 📋
- **功能**：重构节点列表面板的多选右键菜单逻辑，所有功能同步作用到所有选中节点
- **设计理念**：遵循"上下文感知的右键菜单设计规范"，根据选中状态动态显示不同的菜单内容
- **优化方案**：
  - **单选模式**：显示针对单个节点的完整操作菜单（添加画布、移动组、启动/停止、重命名、打开文件夹、查看日志、编辑配置、删除等）
  - **多选模式**：仅显示批量操作菜单，所有功能自动同步应用到所有选中节点
  
- **新增批量功能**：
  - **批量添加到画布**：一次性将多个选中节点添加到画布，自动跳过已在画布上的节点
  - **批量移动到组**：将所有选中节点移动到指定组
  - **批量从组移除**：当所有选中节点在同一组时，提供批量移除选项
  - **批量启动/停止**：同时启动或停止所有选中节点（已有功能，保留）
  - **批量打开文件夹**：同时打开所有选中节点的文件夹
  - **批量查看日志**：合并显示所有选中节点的日志内容，便于对比分析
  - **批量编辑配置**：依次打开每个节点的配置对话框进行编辑
  - **批量删除**：同时删除所有选中节点及其文件（已有功能，增强确认提示）
  
- **技术实现**：
  - 重构 `_show_node_context_menu()` 方法，使用条件分支区分单选和多选模式
  - 新增7个批量操作方法：
    - `batch_add_nodes_to_canvas()` - 批量添加到画布
    - `batch_open_node_folders()` - 批量打开文件夹
    - `batch_view_node_logs()` - 批量查看日志
    - `batch_edit_node_configs()` - 批量编辑配置
    - `_get_common_group()` - 获取共同组（辅助方法）
    - `batch_remove_nodes_from_group()` - 批量从组移除
  - 智能判断：检测选中节点是否在同一组，动态显示相关菜单项
  - 用户友好：所有批量操作提供详细的成功/失败统计和Toast通知
  
- **用户体验提升**：
  - ✅ 多选时菜单更简洁，只显示相关的批量操作
  - ✅ 避免误操作：不会在多选时意外执行单节点操作
  - ✅ 提高效率：一次操作即可处理多个节点
  - ✅ 反馈清晰：明确显示操作的节点数量和结果
  
- **影响文件**：`ui/node_list_panel.py` - `NodeListPanel` 类

#### 5. **画布框选功能优化** 📦
- **功能**：严格限制框选功能只能在完全空白的画布区域触发，避免在节点上误触框选
- **问题背景**：之前框选功能的判断条件不够严格，可能在点击节点或其他交互项时意外触发框选模式，影响正常的节点选择和拖拽操作
- **优化方案**：
  - **严格空白检测**：修改 `mousePressEvent` 中的框选触发条件，只有当 `item is None` 时才允许开始框选
  - **移除宽松条件**：删除原有的 `or` 分支判断，确保不会在任何 QGraphicsItem 上触发框选
  - **明确日志提示**：添加"（空白区域）"标识，便于调试和用户理解
  
- **技术实现**：
  - 修改前：`if item is None or (not isinstance(item, NodeItem) and ...)`
  - 修改后：`if item is None:` （仅当完全空白时）
  - 如果点击了任何项（节点、连线、锚点等），直接调用 `super().mousePressEvent(event)` 让默认行为处理
  - 保持与其他交互模式（Ctrl+单击多选、平移模式）的互斥性
  
- **用户体验提升**：
  - ✅ 点击节点时正常选中/拖拽，不会意外进入框选模式
  - ✅ 点击连线或锚点时正常响应，不触发框选
  - ✅ 只有在真正空白的画布区域长按才会显示框选矩形
  - ✅ 操作更加精准，减少误操作
  
- **影响文件**：`ui/canvas_widget.py` - `NodeCanvas.mousePressEvent()` 方法

#### 6. **画布节点双击打开配置** ⚙️
- **功能**：在画布上双击节点直接打开配置对话框，快速编辑节点配置
- **实现细节**：
  - **双击检测**：监听画布的 `mouseDoubleClickEvent` 事件
  - **目标识别**：通过 `itemAt()` 方法检测双击位置是否为节点项（NodeItem）
  - **配置加载**：自动从父窗口获取节点的配置信息和路径
  - **对话框展示**：打开完整的 [NodeConfigDialog](file://d:\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main\ui\property_panel.py#L17-L490)，包含：
    - 基本配置编辑（监听文件、输出类型等）
    - Filter注意力规则管理
    - Output.json 内容查看和编辑
    - 节点控制按钮（启动/停止/打开文件夹/命令行/VSCode工作区）
    - 配置保存功能
  
- **技术实现**：
  - 在 `NodeCanvas` 类中新增 `mouseDoubleClickEvent()` 方法
  - 使用 `isinstance(item, NodeItem)` 精确判断双击目标
  - 调用现有的 `NodeConfigDialog` 组件，复用已有功能
  - 遵循Qt事件处理规范：处理后调用 `event.accept()` 并 `return`
  - 非侵入式设计：仅新增方法，不修改现有代码逻辑
  
- **使用方式**：
  ```
  1. 在画布上找到需要配置的节点
  2. 双击该节点
  3. 系统自动弹出配置对话框
  4. 编辑配置后点击"保存配置"按钮
  5. 配置立即生效并同步到内存数据
  ```
  
- **影响文件**：`ui/canvas_widget.py` - `NodeCanvas` 类
- **用户价值**：简化配置编辑流程，无需通过右键菜单或列表面板，提升操作效率

#### 7. **节点列表多选批量删除** 🗑️
- **功能**：在节点列表面板中支持通过 Shift/Ctrl 多选节点后批量删除
- **实现细节**：
  - **多选支持**：按住 Shift 或 Ctrl 键选择多个节点（已有功能）
  - **右键菜单增强**：选中多个节点时，右键菜单显示"🗑️ 删除选中的 X 个节点"选项
  - **二次确认机制**：删除前弹出确认对话框，列出所有待删除的节点名称（最多显示10个）
  - **完整清理流程**：
    - 自动停止运行中的节点进程
    - 删除节点文件夹及所有文件
    - 从节点组中移除引用
    - 从内存数据中删除
    - 从画布中移除节点显示
  - **详细结果反馈**：显示成功/失败的统计信息，失败节点单独列出
  - **Toast 通知**：操作完成后通过 Toast 提示用户
  
- **技术实现**：
  - 新增 `batch_delete_nodes()` 方法处理批量删除逻辑
  - 在 `_show_node_context_menu()` 中添加条件判断，当选中多个节点时显示批量删除选项
  - 完善的异常处理，确保单个节点删除失败不影响其他节点
  - 遵循项目规范：提供明确的二次确认，防止误操作
  
- **使用方式**：
  ```
  1. 在节点列表面板中，按住 Shift 或 Ctrl 键选择多个节点
  2. 在任意选中的节点上右键点击
  3. 选择 "🗑️ 删除选中的 X 个节点"
  4. 确认删除操作
  5. 系统自动完成所有节点的清理工作
  ```
  
- **影响文件**：`ui/node_list_panel.py` - `NodeListPanel` 类
- **用户价值**：提高节点管理效率，简化批量清理操作，降低误删风险

#### 8. **窗口关闭进程检测与管理** 🛑
- **功能**：在关闭应用时智能检测运行中的节点，并提供友好的确认对话框
- **实现细节**：
  - **自动检测**：扫描 `nodes_data` 中所有节点，识别状态为 'running' 且有活跃进程的节点
  - **智能提示**：清晰显示正在运行的节点列表（最多显示 10 个，超出的用省略号表示）
  - **三选项对话框**：
    - **是**：强制停止所有运行中的节点并关闭窗口（默认选项，确保安全）
    - **否**：允许节点在后台继续运行，但关闭窗口
    - **取消**：中止关闭操作，返回应用程序继续使用
  - **跨平台进程终止**：
    - Windows：优雅终止 → CTRL_BREAK_EVENT → 超时保护下的强制杀死
    - Linux/macOS：向进程组发送 SIGTERM → 必要时使用 SIGKILL
  - **健壮的错误处理**：单个节点失败不影响其他节点；正确清理所有进程引用
  - **UI 同步更新**：批量操作后自动更新节点列表面板和画布显示
  - **用户反馈**：通过 Toast 通知告知用户操作结果（停止了多少节点或有多少节点在后台运行）
  
- **技术实现**：
  - 增强 `BNOSMainWindow.closeEvent()` 方法，添加检测逻辑
  - 新增 `_force_stop_all_nodes()` 辅助方法用于批量进程终止
  - 遵循外部进程管理架构规范
  - 与现有的节点生命周期管理保持一致
  
- **用户工作流**：
  ```
  用户点击窗口关闭按钮（X）
  ↓
  系统检测到 3 个运行中的节点：Node_A, Node_B, Node_C
  ↓
  弹出对话框："以下 3 个节点正在运行... 请选择操作："
  ↓
  用户选择：
    • 是 → 停止所有节点，关闭窗口
    • 否 → 节点继续在后台运行，关闭窗口
    • 取消 → 窗口保持打开，用户继续工作
  ```
  
- **使用场景**：
  - ✅ **防止误关闭**：用户误点关闭时可以取消操作
  - ✅ **后台处理**：允许长时间运行的任务在关闭 GUI 后继续执行
  - ✅ **安全关闭**：确保退出前干净地终止所有进程
  - ✅ **灵活性**：三个选项覆盖所有可能的用户意图
  
- **技术亮点**：
  - 默认选择"是"，采用安全第一的策略
  - 正确的资源清理，防止僵尸进程
  - 异常处理确保即使某些进程无法停止也能保持稳定
  - 控制台日志提供详细的操作跟踪，便于调试
  
- **影响文件**：
  - `ui/main_window.py` - `BNOSMainWindow.closeEvent()` 和新增的 `_force_stop_all_nodes()` 方法
  
- **代码质量**：
  - 遵循项目的外部进程管理规范
  - 跨平台兼容，采用操作系统特定的策略
  - 关注点清晰分离（检测逻辑 vs. 终止逻辑）
  - 全面的错误处理和用户反馈

---

## 🆕 最近更新 (2026-05-17)

### ✨ 新增功能与优化

#### 1. **增强型 Rust 节点生成器** 🔧
- **功能**：完全重写的 Rust 节点生成系统，具备自愈能力
- **实现细节**：
  - **自动环境检测**：启动时自动检查 Rust 工具链和编译产物
  - **自我修复机制**：检测到缺失或损坏的二进制文件时，自动使用 `cargo build --release` 重新构建
  - **双二进制架构**：生成两个可执行文件：
    - `{node_name}`：主处理逻辑（单次执行模式）
    - `{node_name}_listener`：带自愈功能的持久监听器（持续监控模式）
  - **智能构建系统**：发布模式优化，启用 LTO、codegen-units=1 和符号剥离以获得最佳性能
  - **跨平台支持**：在 Windows (.exe)、macOS 和 Linux 上无缝运行
  
- **技术实现**：
  - **模块化源码结构**：
    - `src/main.rs`：核心业务逻辑，包含 JSON 输入输出处理
    - `src/listener.rs`：文件监控循环，带环境自愈功能
    - `src/packet.rs`：标准化输出数据包结构（成功/错误响应）
  - **配置管理**：自动生成 `config.json`，包含过滤规则、上下游路径和输出类型设置
  - **启动脚本**：平台特定的启动器（Windows 的 `start.bat`，Unix 的 `start.sh`），内置环境验证
  - **日志系统**：自动在 `logs/listener.log` 中记录带时间戳的日志
  
- **用户工作流**：
  ```bash
  # 生成新的 Rust 节点
  python tools/rust_create_node.py my_processor
  
  # 进入目录并实现逻辑
  cd node_rust_my_processor
  # 编辑 src/main.rs 添加自定义处理逻辑
  
  # 构建并运行（如需要会自动修复）
  start.bat  # Windows
  ./start.sh # macOS/Linux
  ```
  
- **性能优势**：
  - 比 Python 等效代码**快 10-100 倍**（编译型语言特性）
  - **内存安全**：编译器强制的所有权模型防止数据竞争
  - **零成本抽象**：高级易用性与低级控制相结合
  - **最小运行时**：无垃圾回收暂停，延迟可预测
  
- **自愈能力**：
  - ✅ 执行前检查 `rustc` 和 `cargo` 是否可用
  - ✅ 验证 `target/release/` 目录是否存在
  - ✅ 通过尝试执行来验证二进制文件完整性
  - ✅ 自动清理损坏的编译产物
  - ✅ 使用详细的错误报告重新构建项目
  - ✅ 修复成功后继续运行，无需人工干预
  
- **影响文件**：
  - `tools/rust_create_node.py` - 完整的节点生成器，包含 1083 行模板代码
  - `node_rust_9/` - 展示架构的示例实现
  
- **技术亮点**：
  - 使用 `serde` 和 `serde_json` 进行健壮的 JSON 序列化/反序列化
  - 集成 chrono 库实现精确的时间戳日志
  - 采用基于线程的轮询机制，可配置的睡眠间隔（默认 200ms）
  - 通过 config.json 规则支持注意力机制过滤
  - 结构化错误包实现的优雅错误处理

---

## 🆕 最近更新 (2026-05-08)

### ✨ 新增功能与优化

#### 1. **VSCode 工作区集成** 🔧
- **功能**：在节点配置对话框中新增"打开为 VSCode 工作区"按钮
- **实现细节**：
  - 自动为节点文件夹生成标准的 `.code-workspace` 配置文件
  - 智能配置 Python 虚拟环境解释器路径（跨平台支持：Windows/macOS/Linux）
  - 自动排除 `__pycache__` 和 `.pyc` 文件，保持工作区整洁
  - 一键调用 VSCode 以工作区模式打开节点目录
- **技术实现**：采用非侵入式设计，仅新增 `open_vscode_workspace()` 函数，未修改任何现有代码
- **影响文件**：`ui/property_panel.py` - `NodeConfigDialog` 类
- **用户价值**：简化开发流程，提供即时的源代码访问能力，并自动配置正确的开发环境

#### 2. **VSCode 工作区功能优化** ⚡
- **智能检测机制**：在尝试打开前预先检测 VSCode 是否已安装
  - Windows 系统：使用 `where code` 命令检测
  - macOS/Linux 系统：使用 `which code` 命令检测
  - 超时保护：3秒超时，避免长时间等待
- **相对路径配置**：
  - 工作区文件夹使用 `"path": "."`（相对路径）
  - Python 解释器路径使用 `${workspaceFolder}` 变量
  - 确保项目可移植性，支持安全迁移
- **友好的用户交互**：
  - 未检测到 VSCode 时：显示确认对话框，提供清晰指引
  - 用户可选择仍创建工作区文件（供将来使用）
  - 提供安装提示："将 'code' 命令添加到 PATH"
  - 尊重用户选择：可选择取消，不创建任何文件
- **跨平台支持**：在 Windows、macOS、Linux 上无缝运行
- **增强的反馈信息**：根据 VSCode 是否可用显示不同的成功提示
  - 已安装 VSCode："✅ 已创建并自动打开"
  - 未安装 VSCode："✅ 已创建，安装 VSCode 后双击即可打开"
- **技术改进**：将检测逻辑分离为独立的 `_check_vscode_installed()` 方法，提高可维护性

---

## 🆕 最近更新 (2026-05-07)

### ✨ 新增功能与优化

#### 1. **连线锚点位置修复** 🔧
- **问题**：连线在拖动时显示正确，但连接后锚点位置偏移到状态指示灯上
- **修复**：改用 `sceneBoundingRect().center()` 直接获取锚点几何中心，确保连线始终连接到锚点中心
- **影响文件**：`ui/canvas_widget.py` - `EdgeItem.update_path()` 方法
- **技术改进**：避免手动计算偏移量，提高坐标计算的准确性和可靠性

#### 2. **窗口置顶行为优化** 🪟
- **问题**：节点列表、Toast通知和进度窗口在切换应用后仍然全局置顶，覆盖其他软件窗口
- **修复**：移除所有不必要的 `WindowStaysOnTopHint` 标志，保留 `Qt.WindowType.Tool` 标志
- **影响文件**：
  - `ui/node_list_panel.py` - 节点列表面板
  - `ui/main_window.py` - ToastNotification 和 ProgressFloatingWindow
- **效果**：工具窗口只在应用内部保持层级关系，不会干扰其他应用程序的使用

#### 3. **最佳实践记录** 📚
- 创建记忆知识库，记录 QGraphicsItem 锚点位置计算的最佳实践
- 记录 Qt 工具窗口置顶问题的解决方案
- 为后续开发提供技术参考和规范指导

### 🎯 技术亮点

- **更准确的坐标计算**：使用 `sceneBoundingRect().center()` 替代 `scenePos() + offset`
- **更好的用户体验**：工具窗口遵循标准 Windows 窗口行为，不覆盖其他应用
- **代码质量提升**：通过记忆系统沉淀最佳实践，避免重复踩坑

