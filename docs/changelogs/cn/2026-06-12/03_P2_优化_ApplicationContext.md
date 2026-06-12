# P2 级别优化：ApplicationContext 聚合全局状态

## 概述

创建了 `ApplicationContext` 单例类，统一聚合所有全局状态持有者，提供统一的服务访问入口。

## 优化内容

### 新建文件

**`ui/core/application_context.py`**

创建了 `ApplicationContext` 单例类，聚合以下服务：

| 服务名称 | 属性名 | 说明 |
|----------|--------|------|
| AppConfig | `config` | 配置服务 |
| EventBus | `event_bus` | 事件总线 |
| PollingManager | `polling` | 轮询管理器 |
| NodeControlService | `node_control` | 节点控制服务 |
| ProcessManager | `process_manager` | 进程管理器 |
| PanelManager | `panel_manager` | 面板管理器 |
| DockManager | `dock_manager` | Dock 管理器 |
| ToastQueueManager | `toast_manager` | Toast 管理器 |
| ShortcutManager | `shortcut_manager` | 快捷键管理器 |
| FileOperationManager | `file_operation` | 文件操作管理器 |
| ImportExportManager | `import_export` | 导入导出管理器 |

### 修改文件

**`bnos_console.py`**

- 在 Qt 初始化后调用 `ApplicationContext.initialize()`
- 在主窗口创建后调用 `ApplicationContext.initialize_ui_services(window)`
- 在应用退出前调用 `ApplicationContext.shutdown()`

## 设计特点

1. **延迟初始化**：依赖主窗口的服务（如 PanelManager、DockManager）延迟到主窗口创建后初始化
2. **统一入口**：所有模块通过 `ApplicationContext()` 单例访问服务
3. **生命周期管理**：提供 `initialize()` 和 `shutdown()` 方法管理服务生命周期

## 使用方式

```python
from ui.core.application_context import ApplicationContext

ctx = ApplicationContext()
ctx.config.save()
ctx.node_control.start_node(node_id)
```

## 验证结果

- ✅ GUI 正常启动
- ✅ 所有服务正确初始化
- ✅ 项目正常加载

## 收益

- 减少全局变量分散
- 提高代码可维护性
- 便于依赖注入和测试
