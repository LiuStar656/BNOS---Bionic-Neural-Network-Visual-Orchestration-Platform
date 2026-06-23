# BNOS 更新日志总索引

> 点击左侧三角展开对应版本完整日志
> 📖 英文版本：[English Version](../en/README.md)

---
<details open>
<summary><strong>【2026-06-24】V2.0.20 - 调试面板移除、性能异步化与生命周期防护</strong></summary>

[查看完整更新](./2026-06-24/README.md) | [01_调试面板精简与性能优化](./2026-06-24/01_调试面板精简与性能优化.md)

**主要更新：**
- 调试面板移除：删除 debug_panel.py 和 node_debugger.py，清理全部 7 个文件引用，移除 34 个 i18n 键
- 性能分析面板异步化：psutil.process_iter() 从主线程移入后台线程，消除打开面板时的 UI 冻结
- 面板生命周期防悬空指针：_is_panel_alive() 使用 shiboken6.isValid() 检测 C++ 对象存活，修复 Internal C++ object already deleted 崩溃
- 菜单打钩标记修复：6 个 Dock 面板 is_checked_fn 统一使用 config fallback
- Dock 标签栏从底部移到顶部

</details>

<details>
<summary><strong>【2026-06-22】V2.0.19 - 连线渲染矢量轮廓填充、高 DPI 支持与画布分辨率自定义</strong></summary>

[查看完整更新](./2026-06-22/README.md) | [01_连线渲染](./2026-06-22/01_连线渲染矢量轮廓填充.md) | [02_高DPI](./2026-06-22/02_高DPI屏幕适配.md) | [03_分辨率](./2026-06-22/03_画布分辨率自定义.md)

**主要更新：**
- 01 连线渲染：QPainterPathStroker 将线条转为闭合轮廓路径，使用 QBrush 填充（与箭头多边形填充一致），彻底解决放大锯齿问题
- 02 高 DPI 适配：主进程与画布子进程均启用 AA_EnableHighDpiScaling / AA_UseHighDpiPixmaps，确保 4K/Retina 屏幕效果
- 03 画布分辨率：设置对话框新增「渲染」标签页，5 个预设（1000-10000）+ 自定义宽高 + 抗锯齿开关，配置持久化至 app_config.json

</details>

<details>
<summary><strong>【2026-06-20】V2.0.18 - 浮动面板系统完善、预设节点库重构、翻译与 UI 统一化</strong></summary>

[查看完整更新](./2026-06-20/README.md) | [01_性能](./2026-06-20/01_性能分析面板修复.md) | [02_调试](./2026-06-20/02_调试面板翻译补全.md) | [03_预设库](./2026-06-20/03_预设节点库重构.md) | [04_IPC](./2026-06-20/04_IPC核心进程命令扩展.md) | [05_轮询](./2026-06-20/05_轮询管理器动态调频.md) | [06_翻译](./2026-06-20/06_翻译键值全面修订.md)

**主要更新：**
- 01 性能分析面板：ChartCanvas 自定义绘制，QPainter/QPainterPath 导入修复，拖动暂停刷新
- 02 调试面板：17 个中英文翻译键补全（端口、模式、操作、断点等）
- 03 预设节点库：废弃空壳模板系统，复用 `.bnos` 打包完整节点，新增 PresetLibraryDialog
- 04 IPC 核心进程：新增 node.stop_all（批量停止）和 node.detect_running 命令分发
- 05 轮询管理器：CPU 负载自适应动态调频（1s/2s/4s）
- 06 翻译全面修订：3 处错配修复，29 个新增键，17 个废弃键清理

</details>

<details>
<summary><strong>【2026-06-18】V2.0.17 - NodeItem 拆分重构与 Mixin 架构组合化</strong></summary>

[查看完整更新](./2026-06-18/README.md)

**主要更新：**
- NodeItem 单体类拆分：`node_item.py` 从 846 行精简为 227 行，拆分为 9 个子组件（渲染、几何、交互、状态、配置、样式、参数面板等），对外 API 完全兼容
- Mixin 架构重构：6 个 Mixin 类（CanvasConnections / CanvasBatchOps / CanvasMenu / CanvasBoxSelect / CanvasColors / CanvasLayout）完全改造为组合模式，通过 `self.canvas` 显式依赖，消除隐式 MRO 依赖
- Bug 修复：`NodeCanvas.__init__` 显式初始化 `box_select_rect` / `box_selected_nodes` / `is_connecting` 等状态变量；新增 `_save_color_settings()` / `_load_color_settings()` 转发 API；`CanvasLayout` 中 `self` 引用改为 `self.canvas`
- 完整启动测试验证：11 个模块导入、10 个组合层组件、3 个关键 API 调用，全流程通过

</details>

<details>
<summary><strong>【2026-06-17】V2.0.16 - 画布布局加载修复、自动打开项目异步化与节点增删持久化</strong></summary>

[查看完整更新](./2026-06-17/README.md)

**主要更新：**
- 画布布局加载修复：`load_layout` 增加 `try/finally` 确保 `setUpdatesEnabled(True)` 被调用；新增 `scene.update()` + `viewport.update()` 强制刷新；画布节点只来源于 `canvas_layout.json`
- 自动打开项目异步化重构：`_auto_open_project` 改为 `ProjectLoadWorker` Signal 模式，确保 `nodes_data` 先填充再创建画布；新增 `CanvasHost.remove_canvas_dock_by_path()` 防止 dock 残留
- 节点增删自动保存触发：`add_node_to_canvas` / `remove_node_from_canvas` 后触发 `_save_timer.start(500)` 防抖保存；修复子进程模式参数不匹配
- 空引用修复：`_terminal_dock` 未初始化 `hasattr` 保护；`NodeListDockPanel` 新增 `refresh()` 便捷方法

</details>

<details>
<summary><strong>【2026-06-16】V2.0.15 - 卡顿问题迭代优化方案</strong></summary>

[查看完整更新](./2026-06-16/README.md)

**主要更新：**
- 渲染层优化：SmartViewportUpdate、DeviceCoordinateCache，替换全场景刷新
- IO 异步化：新增 `ProjectLoadWorker` 后台线程扫描与 JSON 解析
- 算法层优化：`load_layout` 合并遍历、切换项目跳过重新扫描磁盘
- 后台降噪：PollingManager 降频，减少空闲 CPU 占用

</details>

<details>
<summary><strong>【2026-06-15】V2.0.14 - 节点样式统一化、Bug 修复与 Python 节点虚拟环境可迁移化</strong></summary>

[查看完整更新](./2026-06-15/README.md)

**主要更新：**
- 节点样式统一化：删除矩形/圆点样式，全系统统一为面板模式；锚点坐标修复（两侧边线中点）
- dialog_utils pick 函数 UnboundLocalError 修复：闭包定义前移
- 项目打开异步化与画布布局修复：`project_open` 改为 QTimer.singleShot 两阶段异步加载
- Python 节点虚拟环境可迁移化：`--copies` 创建 venv，start.json 去绝对路径，导入时 `_repair_portable_venv` 自动修复

</details>

<details>
<summary><strong>【2026-06-13】V2.0.13 - 日志系统架构重设计 & 历史回滚功能</strong></summary>

[查看完整更新](./2026-06-13/README.md)

**主要更新：**
- 日志系统架构重设计：双文件分离（`bnos.log` + `bnos_error.log`），三层防臃肿
- 进程管理全量性能安全修复：`taskkill /F /T` 进程树原子杀、PID 优先检测（10x+ 性能提升）、管道防阻塞、线程泄漏修复
- Photoshop 风格历史回滚：Command 模式 + HistoryManager 单例 + HistoryPanel 可视化面板
- 资源监测网络下载首次满载修复
- 节点样式切换尺寸不更新修复（DeviceCoordinateCache 缓存失效时序问题）
- 历史记录面板菜单入口补充
- 编码兼容：Emoji 清理 + SafeStreamHandler 双重保障

</details>

<details>
<summary><strong>【2026-06-12】V2.0.12 - 主窗口解耦与代码质量全面提升</strong></summary>

[查看完整更新](./2026-06-12/README.md)

**主要更新：**
- ApplicationContext 单例类聚合 11 个全局服务，统一生命周期管理
- 主窗口从 1500 行精简到 **499行**，拆分为 7 个 Mixin 模块（状态、生命周期、业务、面板、IPC、节点控制、交互）
- 测试框架：9 个测试文件，28+ 个单元测试用例
- i18n 字符串 Key 标准化，采用 `{domain}.{object}.{action}` 命名规范
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
