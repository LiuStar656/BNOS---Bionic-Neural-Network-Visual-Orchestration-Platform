
# BNOS 更新日志（可折叠展开）

&gt; 📖 英文版：[UPDATE_COLLAPSED_EN.md](UPDATE_COLLAPSED_EN.md)

---

## 快速导航

- 📂 [按日期分类的完整更新日志](./changelogs/)
- 🇨🇳 [中文更新日志索引](./changelogs/cn/INDEX.md)

---

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-06-07&lt;/h2&gt;&lt;/summary&gt;

### 🔄 节点状态同步与项目持久化完善

#### 已修复的问题

**1. 节点状态信息未正常更新**
- **问题**：画布节点的CPU、内存信息未正常更新，与资源监测面板显示不一致
- **原因**：节点状态获取方式存在冲突，node_monitor 模块与资源监测面板数据来源不同
- **修复**：
  - 废弃 ui/core/node_monitor.py 模块
  - 资源监测面板新增 node_state_updated 信号，转发节点CPU、内存数据
  - 画布节点通过信号接收资源监测面板的数据，确保数据源一致
- **修改文件**：
  - ui/panels/resource_monitor.py
  - ui/panels/resource_monitor_dock.py
  - ui/canvas/items/node_item.py

**2. 异步调用导致数据加载不及时**
- **问题**：节点创建后无法接收资源监测面板的数据信号
- **原因**：信号连接时序问题，资源监测面板创建晚于节点
- **修复**：主窗口新增 _connect_existing_nodes_to_resource_monitor() 方法
- **修改文件**：ui/main_window.py

**3. 项目持久化功能完善**
- **问题**：重启GUI后需要手动打开项目
- **修复**：
  - 打开项目时记录到 app_config.json
  - 下次打开GUI时自动加载上次打开的项目
- **修改文件**：
  - ui/main_window.py
  - ui/core/project_manager.py

---

[查看完整更新](./changelogs/cn/2026-06-07/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-06-06&lt;/h2&gt;&lt;/summary&gt;

### 🎨 Toast 通知视觉效果全面修复

#### 问题描述

**Toast 通知存在严重视觉缺陷**
- **问题 1：黑色底框闪烁** — 显示通知时先弹出黑色底框，随后才显示正确样式
- **问题 2：消失动画突兀** — 通知消失时瞬间消失，而非平滑渐隐

#### 修复方案

**采用"外层透明窗口 + 内层承载样式"的双层架构**
1. 继承类调整：`QLabel` → `QWidget`
2. 窗口属性精简：仅设置 `WA_TranslucentBackground`
3. 样式承载：在内层 `QLabel` 上设置 `rgba` 背景色
4. 动画重构：用 `QTimer` 驱动 `setWindowOpacity()`

### 🔧 代码健壮性修复

- 修复多处潜在的空指针异常
- 优化异常处理逻辑
- 增强代码的鲁棒性

---

[查看完整更新](./changelogs/cn/2026-06-06/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-06-05&lt;/h2&gt;&lt;/summary&gt;

### 🔄 强制删除节点文件夹
- 即使文件被占用也能强制删除
- 支持删除被锁定的节点文件夹

### ⚡ 异步操作优化
- **异步删除节点** - 不阻塞GUI
- **异步启动/停止节点** - 不阻塞GUI
- **异步挂载/卸载/刷新节点** - 不阻塞GUI

### 🖥️ 绘图工具栏按需显示
- 工具栏仅在需要时显示
- 优化界面布局

### 🌳 进程树终止机制
- 完整终止节点进程树
- 防止僵尸进程残留

### 🐍 JSON 启动虚拟环境支持
- 支持通过 JSON 配置启动虚拟环境
- 更灵活的节点启动方式

---

[查看完整更新](./changelogs/cn/2026-06-05/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-23&lt;/h2&gt;&lt;/summary&gt;

### 🎬 启动动画、品牌重命名、BnosConsole、README 重构
- 新增启动动画
- 品牌重命名为 BnosConsole
- 重构项目 README

### 🚀 独立启动器、三态状态灯、Ctrl+D 删除、颜色设置修复
- 独立启动器
- 三态状态灯
- Ctrl+D 快捷键删除
- 颜色设置修复

### 🔄 统一轮询管理器、全局状态监测重构
- 统一轮询管理器
- 全局状态监测重构

### 🎨 VS Code Codicon 图标系统集成
- 集成 VS Code Codicon 图标系统
- 更美观的图标展示

---

[查看完整更新](./changelogs/cn/2026-05-23/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-22&lt;/h2&gt;&lt;/summary&gt;

### 🔗 ComfyUI 风格连线重构、人工折叠交互
- ComfyUI 风格连线重构
- 人工折叠交互

### 📋 节点注册表、挂载外部节点
- 节点注册表
- 挂载外部节点功能

---

[查看完整更新](./changelogs/cn/2026-05-22/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-21&lt;/h2&gt;&lt;/summary&gt;

### 🏗️ 重大架构重构、UI 组件模块化与菜单栏整合
- 重大架构重构
- UI 组件模块化
- 菜单栏整合

### 🎨 UI 精简与优化
- UI 精简与优化

### 📋 四项重大计划实施
- 四项重大计划实施

### 🖥️ VSCode 风格深色无边框窗口
- VSCode 风格深色无边框窗口

### 🎨 画布可视区域渲染优化
- 画布可视区域渲染优化

### 🎨 节点样式系统
- 节点样式系统

### 🏗️ GUI 架构重构与功能增强
- GUI 架构重构与功能增强

### 🔗 连线反推校验、连线交互修复
- 连线反推校验
- 连线交互修复

---

[查看完整更新](./changelogs/cn/2026-05-21/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-20&lt;/h2&gt;&lt;/summary&gt;

查看 [2026-05-20 更新](./changelogs/cn/2026-05-20/) 获取完整内容。

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-19&lt;/h2&gt;&lt;/summary&gt;

### 🔧 关键问题修复与增强

#### 1. **Rust 节点语言检测修复** 🦀
- **问题**：画布上的 Rust 节点显示为 "Unknown" 而非 "Rust"
- **解决方案**：增强语言检测逻辑，同时检查 `src/main.rs` 和 `Cargo.toml` 文件

#### 2. **节点文件夹路径解析修复** 📁
- **问题**：点击"打开节点文件夹"时打开了错误的目录
- **解决方案**：实现三层路径验证和规范化机制
- 第一层：节点加载时的路径规范化
- 第二层：配置对话框中的路径验证
- 第三层：节点列表中的路径验证

[查看完整更新](./changelogs/cn/2026-05-19/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-18&lt;/h2&gt;&lt;/summary&gt;

### ✨ 新增功能与优化

#### 1. **画布节点右键菜单增强 - 启动/停止节点** ⚡
- 画布右键点击节点，动态显示启动/停止选项

#### 2. **节点配置对话框全新布局设计** 🎨
- 横向矩形窗口布局，JSON 直接编辑

#### 3. **节点列表拖拽移动与智能分组** 🎯
- 拖拽节点到不同组，重叠自动创建组

#### 4. **节点列表多选右键菜单优化** 📋
- 多选时显示批量操作菜单

#### 5. **画布框选功能优化** 📦
- 仅在空白区域触发框选

#### 6. **画布节点双击打开配置** ⚙️
- 双击节点直接打开配置对话框

#### 7. **节点列表多选批量删除** 🗑️
- Shift/Ctrl 多选后批量删除

#### 8. **窗口关闭进程检测与管理** 🛑
- 关闭时检测运行中的节点并确认

[查看完整更新](./changelogs/cn/2026-05-18/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-17&lt;/h2&gt;&lt;/summary&gt;

### ✨ 新增功能与优化

#### 1. **增强型 Rust 节点生成器** 🔧
- 完全重写的 Rust 节点生成系统，具备自愈能力
- 自动环境检测和自我修复机制
- 比 Python 等效代码快 10-100x

[查看完整更新](./changelogs/cn/2026-05-17/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-08&lt;/h2&gt;&lt;/summary&gt;

### ✨ 新增功能与优化

#### 1. **VSCode 工作区集成** 🔧
- 节点配置对话框中新增"打开为 VSCode 工作区"按钮
- 自动生成 .code-workspace 配置文件

#### 2. **VSCode 工作区功能优化** ⚡
- 智能检测 VSCode 是否已安装
- 友好的用户交互

[查看完整更新](./changelogs/cn/2026-05-08/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-07&lt;/h2&gt;&lt;/summary&gt;

### ✨ 新增功能与优化

#### 1. **连线锚点位置修复** 🔧
- 使用 `sceneBoundingRect().center()` 确保连线正确

#### 2. **窗口置顶行为优化** 🪟
- 移除不必要的 `WindowStaysOnTopHint` 标志

#### 3. **最佳实践记录** 📚
- 创建记忆知识库

[查看完整更新](./changelogs/cn/2026-05-07/)

&lt;/details&gt;

---

[查看完整索引](./changelogs/cn/INDEX.md)

---

## 使用说明

- 点击日期标题即可展开/折叠该日期的更新内容
- 每个日期下包含该日期的主要更新摘要
- 点击"查看完整更新"可查看该日期的详细更新记录

---

*最后更新：2026-06-07*

