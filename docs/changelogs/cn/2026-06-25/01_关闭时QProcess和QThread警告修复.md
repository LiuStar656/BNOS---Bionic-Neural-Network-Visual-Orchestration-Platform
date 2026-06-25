# 关闭时 QProcess 和 QThread 警告修复

## 一、问题描述

关闭 BNOS 应用时出现两个 Qt 警告，且应用崩溃退出（退出码 `-1073740791`，`STATUS_STACK_BUFFER_OVERRUN`）：

```
QProcess: Destroyed while process ("powershell.exe") is still running.
QThread: Destroyed while thread 'StatsCollector' is still running
```

---

## 二、QThread 警告修复

### 根因

`StatsCollectorThread` 是 `PerformancePanel` 的子 QThread（`parent=self`）。当主窗口关闭时，Qt 从父到子递归销毁 Widget 树。在 `PerformancePanel` 被销毁时，其子 QThread 仍在 `run()` 循环中执行（`while self._running: ... msleep(2000)`），Qt 检测到线程未退出，输出警告。

### 为什么原有的 `_cleanup_on_shutdown()` 没有生效

关闭流程中 `_cleanup_on_shutdown()` 会遍历所有 Dock 面板，调用 `DockManager._stop_content_timers()` 和 `content.dispose()` 来停止线程。但 `closeEvent` 的顺序问题导致崩溃中断了清理链：

```
closeEvent()
  ├── _shutdown_orchestrator.execute()  ← 崩溃在此处
  │     └── stop_terminal_signals → 访问已析构的 C++ 对象 → SEGFAULT
  └── _cleanup_on_shutdown()  ← 永远到不了这里
```

### 修复

采用 **`QApplication.aboutToQuit` 信号** 方案，该信号在 Qt 销毁 Widget 树 **之前** 触发，确保线程在任何销毁逻辑执行前就被停止。

在 `PerformancePanel.__init__` 中注册回调：

```python
QApplication.instance().aboutToQuit.connect(self._on_app_quitting)
```

新增 `_stop_collector_thread()` 方法，安全停止线程：

```python
def _stop_collector_thread(self):
    if not hasattr(self, '_collector_thread'):
        return
    t = self._collector_thread
    if t.isRunning():
        t._running = False
        if not t.wait(5000):
            t.terminate()
            t.wait(1000)
```

同时给 `StatsCollectorThread.stop()` 添加超时参数，防止无限阻塞：

```python
def stop(self):
    self._running = False
    if not self.wait(5000):
        self.terminate()
        self.wait(1000)
```

### 修改文件

- `ui/panels/performance_panel.py`

---

## 三、QProcess 警告修复

### 根因

`TerminalProcess` 中的 `QProcess` 没有设置父对象，`stop()` 方法中的 `terminate()` 对控制台进程（`powershell.exe`）无效，导致主窗口销毁时 QProcess 底层 C++ 对象仍关联着未退出的子进程。

### 修复

1. **设置 Qt 父对象管理生命周期**：`QProcess(self)` — 父对象销毁时自动清理
2. **增强 `stop()` 终止链**：`terminate()` → `kill()` → `taskkill /F /T` OS 级别兜底
3. **新增 `_os_kill(pid)` 方法**：调用 Windows `taskkill /F /T /PID` 杀死整个进程树
4. **新增 `_disconnect_process()` 方法**：断开 4 个 QProcess 信号连接，防止野信号
5. **`process.close()` 清理**：终止完成后释放底层资源

### 修改文件

- `ui/core/terminal/terminal_process.py`

---

## 四、关闭流程顺序调整

### 问题

在测试过程中发现，若 `_shutdown_orchestrator.execute()` 在 `_cleanup_on_shutdown()` **之前**运行，`shiboken6.isValid()` 守卫会错误地跳过终端停止逻辑（因为 Dock 已在 `_cleanup_on_shutdown` 中被 dispose，C++ 对象失效）。

### 修复

恢复原始顺序：

```python
# 1. 先执行编排器（保存数据、停止终端、停止IPC、停止进程管理器）
self._shutdown_orchestrator.execute()

# 2. 再清理面板线程/定时器
self._cleanup_on_shutdown()

# 3. 最后接受关闭
event.accept()
```

由于 QThread 警告已通过 `aboutToQuit` 信号解决，关闭流程不再需要提前清理线程。

---

## 五、测试结果

| 检查项 | 修复前 | 修复后 |
|--------|--------|--------|
| `QProcess: Destroyed while process is still running` | ✗ 出现 | ✓ 消除 |
| `QThread: Destroyed while thread is still running` | ✗ 出现 | ✓ 消除 |
| 退出码 | `-1073740791`（崩溃） | `0`（正常） |
| 终端子进程清理 | 正常 | 正常 |

### 修改文件总览

| 文件 | 修改内容 |
|------|----------|
| `ui/panels/performance_panel.py` | 添加 `aboutToQuit` 信号处理、`_stop_collector_thread()` 方法、`StatsCollectorThread.stop()` 超时 |
| `ui/core/terminal/terminal_process.py` | `QProcess(self)` 父对象、`stop()` 增强、`_os_kill()`、`_disconnect_process()`、`process.close()` |
| `ui/main_window/lifecycle.py` | 关闭流程顺序调整、`_stop_content_timers` 增强（flag 线程检测） |
| `ui/core/dock_manager.py` | `_stop_content_timers` 增强：检测 `_running` flag 型线程并使用 `flag+wait` 模式 |
| `ui/core/thread_pool.py` | `shutdown()` 增强：超时从 5s 提升到 8s + 二次等待 |
| `ui/core/canvas_host.py` | `closeEvent` 添加 `RuntimeError` 保护 |
