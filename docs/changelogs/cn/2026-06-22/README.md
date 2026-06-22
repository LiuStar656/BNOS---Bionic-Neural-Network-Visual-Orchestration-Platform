# 【2026-06-22】V2.0.19 - 连线渲染矢量轮廓填充、高 DPI 支持与画布分辨率自定义

## 更新总览

**本次更新包含 3 个子模块变更**：

| 编号 | 模块 | 说明 | 详情 |
|------|------|------|------|
| 01 | 连线渲染矢量轮廓填充 | QPainterPathStroker 将线条转为闭合轮廓并用 QBrush 填充 | [→](01_连线渲染矢量轮廓填充.md) |
| 02 | 高 DPI 屏幕适配 | AA_EnableHighDpiScaling、AA_UseHighDpiPixmaps | [→](02_高DPI屏幕适配.md) |
| 03 | 画布分辨率设置 | 设置对话框新增「渲染」标签页，支持预设/自定义分辨率与抗锯齿开关 | [→](03_画布分辨率自定义.md) |

---

## 变更统计

| 变更类型 | 数量 | 涉及文件 |
|----------|------|---------|
| **修改** | 9 | `ui/canvas/items/edge_item.py`、`bnos_console.py`、`ui/canvas/canvas_process.py`、`ui/canvas/canvas_view.py`、`ui/dialogs/settings_dialog.py`、`ui/core/app_config.py`、`ui/core/strings_cn.json`、`ui/core/strings_en.json`、`ui/canvas/mixins/canvas_connections.py` |

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