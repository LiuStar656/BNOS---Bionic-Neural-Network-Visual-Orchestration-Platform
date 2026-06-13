# 【2026-06-13】V2.0.13 - 日志系统架构重设计 & 历史回滚功能

---

## 更新列表

### 1. 日志系统架构重设计

[详细内容](./01_日志系统架构重设计.md)

- 双文件分离：`bnos.log`（按天轮转）+ `bnos_error.log`（按大小轮转，独立存储错误）
- 三层防臃肿：FrequencyFilter → DebugLevelManager → 轮转清理
- ERROR/CRITICAL 永不过滤，错误日志独立可查
- SafeStreamHandler 处理 Windows GBK 编码兼容
- 启动自动清理 7 天前旧日志

### 2. PollingManager super().__init__() 修复

- 修复单例模式下 QObject C++ 层未初始化的崩溃
- `super().__init__(parent)` 移到单例检查之前

### 3. CanvasHost 面板加载顺序调整

- 终端 Dock 延迟到第一个画布创建后初始化
- 先画布面板后终端面板，减少启动闪烁

### 4. Emoji 清理

- 所有日志调用中 emoji 替换为 `[TAG]` 标签前缀
- 彻底解决 Windows GBK 编码下的 UnicodeEncodeError

### 5. 进程管理全量性能安全修复

[详细内容](./03_进程管理全量性能安全修复.md)

- **进程树原子杀**：`taskkill /F /T` 确保子进程与主进程同步终止，消除僵尸进程
- **PID 优先检测**：`_is_pid_alive` 通过 `OpenProcess` 直接检测进程存活，替代全量 PowerShell 扫描（性能提升 10x+）
- **stopped 节点跳过**：`check_running_processes` 跳过无 PID 的已停止节点，减少无效轮询
- **monitor 线程追踪清理**：`NodeControlService` 的 monitor 线程增加 finally 清理，防止线程泄漏
- **NodeItem.dispose()**：节点从画布移除时断开信号连接、停止计时器、清除缓存，防止信号/内存泄漏
- **subprocess PIPE→DEVNULL**：子进程管道缓冲区改为 DEVNULL，避免管道阻塞导致进程僵死

### 6. Photoshop 风格历史回滚功能

[详细内容](./04_Photoshop风格历史回滚功能.md)

- **Command 模式**：CreateNodeCommand / DeleteNodeCommand / MoveNodeCommand / CreateEdgeCommand / DeleteEdgeCommand
- **HistoryManager 单例**：扁平 commands 列表 + current_index 指针，支持 undo/redo/jump_to 任意位置跳转
- **HistoryPanel 面板**：可视化历史记录列表，点击任意条目跳转到对应状态
- **自动录制**：连线增删自动录制，重放保护机制防止二次执行
- **锚点精确恢复**：`_resolve_anchor` 优先使用 `_desired_target_port_name` 查找正确锚点，解决多端口场景下恢复错误

### 7. 资源监测与其他 Bug 修复

[详细内容](./05_资源监测与其他Bug修复.md)

- **资源监测网络下载首次满载修复**：预热 `net_io_counters()` 结果存入 `_last_net_*`，首次查询 diff 为零
- **节点样式切换尺寸不更新修复**：`DeviceCoordinateCache` 缓存失效时序修复 + `_ensure_rect()` 兜底
- **历史记录面板菜单入口补充**：工具菜单添加「历史记录」入口

---

## 主要更新

| 类别 | 更新内容 |
|------|----------|
| **日志架构** | 双文件分离，三层防臃肿，错误独立存储 |
| **进程管理** | 进程树原子杀、PID 优先检测、管道防阻塞、线程泄漏修复 |
| **历史回滚** | Photoshop 风格 Command 模式 + HistoryManager + HistoryPanel |
| **Bug 修复** | PollingManager QObject 初始化、资源监测首次满载、节点样式切换尺寸 |
| **面板优化** | CanvasHost 加载顺序调整、历史面板菜单入口 |
| **编码兼容** | Emoji 清理 + SafeStreamHandler 双重保障 |

---

## 验证结果

- ✅ 新日志文件 `bnos.log` / `bnos_error.log` 正常生成
- ✅ 控制台输出无 UnicodeEncodeError
- ✅ polling_manager 全局文件监控引用已同步更新
- ✅ 旧日志文件引用全部清理完毕
- ✅ 进程树原子杀通过 `/F /T` 消除僵尸进程
- ✅ 历史回滚 undo/redo 正确恢复节点位置、连线、锚点绑定
- ✅ 资源监测网络下载首次显示正确（不再满载）
- ✅ 面板模式→框图模式尺寸正确切换
