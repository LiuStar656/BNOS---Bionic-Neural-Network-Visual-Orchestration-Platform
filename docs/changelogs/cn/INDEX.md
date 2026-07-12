# BNOS 更新日志

📖 英文版：[INDEX.md](../en/INDEX.md)

---

## 更新日志索引

点击下方日期查看该日期的详细更新：

### [2026-07-12](./2026-07-12/)
- **代码规范统一化整改**：全项目 227 文件工具链引入（Ruff + Pre-commit + EditorConfig + Pylance）；消除 8 个真实运行时 Bug；Logger 4 种写法统一；`print()` 迁移 `logger.info()`；219 文件新增 `from __future__ import annotations`；`# type: ignore` 清零；`os.path` → `pathlib.Path` 691→156（-77%）；死代码清理；最终 ruff/pytest/Pylance 全绿
- **节点资源限制组件**：全平台 CPU/内存硬限制（Linux cgroups v2 / Windows Job Objects / macOS nice），config.json 新增 `resource_limit` 可选字段，21 个新测试，规范文档更新第八章
- **_port_routing 端口路由机制**：路由信息从内部节点 config.json 迁移到 node_clusters.json 的 `_port_routing` 字段，解耦端口路由与节点配置，解决写入 `listen_upper_file` 导致输入端口消失的核心问题；节点 `main.py` 零改动
- **复合节点连线与折叠修复**：展开/折叠连线更新抖动修复（补充 `update_path()` 调用、`_batch_updating` 标志、跳过拖拽节点双重 `setPos`）；config 写入诊断增强；`_port_routing` 残留清理
- **单入口 DAG 防错机制**：新增 `_validate_dag_single_entry` 校验方法，压缩/折叠时检测多入口拒绝操作，支持 A→B→C 或 A→B 同时 A→C，不允许多入口 DAG
- **国际化**：新增 3 个中英文翻译键（入口检测、多入口拒绝、折叠阻止标题）
- **复合节点UI交互与连线系统第二轮修复**：右键菜单展开/折叠；复合节点输出锚点连线；展开态 UI 交互修复（CompositeGroupFrame 形状重写）；折叠后线条残留清理（多复合节点安全）；连线 config.json 双向同步与展开/折叠重新对齐；端口识别遵循 config.json；折叠后锚点失效修复（保存→刷新→重新绑定）；内部节点拖动抖动修复（预设锚点+逐帧更新）；文件保存 PermissionError 重试机制；SelectedNodesList 序列化修复；AnchorItem 参数匹配修复
- **复合节点系统**：多节点压缩为虚拟节点，DAG 拓扑排序编排，支持解耦还原，画布专用渲染，节点列表集成
- **全局防呆机制**：40 项防御覆盖进程管理、文件持久化、信号生命周期、资源清理、路径安全、线程安全、配置校验、并发控制
- **项目文件锁**：`.bnos_project.lock` 防止多实例同时打开同一项目导致数据损坏
- **架构债修复**：消除双选状态（SelectedNodesList 代理）、修复懒导入、消除 `__del__` 改用 `dispose()`、节点扫描增加 config.json 校验
- **进程日志捕获与DI容器增强**：子进程输出从 DEVNULL 改为持久化日志文件，启动失败自动读取日志尾部；DI 容器重构为复合键存储，新增命名注册、作用域控制（singleton/transient）、服务列表查询
- **国际化集中管理**：创建翻译 key 集中注册表（translation_keys.py），270+ key 以类属性暴露，提供 IDE 自动补全和重构支持；新增 validate_all_keys() 一致性检查；补全 8 个英文渲染设置翻译
- **Core目录组件分类重组**：ui/core/ 45 个模块按功能拆分为 node/dock/system/services/project/config/i18n 七个子目录，150+ 处 import 路径同步更新，修复重组过程中引入的编码损坏和 UnboundLocalError
- **复合节点监控与日志修复**：折叠态聚合 CPU/MEM 显示（psutil 进程树），PIPE→文件日志落盘，View Log 支持复合双日志，get_node_pid() 回退 __composite_{id}.pid
- **复合节点健壮性增强**：拖拽性能（mouseRelease 批量持久化），磁盘异常防护（PermissionError/OSError），config 冲突校验（展开快照→折叠对比），编排器断点续跑（output.json 缓存跳过），分布式传输接口预埋
- **BNOS Build 驱动引擎方案**：导出模式→驱动层注入；引擎与源文件完全隔离；新增 --clean/--update/--docker 命令；独立/复合节点混合支持
- **except Exception: pass 全面治理**：100 处清零，26 文件修改；替换为精确类型（OSError、ProcessLookupError、psutil.NoSuchProcess、RuntimeError 等）
- **连线正交吸附功能**：拖拽折叠点吸附 90°/180° 直角交点；Shift 临时禁用；右键菜单开关；SNAP_THRESHOLD = 20px
- **复合节点配置文件与资源组**：composite.json Schema 定义与自愈恢复；压缩时创建 composite_nodes/<id>/ 完整目录结构；node_registry.json 运行时登记簿；日志路径从 venv 迁移到 composite_nodes/<id>/logs/；解压缩日志存档（.archive/）；复合节点 venv 生命周期绑定
- **启动守卫与资源监测双层架构**：独立节点启动前检查所属复合节点运行状态（三选一弹窗）；复合节点启动前检查子节点独立运行状态（自动停止）；资源面板 orchestrator PID 独立监测行；子节点 [sub] 缩进行（进程内 vs 独立运行区分）
- **复合节点防错窗口风格统一**：6 处 QMessageBox → themed_message()（确认/折叠/失败）；深色圆角无边框与 BNOS 主题一致；复用 i18n 标准键
- **节点配置对话框国际化**：20 处硬编码中英文字符串 → `t(TK.KEY)`；Resource Limits 区域全面国际化；+19 键
- **Bug 修复**：GROUP_PREFIX AttributeError、blockSignals 双击/右键失效、clear_box_selection 方法名错误、node_list_context UnboundLocalError、status_manager C++ 对象已删除 RuntimeError、app_config 类型校验兼容、QProcess destroyed while running、无 config.json 目录被误加载为节点

### [2026-07-08](./2026-07-08/)
- **节点启动机制改进**：`start.json` 新增 `entry` 字段支持自定义启动程序，默认值为 `main.py`，向后兼容
- **输入输出锚点条件渲染**：当 `config.json` 中不存在 `listen_upper_file`/`output_file` 字段时不渲染输入/输出锚点
- **参数定义与代码清理**：`ParameterDef` 添加 `description` 字段支持，移除 `AnchorManager` 中未使用的死代码

### [2026-07-07](./2026-07-07/)
- **节点名称支持中文命名**：验证规则从仅允许字母数字改为排除文件系统保留字符，统一使用 NodeNameValidator，更新中英文错误提示

### [2026-07-03](./2026-07-03/)
- **终端面板内存泄漏修复**：_stop_content_timers() 新增 QProcess 三级终止链和 TerminalWidget.close_terminal() 显式清理，解决面板隐藏/关闭时 powershell.exe 进程残留问题
- **docs 文档整理**：按职能将 46 个散落文档分类到 archive/、design/、reference/，新增导航索引 README.md，更新 6 处跨文件路径引用

### [2026-07-02](./2026-07-02/)
- **自定义标题栏窗口缩放修复**：nativeEvent MRO 遮蔽修复 + QCursor.pos() 坐标获取替代 ctypes.MSG.lParam，解决上/左/右/右下边缘缩放均异常的问题

### [2026-06-25](./2026-06-25/)
- **QThread 警告修复**：PerformancePanel 使用 `QApplication.aboutToQuit` 信号在 Qt 销毁控件树前停止 StatsCollectorThread，消除关闭时线程残留警告
- **QProcess 警告修复**：TerminalProcess 设置 QProcess(self) 父对象 + 增强 stop() 终止链（terminate→kill→taskkill）+ 信号断开 + process.close()
- **崩溃修复**：关闭流程顺序优化与 C++ 对象存活保护，退出码从 `-1073740791` 恢复为 `0`

### [2026-06-24](./2026-06-24/)
- **调试面板移除**：删除 debug_panel.py 和 node_debugger.py，清理全部 7 个文件引用，移除 34 个 i18n 键
- **性能分析面板异步化**：psutil.process_iter() 从主线程移入后台线程，消除打开面板时的 UI 冻结
- **面板生命周期防悬空指针**：_is_panel_alive() 使用 shiboken6.isValid() 检测 C++ 对象存活，修复 Internal C++ object already deleted 崩溃
- **菜单打钩标记修复**：6 个 Dock 面板 is_checked_fn 统一使用 config fallback，重启后自启面板正确显示打钩
- **Dock 标签栏位置**：主窗口 Dock 标签栏从底部移到顶部
- **Dock 双击事件组件化**：提取 DockDoubleClickHandler 统一处理双击标题栏/边缘切换浮动停靠，消除 BnosDock 与 BnosDockWidget 间重复代码
- **Dock 双击事件屏蔽**：因存在 Bug，采用 eventFilter + event.accept() 双重拦截彻底屏蔽双击切换浮动/停靠
- **更新日志查看器**：菜单栏新增「帮助→查看更新日志」入口，QWebEngineView + markdown 库渲染，自动根据语言读取中英文 changelogs，支持交互式折叠展开

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

**最后更新**：2026-07-12