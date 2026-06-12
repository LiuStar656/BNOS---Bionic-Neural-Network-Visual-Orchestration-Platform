# BNOS 更新日志总索引

> 点击左侧三角展开对应版本完整日志
> 📖 英文版本：[English Version](../en/README.md)

---

<details open>
<summary><strong>【2026-06-12】V2.0.12 - 主窗口解耦与代码质量全面提升</strong></summary>

[查看完整更新](./2026-06-12/README.md)

**主要更新：**
- ApplicationContext 单例类聚合 11 个全局服务，统一生命周期管理
- 主窗口从 1500 行精简到 **499行**，拆分为 7 个 Mixin 模块（状态、生命周期、业务、面板、IPC、节点控制、交互）
- 代码质量改进：类型注解、代码去重、增强错误处理
- 跨平台支持：Windows/macOS/Linux
- 修复 Unicode 编码、权限检查、路径验证等问题

</details>

<details>
<summary><strong>【2026-06-11】V2.0.11 - 连线端口锚点绑定保护与 canvas_layout 防改写</strong></summary>

[查看完整更新](./2026-06-11/README.md)

**主要更新：**
- EdgeItem 新增期望端口名字段（_desired_target_port_name），锚点重建后能重新找到正确锚点
- 指定端口但找不到锚点时跳过连线（不 fallback 到 default），canvas_layout.json 不再被错误改写
- _validate_edge_anchor_binding 优先使用期望端口名查找，而非当前已错绑的锚点名
- 手动连线时也传递端口名参数，确保全链路一致性

</details>

<details>
<summary><strong>【2026-06-10】V2.0.10 - IDE 自动扫描 & 自适应节点视图 & 多锚点系统完善</strong></summary>

[查看完整更新](./2026-06-10/README.md)

**主要更新：**
- IDEScanner 自动扫描器，跨平台检测 VSCode / Trae IDE
- 第三种节点样式「面板模式」（ComfyUI 风格），11 种参数控件
- 多输入端口支持（prompt / context 等），均匀分布在节点左侧
- 端口映射修正（default → listen_upper_file），连线持久化不再丢失

</details>

<details>
<summary><strong>【2026-06-09】V2.0.9 - CanvasHost 分割条位置持久化 & 架构解耦与功能统一化</strong></summary>

[查看完整更新](./2026-06-09/README.md)

**主要更新：**
- CanvasHost 窗口分割条位置持久化
- 引入 EventBus、DI 容器、ShutdownOrchestrator 等 8 个基础设施模块
- Action 系统扩展至 50 个 Action，画布+节点菜单统一
- 消除两大面板间 ~800 行重复代码

</details>

<details>
<summary><strong>【2026-06-08】V2.0.8 - 绘图工具显示状态持久化</strong></summary>

[查看完整更新](./2026-06-08/README.md)

**主要更新：**
- 绘图工具栏显示状态持久化
- 修复需要连续两次操作的问题
- 配置文件集成

</details>

<details>
<summary><strong>【2026-06-07】V2.0.7 - 节点状态同步与项目持久化完善</strong></summary>

[查看完整更新](./2026-06-07/README.md)

**主要更新：**
- 节点状态信息正常更新修复
- 异步调用导致数据加载不及时修复
- 项目持久化功能完善

</details>

<details>
<summary><strong>【2026-06-06】V2.0.6 - Toast 通知视觉效果全面修复</strong></summary>

[查看完整更新](./2026-06-06/README.md)

**主要更新：**
- Toast 通知视觉缺陷修复
- 代码健壮性修复

</details>

<details>
<summary><strong>【2026-06-05】V2.0.5 - 多项异步优化与功能增强</strong></summary>

[查看完整更新](./2026-06-05/README.md)

**主要更新：**
- 强制删除节点文件夹
- 多项异步操作优化
- 绘图工具栏按需显示
- 进程树终止机制
- JSON 启动虚拟环境支持

</details>

<details>
<summary><strong>【2026-05-23】V2.0.4 - 多项架构与 UI 改进</strong></summary>

[查看完整更新](./2026-05-23/README.md)

**主要更新：**
- 启动动画、品牌重命名
- 独立启动器、三态状态灯
- 统一轮询管理器
- VS Code Codicon 图标系统集成

</details>

<details>
<summary><strong>【2026-05-22】V2.0.3 - 连线与节点管理改进</strong></summary>

[查看完整更新](./2026-05-22/README.md)

**主要更新：**
- ComfyUI 风格连线重构
- 人工折叠交互
- 节点注册表、挂载外部节点

</details>

<details>
<summary><strong>【2026-05-21】V2.0.2 - 重大架构重构</strong></summary>

[查看完整更新](./2026-05-21/README.md)

**主要更新：**
- 重大架构重构、UI 组件模块化
- 菜单栏整合
- VSCode 风格深色无边框窗口
- 节点样式系统
- 画布可视区域渲染优化

</details>

<details>
<summary><strong>【2026-05-20】V2.0.1 - 画布组件模块化拆分</strong></summary>

[查看完整更新](./2026-05-20/README.md)

**主要更新：**
- Canvas Widget 模块化拆分

</details>

<details>
<summary><strong>【2026-05-19】V2.0.0 - Rust 节点与路径解析修复</strong></summary>

[查看完整更新](./2026-05-19/README.md)

**主要更新：**
- Rust 节点语言检测修复
- 节点文件夹路径解析修复

</details>

<details>
<summary><strong>【2026-05-18】V1.9.0 - 节点管理与配置改进</strong></summary>

[查看完整更新](./2026-05-18/README.md)

**主要更新：**
- 画布节点右键菜单增强
- 节点配置对话框全新布局
- 节点列表拖拽移动与智能分组
- 多项批量操作功能

</details>

<details>
<summary><strong>【2026-05-17】V1.8.0 - Rust 节点生成器</strong></summary>

[查看完整更新](./2026-05-17/README.md)

**主要更新：**
- 增强型 Rust 节点生成器
- 自愈能力、性能优化

</details>

<details>
<summary><strong>【2026-05-08】V1.7.0 - VSCode 工作区集成</strong></summary>

[查看完整更新](./2026-05-08/README.md)

**主要更新：**
- VSCode 工作区集成
- VSCode 工作区功能优化

</details>

<details>
<summary><strong>【2026-05-07】V1.6.0 - 连线与窗口行为修复</strong></summary>

[查看完整更新](./2026-05-07/README.md)

**主要更新：**
- 连线锚点位置修复
- 窗口置顶行为优化
- 最佳实践记录

</details>

---

## 快速导航

- [按日期浏览](INDEX.md)
- [回到项目根目录](../../README_CN.md)

---

### 架构说明

本更新日志采用**「单一索引页 + 分版本独立 MD 子文件」**架构：
- **总索引页**：本文件，负责导航、折叠、引入
- **每日期独立文件夹**：所有详细内容按日期组织
- **完全解耦**：新增版本只需在对应日期文件夹添加文件，无需修改旧代码

### 使用说明

1. 点击日期左侧的三角展开/收起该版本摘要
2. 点击「查看完整更新」链接进入该日期的详细更新页面
3. 每个日期文件夹包含该日期的所有更新条目，支持单独浏览和归档
