# BNOS 文档中心

欢迎来到 BNOS 项目的文档中心。本目录按职能组织各类技术文档，方便快速定位和回溯。

## 目录结构

```
docs/
├── changelogs/          # 更新日志（中英文）
├── guides/              # 开发规范与指南
├── design/              # 设计方案与架构文档
├── reference/           # 技术参考文档与结构图
├── archive/             # 归档文档（已过期的分析报告、旧版更新日志等）
└── README.md            # 本导航索引
```

## 文档分类说明

### 📝 changelogs/
- **用途**：项目更新日志，按日期组织的详细变更记录
- **内容**：每日更新明细、功能新增、Bug修复、架构变更
- **子目录**：`cn/`（中文）、`en/`（英文）
- **入口**：[中文总索引](changelogs/cn/README.md) | [English Index](changelogs/en/README.md)

### 📋 guides/
- **用途**：开发规范、编码指南、最佳实践
- **文件**：
  - [config_json_开发规范.md](guides/config_json_开发规范.md) - node_config.json 配置文件开发规范

### 🎨 design/
- **用途**：架构设计、重构计划、开发方案
- **文件**：
  - [BNOS_解耦开发方案.md](design/BNOS_解耦开发方案.md) - 项目解耦开发方案
  - [CANVAS_VIEW_REFACTOR_PLAN.md](design/CANVAS_VIEW_REFACTOR_PLAN.md) - 画布视图重构计划
  - [DRAWING_ANNOTATION_ITERATION_PLAN.md](design/DRAWING_ANNOTATION_ITERATION_PLAN.md) - 绘图标注迭代计划
  - [MIXIN_REFACTOR_PLAN.md](design/MIXIN_REFACTOR_PLAN.md) - Mixin 架构重构计划
  - [MULTI_ANCHOR_REFACTOR_PLAN.md](design/MULTI_ANCHOR_REFACTOR_PLAN.md) - 多锚点系统重构计划
  - [Phase12_自适应节点视图开发方案.md](design/Phase12_自适应节点视图开发方案.md) - 自适应节点视图开发方案
  - [单模式自适应节点渲染_开发方案.md](design/单模式自适应节点渲染_开发方案.md) - 单模式自适应节点渲染方案
  - [历史回滚功能设计方案.md](design/历史回滚功能设计方案.md) - 历史回滚功能设计
  - [日志系统分析与优化方案.md](design/日志系统分析与优化方案.md) - 日志系统分析
  - [日志系统去臃肿化优化方案.md](design/日志系统去臃肿化优化方案.md) - 日志系统优化
  - [线程泄漏防护三层架构设计方案.md](design/线程泄漏防护三层架构设计方案.md) - 线程泄漏防护架构
  - [终端Dock开发方案.md](design/终端Dock开发方案.md) - 终端 Dock 开发方案
  - [菜单功能统一化开发指南.md](design/菜单功能统一化开发指南.md) - 菜单功能开发指南
  - [菜单功能统一化开发方案.md](design/菜单功能统一化开发方案.md) - 菜单功能开发方案
  - [node_item_refactoring_analysis.md](design/node_item_refactoring_analysis.md) - NodeItem 重构分析
  - [node_startup_queue_design.md](design/node_startup_queue_design.md) - 节点启动队列设计
  - [面板加载顺序调整.md](design/面板加载顺序调整.md) - 面板加载顺序调整方案

### 📖 reference/
- **用途**：技术参考文档、架构图、模块说明
- **文件**：
  - [BNOS_架构图.md](reference/BNOS_架构图.md) - 系统架构图
  - [BNOS_文件结构图.md](reference/BNOS_文件结构图.md) - 文件结构说明
  - [DEVELOPMENT_GUIDELINES.md](reference/DEVELOPMENT_GUIDELINES.md) - 开发指南
  - [TECHNICAL_DOCUMENTATION.md](reference/TECHNICAL_DOCUMENTATION.md) - 技术文档（英文）
  - [TECHNICAL_DOCUMENTATION_CN.md](reference/TECHNICAL_DOCUMENTATION_CN.md) - 技术文档（中文）
  - [TOAST_MODULE_README.md](reference/TOAST_MODULE_README.md) - Toast 模块说明
  - [JSON区域布局结构说明.md](reference/JSON区域布局结构说明.md) - JSON 区域布局说明
  - [Thread_Leak_Prevention_Three_Layer_Architecture.md](reference/Thread_Leak_Prevention_Three_Layer_Architecture.md) - 线程泄漏防护（英文）

### 🗄️ archive/
- **用途**：已过期或已实施完毕的文档归档，保留历史记录供回溯
- **文件**：
  - [UPDATE_CN.md](archive/UPDATE_CN.md) - 旧版更新日志（中文）
  - [UPDATE_EN.md](archive/UPDATE_EN.md) - 旧版更新日志（英文）
  - [UPDATE_COLLAPSED_CN.md](archive/UPDATE_COLLAPSED_CN.md) - 旧版折叠更新日志（中文）
  - [UPDATE_COLLAPSED_EN.md](archive/UPDATE_COLLAPSED_EN.md) - 旧版折叠更新日志（英文）
  - [README_BAK.md](archive/README_BAK.md) - README 备份
  - [README_FIXED.md](archive/README_FIXED.md) - README 修正版
  - [BNOS_优化实施步骤.md](archive/BNOS_优化实施步骤.md) - 优化实施步骤
  - [BNOS_技术分析报告.md](archive/BNOS_技术分析报告.md) - 技术分析报告
  - [BNOS_项目优化分析报告.md](archive/BNOS_项目优化分析报告.md) - 项目优化分析报告
  - [BNOS_重复与矛盾逻辑分析报告.md](archive/BNOS_重复与矛盾逻辑分析报告.md) - 重复与矛盾逻辑分析
  - [CODE_ANALYSIS_REPORT.md](archive/CODE_ANALYSIS_REPORT.md) - 代码分析报告
  - [DOCK吸附堆叠方案实施总结.md](archive/DOCK吸附堆叠方案实施总结.md) - Dock 吸附堆叠总结
  - [Dock吸附堆叠尺寸持久化方案.md](archive/Dock吸附堆叠尺寸持久化方案.md) - Dock 尺寸持久化方案
  - [Dock尺寸持久化问题记录.md](archive/Dock尺寸持久化问题记录.md) - Dock 尺寸问题记录
  - [dock_window_solution.md](archive/dock_window_solution.md) - Dock 窗口解决方案
  - [下一步计划.md](archive/下一步计划.md) - 旧版下一步计划
  - [主线程阻塞与假异步分析报告.md](archive/主线程阻塞与假异步分析报告.md) - 主线程阻塞分析
  - [进程隔离功能问题分析报告.md](archive/进程隔离功能问题分析报告.md) - 进程隔离问题分析
  - [节点进程僵尸与内存泄漏修复方案.md](archive/节点进程僵尸与内存泄漏修复方案.md) - 僵尸进程修复方案
  - [TRAE_COMMUNITY_POST.md](archive/TRAE_COMMUNITY_POST.md) - 社区帖子
  - [卡顿问题迭代优化方案.md](archive/卡顿问题迭代优化方案.md) - 卡顿优化方案

## 文档维护规范

1. **新增文档**：根据内容类型放入对应子目录
2. **归档规则**：已实施完毕的开发方案、不再维护的分析报告，移入 `archive/`
3. **版本更新**：更新日志统一放入 `changelogs/` 对应日期目录
4. **中英文**：技术文档尽量提供中英文版本，中文放文件名后加 `_CN`，英文不加后缀

## 快速导航

| 分类 | 入口 |
|------|------|
| 更新日志 | [中文](changelogs/cn/README.md) |
| 更新日志 | [English](changelogs/en/README.md) |
| 架构设计 | [设计方案汇总](design/) |
| 技术参考 | [参考文档汇总](reference/) |
| 开发规范 | [规范指南](guides/) |
| 历史归档 | [归档文档](archive/) |
