# 2026-06-09 更新日志

## 📋 更新概述

本次更新包含两项重大改进：
1. CanvasHost 窗口分割条位置持久化修复
2. 系统性架构解耦与功能统一化

---

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

**详细文档**：[CanvasHost 分割条位置持久化](./01_CanvasHost%20分割条位置持久化.md)

---

### 2. 🏗️ 架构解耦与功能统一化

**功能描述**：
- 引入 EventBus、DI 容器、ShutdownOrchestrator 等基础设施模块
- 消除两大面板间 ~800 行重复代码（NodeListOperationsMixin）
- Action 系统扩展至 50 个 Action，画布菜单、节点菜单、菜单栏共用
- Canvas 控制器组合（委托模式）、PanelManager 面板管理器

**修改文件**（17 个文件）：
- 新增 8 个基础设施文件
- 重构 3 个菜单/面板文件
- 修改 6 个框架文件

**详细文档**：[架构解耦与功能统一化](./02_架构解耦与功能统一化.md)

---

## 🎯 总览

| 功能 | 状态 |
|------|------|
| CanvasHost 分割条位置持久化 | ✅ 完成 |
| 架构解耦（EventBus + DI + 关闭编排） | ✅ 完成 |
| NodeListOperationsMixin 重复代码消除 | ✅ 完成 |
| Action 系统扩展（13 → 50 个） | ✅ 完成 |
| 画布 + 节点右键菜单统一 | ✅ 完成 |

---

**更新日期**：2026-06-09
