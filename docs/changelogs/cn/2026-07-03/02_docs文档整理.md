# docs 文档整理

## 问题描述

docs 目录下散落了约 46 个文档文件，大部分已过期或已实施完毕，缺乏清晰的组织结构。

## 解决方案

按职能将文档分为 4 个子目录：

### 目录结构

```
docs/
├── changelogs/          # 更新日志（中英文，保持不变）
├── guides/              # 开发规范与指南（已有）
├── design/              # 新建：架构设计、重构计划、开发方案
├── reference/           # 新建：技术参考文档、结构图
├── archive/             # 新建：已过期/已实施完毕的文档归档
└── README.md            # 新建：导航索引
```

### 文件分类

| 目录 | 文件数 | 内容类型 |
|------|--------|----------|
| `design/` | 17 | 解耦开发方案、Canvas重构计划、Mixin重构计划、多锚点重构、历史回滚设计、线程泄漏防护架构等 |
| `reference/` | 8 | 架构图、文件结构图、技术文档（中英文）、Toast模块说明、JSON布局说明 |
| `archive/` | 21 | 旧版更新日志、已实施完毕的分析报告、项目优化报告、Dock解决方案、卡顿优化方案等 |

## 修改文件

### 新增目录
- `docs/archive/`
- `docs/design/`
- `docs/reference/`

### 新增文件
- `docs/README.md` — 导航索引，含目录说明、文件清单、维护规范

### 路径引用更新
| 文件 | 更新内容 |
|------|----------|
| `README.md` | TECHNICAL_DOCUMENTATION.md → reference/TECHNICAL_DOCUMENTATION.md |
| `README_CN.md` | TECHNICAL_DOCUMENTATION_CN.md → reference/TECHNICAL_DOCUMENTATION_CN.md |
| `ui/canvas/README.md` | MULTI_ANCHOR_REFACTOR_PLAN.md → design/MULTI_ANCHOR_REFACTOR_PLAN.md |
| `ui/core/README.md` | TOAST_MODULE_README.md → reference/TOAST_MODULE_README.md；MULTI_ANCHOR → design/ |
| `docs/reference/BNOS_文件结构图.md` | 内部引用更新 |
| `docs/design/BNOS_解耦开发方案.md` | 内部引用更新 |

### 移动的文件（共 46 个）

**design/（17个）**：
- BNOS_解耦开发方案.md、CANVAS_VIEW_REFACTOR_PLAN.md、DRAWING_ANNOTATION_ITERATION_PLAN.md
- MIXIN_REFACTOR_PLAN.md、MULTI_ANCHOR_REFACTOR_PLAN.md、Phase12_自适应节点视图开发方案.md
- 单模式自适应节点渲染_开发方案.md、历史回滚功能设计方案.md、日志系统分析与优化方案.md
- 日志系统去臃肿化优化方案.md、线程泄漏防护三层架构设计方案.md、终端Dock开发方案.md
- 菜单功能统一化开发指南.md、菜单功能统一化开发方案.md、node_item_refactoring_analysis.md
- node_startup_queue_design.md、面板加载顺序调整.md

**reference/（8个）**：
- BNOS_架构图.md、BNOS_文件结构图.md、DEVELOPMENT_GUIDELINES.md
- TECHNICAL_DOCUMENTATION.md、TECHNICAL_DOCUMENTATION_CN.md、TOAST_MODULE_README.md
- JSON区域布局结构说明.md、Thread_Leak_Prevention_Three_Layer_Architecture.md

**archive/（21个）**：
- UPDATE_CN.md、UPDATE_EN.md、UPDATE_COLLAPSED_CN.md、UPDATE_COLLAPSED_EN.md
- README_BAK.md、README_FIXED.md、BNOS_优化实施步骤.md、BNOS_技术分析报告.md
- BNOS_项目优化分析报告.md、BNOS_重复与矛盾逻辑分析报告.md、CODE_ANALYSIS_REPORT.md
- DOCK吸附堆叠方案实施总结.md、Dock吸附堆叠尺寸持久化方案.md、Dock尺寸持久化问题记录.md
- dock_window_solution.md、下一步计划.md、主线程阻塞与假异步分析报告.md
- 进程隔离功能问题分析报告.md、节点进程僵尸与内存泄漏修复方案.md、TRAE_COMMUNITY_POST.md
- 卡顿问题迭代优化方案.md
