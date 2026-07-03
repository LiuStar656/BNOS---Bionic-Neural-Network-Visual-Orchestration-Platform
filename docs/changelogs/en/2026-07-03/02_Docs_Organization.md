# Docs Organization

## Problem

Approximately 46 document files were scattered in the docs directory, most of which were outdated or already implemented, lacking a clear organizational structure.

## Solution

Organized documents into 4 subdirectories by function:

### Directory Structure

```
docs/
├── changelogs/          # Changelogs (CN/EN, unchanged)
├── guides/              # Development guidelines (existing)
├── design/              # New: Architecture design, refactoring plans, development proposals
├── reference/           # New: Technical reference docs, diagrams
├── archive/             # New: Archived outdated/implemented documents
└── README.md            # New: Navigation index
```

### File Categories

| Directory | Count | Content Type |
|-----------|-------|--------------|
| `design/` | 17 | Decoupling proposals, Canvas refactor plans, Mixin refactor plans, multi-anchor refactor, history rollback design, thread leak prevention architecture |
| `reference/` | 8 | Architecture diagrams, file structure diagrams, technical docs (CN/EN), Toast module README, JSON layout description |
| `archive/` | 21 | Old changelogs, completed analysis reports, project optimization reports, Dock solutions, lag optimization proposals |

## Modified Files

### New Directories
- `docs/archive/`
- `docs/design/`
- `docs/reference/`

### New Files
- `docs/README.md` — Navigation index with directory descriptions, file listings, and maintenance guidelines

### Path Reference Updates
| File | Update |
|------|--------|
| `README.md` | TECHNICAL_DOCUMENTATION.md → reference/TECHNICAL_DOCUMENTATION.md |
| `README_CN.md` | TECHNICAL_DOCUMENTATION_CN.md → reference/TECHNICAL_DOCUMENTATION_CN.md |
| `ui/canvas/README.md` | MULTI_ANCHOR_REFACTOR_PLAN.md → design/MULTI_ANCHOR_REFACTOR_PLAN.md |
| `ui/core/README.md` | TOAST_MODULE_README.md → reference/TOAST_MODULE_README.md; MULTI_ANCHOR → design/ |
| `docs/reference/BNOS_文件结构图.md` | Internal references updated |
| `docs/design/BNOS_解耦开发方案.md` | Internal references updated |

### Moved Files (46 total)

**design/ (17)**:
- BNOS_解耦开发方案.md, CANVAS_VIEW_REFACTOR_PLAN.md, DRAWING_ANNOTATION_ITERATION_PLAN.md
- MIXIN_REFACTOR_PLAN.md, MULTI_ANCHOR_REFACTOR_PLAN.md, Phase12_自适应节点视图开发方案.md
- 单模式自适应节点渲染_开发方案.md, 历史回滚功能设计方案.md, 日志系统分析与优化方案.md
- 日志系统去臃肿化优化方案.md, 线程泄漏防护三层架构设计方案.md, 终端Dock开发方案.md
- 菜单功能统一化开发指南.md, 菜单功能统一化开发方案.md, node_item_refactoring_analysis.md
- node_startup_queue_design.md, 面板加载顺序调整.md

**reference/ (8)**:
- BNOS_架构图.md, BNOS_文件结构图.md, DEVELOPMENT_GUIDELINES.md
- TECHNICAL_DOCUMENTATION.md, TECHNICAL_DOCUMENTATION_CN.md, TOAST_MODULE_README.md
- JSON区域布局结构说明.md, Thread_Leak_Prevention_Three_Layer_Architecture.md

**archive/ (21)**:
- UPDATE_CN.md, UPDATE_EN.md, UPDATE_COLLAPSED_CN.md, UPDATE_COLLAPSED_EN.md
- README_BAK.md, README_FIXED.md, BNOS_优化实施步骤.md, BNOS_技术分析报告.md
- BNOS_项目优化分析报告.md, BNOS_重复与矛盾逻辑分析报告.md, CODE_ANALYSIS_REPORT.md
- DOCK吸附堆叠方案实施总结.md, Dock吸附堆叠尺寸持久化方案.md, Dock尺寸持久化问题记录.md
- dock_window_solution.md, 下一步计划.md, 主线程阻塞与假异步分析报告.md
- 进程隔离功能问题分析报告.md, 节点进程僵尸与内存泄漏修复方案.md, TRAE_COMMUNITY_POST.md
- 卡顿问题迭代优化方案.md
