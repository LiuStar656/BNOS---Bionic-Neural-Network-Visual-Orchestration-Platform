# README 重写与归档

## 背景

旧版 README（v1）存在以下问题：
- **篇幅过长**：~1100 行，大量内容重复、冗余
- **架构描述不清晰**：模块列表堆砌，缺少高层次抽象和层级关系图
- **复合节点系统缺失**：作为项目最核心、最复杂的功能（`composite_node.py` 近 2800 行），README 中几乎未提及
- **过时引用**：多处引用不存在的文件（`bnos_gui.py`、`requirements_gui.txt`、`start_bnos_gui.bat`）
- **核心设计理念散落**：代码优先、进程隔离、文件通信等理念分散在各功能描述中

## 改动内容

### README 重写（中英文双语）

将 `README.md` 和 `README_CN.md` 从 ~1100 行压缩至 ~220 行，重新组织为 9 个章节：

| 章节 | 内容 |
|------|------|
| 1. 项目简介 | 一句话定义 + 定位说明 |
| 2. 核心设计 | 四核心理念：(1) 代码优先+可视化编排 (2) 每节点独立进程+独立venv (3) 文件级JSON通信+注意力过滤 (4) **复合节点DAG压缩** |
| 3. 架构概览 | 层级关系图：Launcher → BNOS Console → ApplicationContext → {EventBus, DI, Polling} → {Canvas, Panels, NodeSystem} → {Nodes(venv), Composite(orchestrator)} |
| 4. 快速开始 | 正确的启动命令（`python launcher.py` 或 `python bnos_console.py`） |
| 5. 核心功能 | 精简至6项：可视化画布、复合节点系统、多语言节点、进程健康检测、节点注册表、启动队列+历史回滚+Toast |
| 6. 项目结构 | 精简目录树 |
| 7. 扩展开发 | 新增语言/节点样式/参数控件 |
| 8. 已知限制 | 4 项核心限制 |
| 9. 许可+贡献 | 保持不变 |

### 关键改动

- **新增「复合节点」专题**：核心功能独立一节，说明压缩/展开/编排器/DAG执行/端口路由/双模式运行时
- **修正过时引用**：`bnos_gui.py` → `launcher.py` / `bnos_console.py`
- **架构图重绘**：体现双层启动 → ApplicationContext → 核心服务 → 节点系统的层级关系
- **大幅精简**：用户操作指南（创建节点、画布操作等）从 README 移除，保留 5 步快速上手
- **删除「BNOS vs Low-Code」长表**：浓缩为一句话核心定位
- **归档链接**：新旧 README 均包含指向归档版本的链接

### 旧版归档

旧版 README 归档至 `docs/archived/`，顶部添加归档标记：

| 文件 | 归档位置 |
|------|---------|
| `README.md` (v1) | `docs/archived/README_v1_archived.md` |
| `README_CN.md` (v1) | `docs/archived/README_CN_v1_archived.md` |

## 对比

| 方面 | 旧版 (v1) | 新版 (v2) |
|------|-----------|-----------|
| 篇幅 | ~1100 行 | ~220 行 |
| 复合节点 | 未提及 | 旗舰功能独立章节 |
| 架构描述 | 模块列表堆砌 | 高层级关系图 |
| 启动命令 | `bnos_gui.py`（不存在） | `launcher.py` / `bnos_console.py` |
| BNOS vs Low-Code | 冗长对比表 | 一句话定位 |
| 用户操作指南 | 大量详细步骤 | 5 步快速上手 |
| 归档链接 | 无 | 新 README 底部链接 + 归档标记 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `README.md` | 重写：~1100 行 → ~220 行，9 章节结构 |
| `README_CN.md` | 重写：~1100 行 → ~220 行，9 章节结构 |
| `docs/archived/README_v1_archived.md` | 新增：旧版英文 README 归档（含归档标记） |
| `docs/archived/README_CN_v1_archived.md` | 新增：旧版中文 README 归档（含归档标记） |
| `docs/changelogs/cn/2026-07-13/14_README重写与归档.md` | 新增：本 changelog |
| `docs/changelogs/en/2026-07-13/14_README_Rewrite_and_Archive.md` | 新增：英文 changelog |
| `docs/changelogs/cn/2026-07-13/README.md` | 更新：日期索引新增条目 14 |
| `docs/changelogs/en/2026-07-13/README.md` | 更新：日期索引新增条目 14 |
| `docs/changelogs/cn/README.md` | 更新：总索引 details 折叠新增条目 |
| `docs/changelogs/en/README.md` | 更新：总索引 details 折叠新增条目 |
| `docs/changelogs/cn/INDEX.md` | 更新：日期索引新增条目 |
| `docs/changelogs/en/INDEX.md` | 更新：日期索引新增条目 |
