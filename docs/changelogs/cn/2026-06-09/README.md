# 2026-06-09 更新日志

## 📋 更新概述

本次更新主要修复了 CanvasHost 窗口中分割条位置的持久化问题，确保画布和终端之间的尺寸调整能够正确保存和恢复。

## ✨ 更新内容

### 1. 🔧 CanvasHost 分割条位置持久化

**功能描述**：
- CanvasHost 窗口的分割条位置自动保存到 `app_config.json`
- 项目打开后自动恢复上次的分割条位置
- 支持自动打开项目和手动打开项目两种场景
- 使用双重保存机制（Qt 原生状态 + 显式尺寸）确保正确性

**修改文件**：
- `ui/core/window_state_manager.py`
- `ui/main_window.py`
- `ui/core/project_manager.py`

**详细文档**：[CanvasHost 分割条位置持久化](./01_CanvasHost 分割条位置持久化.md)

---

## 🎯 总览

| 功能 | 状态 |
|------|------|
| CanvasHost 分割条位置持久化 | ✅ 完成 |

---

**更新日期**：2026-06-09
