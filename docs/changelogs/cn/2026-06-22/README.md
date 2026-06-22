# 【2026-06-22】V2.0.19 - 连线渲染矢量轮廓填充、高 DPI 支持、画布分辨率自定义、脚本目录重构与节点列表 Dock 持久化修复

## 更新总览

**本次更新包含 5 个子模块变更**：

| 编号 | 模块 | 说明 | 详情 |
|------|------|------|------|
| 01 | 连线渲染矢量轮廓填充 | QPainterPathStroker 将线条转为闭合轮廓并用 QBrush 填充 | [→](01_连线渲染矢量轮廓填充.md) |
| 02 | 高 DPI 屏幕适配 | AA_EnableHighDpiScaling、AA_UseHighDpiPixmaps | [→](02_高DPI屏幕适配.md) |
| 03 | 画布分辨率设置 | 设置对话框新增「渲染」标签页，支持预设/自定义分辨率与抗锯齿开关 | [→](03_画布分辨率自定义.md) |
| 04 | restart_helper 脚本目录迁移 | `restart_helper.py` 从根目录迁入 `scripts/`，同时同步更新相关路径与技术文档 | [→](04_restart_helper脚本目录迁移.md) |
| 05 | 节点列表 Dock 加载与持久化修复 | `NodeListDockPanel.set_project_path` 同步调用 `NodeGroupManager`；修复 `self.node_list_dock` 空引用；主窗口启动/打开项目时 Dock 不再显示空白 | [→](05_节点列表Dock加载与持久化修复.md) |

---

## 变更统计

| 变更类型 | 数量 | 涉及文件 |
|----------|------|---------|
| **修改** | 9+1 | `ui/canvas/items/edge_item.py`、`bnos_console.py`、`ui/canvas/canvas_process.py`、`ui/canvas/canvas_view.py`、`ui/dialogs/settings_dialog.py`、`ui/core/app_config.py`、`ui/core/strings_cn.json`、`ui/core/strings_en.json`、`ui/canvas/mixins/canvas_connections.py`；以及 4 篇 `docs/` 技术文档中的路径引用 |
| **新增** | 1 | `scripts/restart_helper.py`（从根目录迁入，内容保持不变） |
| **删除** | 1 | `restart_helper.py`（旧根位置） |

## 全部变更文件

| 文件 | 变更 | 所属模块 |
|------|------|---------|
| `ui/canvas/items/edge_item.py` | `paint()` 改造：Antialiasing + SmoothPixmapTransform；QPainterPathStroker 矢量轮廓填充；EdgeItem/TempEdgeItem/EdgeArrowItem 全部 NoCache | 01_连线渲染 |
| `bnos_console.py` | 创建 QApplication 之前 `setAttribute(AA_EnableHighDpiScaling, True)` 与 `AA_UseHighDpiPixmaps` | 02_DPI |
| `ui/canvas/canvas_process.py` | 子进程同样设置高 DPI 属性，确保独立画布进程也支持高 DPI | 02_DPI |
| `ui/canvas/canvas_view.py` | `NodeCanvas` 初始化时读取 `AppConfig("rendering")` 的 `canvas_width/canvas_height/antialiasing`，并应用到 `setSceneRect` 和 `setRenderHint` | 03_分辨率 |
| `ui/dialogs/settings_dialog.py` | 新增「渲染」标签页：5 个预设分辨率按钮 + 自定义宽高输入 + 抗锯齿开关；确定后提示重启生效 | 03_分辨率 |
| `ui/core/app_config.py` | 默认配置新增 `rendering` 对象：`{canvas_width: 5000, canvas_height: 5000, antialiasing: true}` | 03_分辨率 |
| `ui/core/strings_cn.json` | 新增 `settings.rendering.title`、`preset_1000/2000/5000/8000/10000`、`custom`、`width`、`height`、`px`、`antialiasing`、`restart_tip` 等翻译键 | 03_分辨率 |
| `ui/core/strings_en.json` | 新增上述翻译键对应的英文文本 | 03_分辨率 |
| `ui/canvas/mixins/canvas_connections.py` | `TempEdgeItem` 创建统一使用填充渲染；`setCacheMode(NoCache)` | 01_连线渲染 |
| `scripts/restart_helper.py` | 从根目录迁入 `scripts/`，内容与功能保持不变 | 04_脚本目录重构 |
| `bnos_console.py` | 定位 `restart_helper.py` 的路径由 `"restart_helper.py"` 改为 `os.path.join("scripts", "restart_helper.py")` | 04_脚本目录重构 |
| `docs/BNOS_文件结构图.md` | 增加 `scripts/` 节点，`restart_helper.py` 归入其子节点 | 04_脚本目录重构 |
| `docs/BNOS_架构图.md` | 流程图中的 `restart_helper.py` 改为 `scripts/restart_helper.py` | 04_脚本目录重构 |
| `docs/BNOS_技术分析报告.md` | LOC 表格中文件名同步为 `scripts/restart_helper.py` | 04_脚本目录重构 |
| `docs/BNOS_项目优化分析报告.md` | 根目录树形展示与 7.4 小节文件引用同步 | 04_脚本目录重构 |