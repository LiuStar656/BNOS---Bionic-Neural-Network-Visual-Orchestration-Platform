# 【2026-06-20】V2.0.18 - 浮动面板系统完善、预设节点库重构、翻译与 UI 统一化

## 更新总览

**本次更新包含 6 个子模块变更**：

| 编号 | 模块 | 说明 | 详情 |
|------|------|------|------|
| 01 | 性能分析面板修复 | ChartCanvas 自定义绘制、QPainter 导入修复、拖动暂停刷新 | [→](01_性能分析面板修复.md) |
| 02 | 调试面板翻译补全 | 17 个中英文翻译键补全 | [→](02_调试面板翻译补全.md) |
| 03 | 预设节点库重构 | 空壳模板 → 完整 .bnos 打包、PresetLibraryDialog | [→](03_预设节点库重构.md) |
| 04 | IPC 核心进程命令扩展 | node.stop_all、node.detect_running | [→](04_IPC核心进程命令扩展.md) |
| 05 | 轮询管理器动态调频 | CPU 负载自适应 1s/2s/4s 间隔 | [→](05_轮询管理器动态调频.md) |
| 06 | 翻译键值全面修订 | 3 处错配修复、29 个新增键、17 个废弃键清理 | [→](06_翻译键值全面修订.md) |

---

## 变更统计

| 变更类型 | 数量 | 涉及文件 |
|----------|------|---------|
| **新增** | 4 | `preset_library_dialog.py`、`node_templates/`、`docs/changelogs/cn/2026-06-20/*`、`docs/changelogs/en/2026-06-20/*` |
| **删除** | 2 | `template_selector_dialog.py`、`node_template_manager.py` |
| **修改** | 14 | `performance_panel.py`、`debug_panel.py`、`_template.py`、`canvas_menus.py`、`panel.py`、`application_context.py`、`builtin_view_actions.py`、`core_process.py`、`polling_manager.py`、`floating_panel.py`、`import_export_manager.py`、`packager.py`、`strings_cn.json`、`strings_en.json` |

## 全部变更文件

| 文件 | 变更 | 所属模块 |
|------|------|---------|
| `ui/panels/performance_panel.py` | 新增 `ChartCanvas`，修复导入，覆写拖动钩子 | 01_性能 |
| `ui/panels/debug_panel.py` | i18n 键名引用更新 | 02_调试 |
| `ui/dialogs/preset_library_dialog.py` | **新增** — 预设节点库对话框 | 03_预设库 |
| `ui/dialogs/template_selector_dialog.py` | **删除** | 03_预设库 |
| `ui/core/node_template_manager.py` | **删除** | 03_预设库 |
| `ui/core/actions/node/_template.py` | 重写 — 保存使用 Packager，注册两个 Action | 03_预设库 |
| `ui/core/actions/node/__init__.py` | 注册 `_template` 模块 | 03_预设库 |
| `ui/canvas/mixins/canvas_menus.py` | 右键菜单添加"保存为预设" | 03_预设库 |
| `ui/main_window/panel.py` | 更新导入为 `PresetLibraryDialog` | 03_预设库 |
| `ui/core/application_context.py` | 移除模板管理器引用 | 03_预设库 |
| `ui/core/floating_panel.py` | 新增 `themed_input_dialog()` | 03_预设库 |
| `ui/core/import_export_manager.py` | 新增 `_repair_portable_venv()` | 03_预设库 |
| `ui/core/packager.py` | 新增 `compress_directory` / `extract_package` / `validate` | 03_预设库 |
| `ui/core/core_process.py` | 新增 `stop_all` / `detect_running` 命令分发 | 04_IPC |
| `ui/core/polling_manager.py` | 动态频率调整机制 | 05_轮询 |
| `ui/core/actions/builtin_view_actions.py` | i18n 键名更新 | 06_翻译 |
| `ui/core/strings_cn.json` | 新增 29 键、删除 17 键、修复错配 | 06_翻译 |
| `ui/core/strings_en.json` | 新增 29 键、删除 17 键、修复错配 | 06_翻译 |
