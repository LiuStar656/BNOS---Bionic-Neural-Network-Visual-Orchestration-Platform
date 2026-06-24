# BNOS 更新日志

📖 英文版：[INDEX.md](../en/INDEX.md)

---

## 更新日志索引

点击下方日期查看该日期的详细更新：

### [2026-06-24](./2026-06-24/)
- **调试面板移除**：删除 debug_panel.py 和 node_debugger.py，清理全部 7 个文件引用，移除 34 个 i18n 键
- **性能分析面板异步化**：psutil.process_iter() 从主线程移入后台线程，消除打开面板时的 UI 冻结
- **面板生命周期防悬空指针**：_is_panel_alive() 使用 shiboken6.isValid() 检测 C++ 对象存活，修复 Internal C++ object already deleted 崩溃
- **菜单打钩标记修复**：6 个 Dock 面板 is_checked_fn 统一使用 config fallback，重启后自启面板正确显示打钩
- **Dock 标签栏位置**：主窗口 Dock 标签栏从底部移到顶部
- **Dock 双击事件组件化**：提取 DockDoubleClickHandler 统一处理双击标题栏/边缘切换浮动停靠，消除 BnosDock 与 BnosDockWidget 间重复代码
- **Dock 双击事件屏蔽**：因存在 Bug，采用 eventFilter + event.accept() 双重拦截彻底屏蔽双击切换浮动/停靠

### [2026-06-23](./2026-06-23/)
- **Dock 窗口吸附 Bug 修复**：修复 `BnosDock._on_top_level_changed` 中操作 `self.window()` 导致的崩溃问题，改为直接操作 `self`
- **Dock 边缘尺寸控制判定范围优化**：边缘拖拽判定区域从 6px 调整为 4px，减少误触
- **画布 Dock 双击边缘自动嵌入功能**：双击漂浮状态下的 Dock 边缘区域自动嵌入到 CanvasHost 并隐藏标题栏，屏蔽双击标题栏默认行为
- **CanvasHost 多余空间修复**：优化 `central_placeholder` 控件属性，确保不占用可见空间
- **Dock 浮动拖动双击嵌入位置异常分析**：记录悬浮窗口拖动后双击嵌入位置异常的已知问题、Qt 根因分析、尝试过的多种方案及当前状态

### [2026-06-22](./2026-06-22/)
- **连线渲染矢量轮廓填充**：使用 `QPainterPathStroker` 将线条的 `QPainterPath` 扩展为闭合轮廓路径，使用 `QBrush` 填充，彻底解决放大锯齿问题
- **高 DPI 屏幕适配**：主进程与画布子进程均启用 `AA_EnableHighDpiScaling` / `AA_UseHighDpiPixmaps`，确保 4K/Retina 屏幕效果；渲染提示启用 `SmoothPixmapTransform`
- **画布分辨率自定义**：设置对话框新增「渲染」标签页，5 个预设分辨率（1000-10000）+ 自定义宽高 + 抗锯齿开关，配置持久化至 `app_config.json`
- **restart_helper 脚本目录迁移**：`restart_helper.py` 从根目录迁入 `scripts/`，同时同步更新 `bnos_console.py` 的调用路径和 4 篇技术文档中的路径引用

### [2026-06-20](./2026-06-20/)
- **性能分析面板修复**：ChartCanvas 自定义绘制、QPainter/QPainterPath 导入修复、拖动暂停刷新
- **调试面板翻译补全**：17 个中英文翻译键补全（端口、模式、操作、断点等）
- **预设节点库重构**：废弃空壳模板系统，复用 `.bnos` 打包完整节点，新增 PresetLibraryDialog
- **IPC 核心进程命令扩展**：新增 node.stop_all（批量停止）和 node.detect_running 命令分发
- **轮询管理器动态调频**：CPU 负载自适应动态调频（1s/2s/4s）
- **翻译键值全面修订**：3 处错配修复，29 个新增键，17 个废弃键清理

### [2026-06-18](./2026-06-18/)
- **NodeItem 单体类拆分为组合模式**：`node_item.py` 从 846 行精简为 227 行，拆分为 9 个子组件（渲染、几何、交互、状态、配置、样式、参数面板等）
- **6 个 Mixin 类改造为组合模式**：`CanvasConnections` / `CanvasBatchOps` / `CanvasMenu` / `CanvasBoxSelect` / `CanvasColors` / `CanvasLayout` — 通过 `self.canvas` 显式依赖，消除隐式 MRO 依赖
- **节点启动队列功能实现**：智能调度器，支持并发控制、优先级调度、错误重试、启动间隔控制、队列持久化（当前仅用于限流）
- **节点启动队列与批量停止修复**：修复右键菜单无响应、`box_selected_nodes` 属性引用错误、批量停止只停一个节点、停止后无法重启、第二次批量启动无效等 10 个问题
- **完整启动测试验证**：所有模块导入 / 实例化 / API 调用 / 完整应用启动全流程通过

### [2026-06-17](./2026-06-17/)
- **画布布局加载修复**：`load_layout` 增加 `try/finally` 确保 `setUpdatesEnabled(True)` 被调用；新增 `scene.update()` + `viewport.update()` 强制刷新；画布节点只来源于 `canvas_layout.json`
- **自动打开项目异步化重构**：`_auto_open_project` 改为 `ProjectLoadWorker` Signal 模式，确保 `nodes_data` 先填充再创建画布；新增 `CanvasHost.remove_canvas_dock_by_path()` 防止 dock 残留
- **节点增删自动保存**：`add_node_to_canvas` / `remove_node_from_canvas` 后触发 `_save_timer.start(500)` 防抖保存；修复子进程模式参数不匹配
- **空引用修复**：`_terminal_dock` 未初始化 `hasattr` 保护；`NodeListDockPanel` 新增 `refresh()` 便捷方法

### [2026-06-16](./2026-06-16/)
- **卡顿问题迭代优化方案**：渲染层（SmartViewportUpdate、DeviceCoordinateCache）、IO 异步化（ProjectLoadWorker）、算法层（load_layout 合并遍历）、后台降噪（PollingManager 降频）四轮优化计划

### [2026-06-15](./2026-06-15/)
- **节点样式统一化**：删除矩形/圆点样式，全系统统一为面板模式，DetailedNodeStyle 直接继承 NodeStyle 基类
- **锚点坐标修复**：输入/输出锚点回落位置改为两侧边线中点，修正 setPos/_find_nearest 双倍偏移 bug
- **进程生命周期保护**：TerminalProcess 析构时 QProcess 已销毁的 RuntimeError 保护
- **dialog_utils pick 函数 UnboundLocalError 修复**：`go_up` / `sel_path` 闭包定义前移，解决打开项目/导入导出节点时的崩溃
- **项目打开异步化与画布布局修复**：`project_open` 改为 QTimer.singleShot 两阶段异步加载；修复第二个项目画布节点为空的问题（canvas_host.py 信号触发顺序）
- **Python 节点虚拟环境可迁移化**：`--copies` 创建 venv，start.json 去绝对路径，导入时 `_repair_portable_venv` 自动修复 `pyvenv.cfg`，打包跳过字节码缓存；跨机器迁移后无需重新 pip install

### [2026-06-14](./2026-06-14/)
- **PyQt6 → PySide6 全栈迁移**：许可证升级 GPLv3 → LGPLv3，100 个源文件 233 处 import 替换，信号/槽语法适配（pyqtSignal→Signal、pyqtSlot→Slot），零业务逻辑变更

### [2026-06-13](./2026-06-13/)
- **日志系统架构重设计**：双文件分离（`bnos.log` 按天轮转 + `bnos_error.log` 按大小轮转），三层防臃肿过滤器，ERROR/CRITICAL 永不过滤独立存储
- **PollingManager 修复**：修复 QObject C++ 层初始化崩溃（`super().__init__()` 顺序问题）
- **面板加载顺序优化**：CanvasHost 先画布后终端，减少启动闪烁
- **Emoji 清理**：全量替换为 `[TAG]` 标签，消除 Windows GBK 编码错误
- **进程管理全量性能安全修复**：`taskkill /F /T` 进程树原子杀、PID 优先检测（10x+）、管道防阻塞、线程泄漏修复
- **Photoshop 风格历史回滚**：Command 模式 + HistoryManager 单例 + HistoryPanel 可视化面板，支持点击跳转
- **资源监测与其他 Bug 修复**：网络下载首次满载、节点样式切换尺寸不更新、历史面板菜单入口

### [2026-06-12](./2026-06-12/)
- **P2 级别优化：主窗口进一步解耦**：将主窗口文件从约1500行精简到 **499行**，新增 4 个 Mixin 模块（面板管理、IPC通信、节点控制、窗口交互），实现细粒度职责分离
- **问题修复**：修复 Unicode 编码问题、权限检查、路径验证等 5 个问题
- **代码质量改进**：添加类型注解、代码去重、跨平台支持（Windows/macOS/Linux）

### [2026-06-11](./2026-06-11/)
- **连线端口锚点绑定保护与 canvas_layout 防改写**：修复连线在重启后端口锚点丢失问题，引入"期望端口名称记忆"机制和"锚点缺失不降质"保护

### [2026-06-10](./2026-06-10/)
- **Phase 10**：IDE 自动扫描 + 右键菜单 Action 集成（VSCode / Trae IDE 跨平台检测、非标准路径识别）
- **Phase 12**：自适应节点视图（ComfyUI 风格面板模式），11 种参数控件、画布直显、双向数据绑定
- **多锚点系统完善**：锚点差异化（16px/10px）、端口映射修正、连线持久化、批量清除完善

### [2026-06-09](./2026-06-09/)
- **CanvasHost 分割条位置持久化**：左侧节点面板/右侧调试面板的分割位置保存到 app_config
- **架构解耦与功能统一化**：右键菜单功能全部迁移到 Action 系统，UI 组件与业务逻辑解耦

### [2026-06-08](./2026-06-08/)
- **绘图工具状态持久化**：画笔/橡皮擦等绘图工具的选中状态保存至项目配置

### [2026-06-07](./2026-06-07/)
- **节点状态同步与项目持久化完善**：节点启停状态、配置写入与恢复
- **Toast 提示机制与 Action 系统扩展**：统一通知队列管理

### [2026-06-06](./2026-06-06/)
- **Toast 通知视觉效果全面修复**：通知气泡的样式、动画、位置
- **代码健壮性修复**：多处空值/异常处理加固

### [2026-06-05](./2026-06-05/)
- **强制删除节点文件夹**：节点目录清理
- **异步启动/停止/挂载/刷新节点**：GUI 无阻塞交互
- **节点配置菜单启动后保持打开**
- **绘图工具栏按需显示功能**
- **进程树终止机制**
- **JSON 启动虚拟环境支持**
- **节点状态显示与进程检测修复**

### [2026-05-23](./2026-05-23/)
- **全局状态同步改造**：全局轮询管理器、资源监测重构
- **画布布局加载增强**
- **面板状态持久化**
- **侧边工具栏尺寸放大与图标修复**
- **VS Code Codicon 图标系统集成**
- **独立启动器、三态状态灯、Ctrl+D 删除**
- **启动动画、品牌重命名（BnosConsole → BNOS）、README 重构**

### [2026-05-22](./2026-05-22/)
- **ComfyUI 风格连线重构 + 人工折叠交互**：贝塞尔曲线、节点折叠/展开
- **节点注册表 + 挂载外部节点**：可扩展节点管理系统

### [2026-05-21](./2026-05-21/)
- **GUI 架构重构与功能增强**：QGraphicsView/Scene 体系搭建
- **节点样式系统**：方形版 / 圆形版样式切换
- **画布可视区域渲染优化**
- **VSCode 风格深色无边框窗口**
- **四项重大计划实施**
- **UI 精简与优化**
- **重大架构重构：UI 组件模块化与菜单栏整合**

### [2026-05-20](./2026-05-20/)
- **Canvas Widget 模块化拆分**：将画布组件按职责拆分为多个独立模块

### [2026-05-19](./2026-05-19/)
- 早期功能与界面迭代

### [2026-05-18](./2026-05-18/)
- 基础功能与节点管理

### [2026-05-17](./2026-05-17/)
- 项目早期版本迭代

### [2026-05-08](./2026-05-08/)
- 项目早期版本迭代

### [2026-05-07](./2026-05-07/)
- 项目早期版本迭代

---

**最后更新**：2026-06-24