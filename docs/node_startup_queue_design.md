
# 节点启动排队功能开发方案 V2.0

---

## 目录

1. [需求分析](#1-需求分析)
2. [架构设计](#2-架构设计)
3. [核心实现](#3-核心实现)
4. [API 设计](#4-api-设计)
5. [集成方案](#5-集成方案)
6. [UI 更新](#6-ui-更新)
7. [配置与默认值](#7-配置与默认值)
8. [代码结构](#8-代码结构)
9. [测试计划](#9-测试计划)
10. [性能考虑](#10-性能考虑)
11. [向后兼容性](#11-向后兼容性)
12. [安全考虑](#12-安全考虑)

---

## 1. 需求分析

### 1.1 问题背景

当前节点启动机制存在以下问题：

| 问题点 | 描述 | 影响 |
| :--- | :--- | :--- |
| 无排队机制 | 批量启动时节点几乎同时启动 | 资源竞争、端口冲突、CPU/内存瞬间飙升 |
| 无并发控制 | 无法限制同时启动的节点数量 | 系统负载过高，可能导致响应变慢 |
| 无优先级管理 | 所有节点同等对待 | 关键节点可能晚于非关键节点启动 |
| 无依赖感知 | 启动顺序不考虑节点间的数据依赖 | 依赖节点先启动导致大量错误日志 |
| 状态反馈不完整 | 缺少"排队中"状态 | 用户无法感知启动进度 |
| 错误处理不完善 | 单个节点失败不影响其他节点，但无重试机制 | 需要手动重新启动失败节点 |
| 队列不持久化 | 关闭应用后队列状态丢失 | 用户体验不连贯 |

### 1.2 功能需求

基于分析，设计以下功能：

| 功能 | 描述 | 优先级 |
| :--- | :--- | :--- |
| 启动队列管理 | 支持节点进入队列等待启动 | 高 |
| 并发控制 | 可配置同时启动的节点数量（默认2个） | 高 |
| 优先级调度 | 支持设置节点启动优先级 | 高 |
| **拓扑依赖启动** | 自动解析节点间连接关系，按依赖顺序启动 | **高** |
| 状态反馈 | 新增"queued"状态，显示排队位置 | 高 |
| 队列操作 | 支持取消排队、插队、清空队列 | 中 |
| 错误重试 | 支持失败自动重试（可配置次数） | 中 |
| **启动间隔控制** | 批次间平滑延迟，避免资源抢占 | 中 |
| **队列持久化** | 退出时保存队列状态，重启后恢复 | 中 |

---

## 2. 架构设计

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        节点启动排队系统 V2.0                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐   │
│   │  UI Layer       │      │   EventBus       │      │  Canvas Layout  │   │
│   │ (节点列表/画布)  │──────▶│   (状态通知)     │◀─────│  (依赖关系解析) │   │
│   └────────┬────────┘      └────────┬─────────┘      └──────────────────┘   │
│            │                        │                                        │
│            ▼                        ▼                                        │
│   ┌───────────────────────────────────────────────────────────────┐         │
│   │          NodeStartupQueueManager                              │         │
│   │  ┌─────────────────────────────────────────────────────────┐ │         │
│   │  │  Queue: [Node1, Node2, Node3, ...]                     │ │         │
│   │  ├─────────────────────────────────────────────────────────┤ │         │
│   │  │  Running Slots: [Slot1, Slot2]                          │ │         │
│   │  ├─────────────────────────────────────────────────────────┤ │         │
│   │  │  Dependency Graph: A → B → C                            │ │         │
│   │  ├─────────────────────────────────────────────────────────┤ │         │
│   │  │  Config: max_concurrent=2, retry_count=3, delay=300ms   │ │         │
│   │  └─────────────────────────────────────────────────────────┘ │         │
│   └──────────────────────────────┬──────────────────────────────┘           │
│                                  │                                         │
│                                  ▼                                         │
│   ┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐   │
│   │  node_process   │      │ node_control_service │   │   Queue Snapshot│   │
│   │ (实际启动逻辑)   │◀─────│   (状态管理)       │◀────│  (队列持久化)    │   │
│   └─────────────────┘      └──────────────────┘      └──────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 职责 | 所属文件 |
| :--- | :--- | :--- |
| `NodeStartupQueueManager` | 队列管理核心类（含依赖解析） | `ui/core/node_startup_queue.py` |
| `QueueItem` | 队列项数据结构 | `ui/core/node_startup_queue.py` |
| `QueueStatus` | 队列状态枚举 | `ui/core/node_startup_queue.py` |
| `DependencyAnalyzer` | 拓扑依赖分析器 | `ui/core/node_startup_queue.py` |
| `QueueSnapshotManager` | 队列持久化管理器 | `ui/core/node_startup_queue.py` |
| `start_node_process` | 现有启动函数 | `ui/core/node_process.py` |
| `node_control_service` | 现有状态管理 | `ui/core/node_control_service.py` |

### 2.3 数据结构设计

#### QueueItem 类

```python
class QueueItem:
    def __init__(self, node_name: str, priority: int = 0):
        self.node_name = node_name          # 节点名称
        self.priority = priority            # 优先级（数值越大优先级越高）
        self.status = QueueStatus.QUEUED    # 当前状态
        self.retry_count = 0                # 已重试次数
        self.enqueue_time = None            # 入队时间
        self.start_time = None              # 开始启动时间
        self.complete_time = None           # 完成时间
        self.error_message = None           # 错误信息
        self.dependencies = []              # 依赖的上游节点名称列表
        self.blocked_by = []                # 当前阻塞本节点的依赖节点
```

#### QueueStatus 枚举

```python
class QueueStatus(Enum):
    QUEUED = "queued"           # 排队中
    BLOCKED = "blocked"         # 被依赖阻塞
    STARTING = "starting"       # 启动中
    SUCCESS = "success"         # 启动成功
    FAILED = "failed"           # 启动失败
    CANCELLED = "cancelled"     # 已取消
```

---

## 3. 核心实现

### 3.1 NodeStartupQueueManager 类设计

#### 关键方法

| 方法 | 功能 | 参数 | 返回值 |
| :--- | :--- | :--- | :--- |
| `__init__()` | 初始化队列管理器 | `max_concurrent: int = 2`, `max_retry: int = 3`, `batch_delay: int = 300` | - |
| `enqueue()` | 将节点加入队列 | `node_name: str`, `priority: int = 0`, `dependencies: List[str] = None` | `bool` |
| `dequeue()` | 从队列移除节点 | `node_name: str` | `bool` |
| `start_queue()` | 启动队列调度 | - | `None` |
| `stop_queue()` | 停止队列调度 | - | `None` |
| `clear_queue()` | 清空队列 | - | `None` |
| `get_queue_status()` | 获取队列状态 | - | `dict` |
| `get_queued_nodes()` | 获取排队中的节点列表 | - | `List[str]` |
| `promote_node()` | 提升节点优先级（插队） | `node_name: str`, `new_priority: int` | `bool` |
| `resolve_dependencies()` | 从画布连接关系解析依赖 | - | `None` |
| `save_snapshot()` | 保存队列快照 | - | `bool` |
| `load_snapshot()` | 加载队列快照 | - | `bool` |

#### 状态流转

```
QUEUED ──(依赖未满足)──▶ BLOCKED ──(依赖就绪)──▶ QUEUED
   │                          │
   │                          └──(轮到启动)──▶ STARTING ──(成功)──▶ SUCCESS
   │                                               │
   │                                               └──(失败)──▶ FAILED ──(重试)──▶ QUEUED
   │
   └──(取消)──▶ CANCELLED
```

### 3.2 拓扑依赖启动（核心亮点）

#### 依赖解析逻辑

```python
def resolve_dependencies(self):
    """从画布连接关系自动解析节点依赖
    
    遍历所有连接，建立节点间的依赖图：
    - 如果 NodeA 的输出连接到 NodeB 的输入，则 NodeB 依赖 NodeA
    - NodeB 必须在 NodeA 启动成功后才能启动
    """
    if not self._canvas_layout:
        return
    
    # 清空现有依赖关系
    for item in self._queue:
        item.dependencies = []
    
    # 遍历画布连接
    for conn in self._canvas_layout.get_connections():
        source_node = conn['source_node']
        target_node = conn['target_node']
        
        # 找到对应的队列项并添加依赖
        for item in self._queue:
            if item.node_name == target_node:
                if source_node not in item.dependencies:
                    item.dependencies.append(source_node)
                    logger.debug(f"解析依赖: {target_node} 依赖 {source_node}")
```

#### 就绪检查（Ready Check）

```python
def _get_ready_nodes(self):
    """获取当前就绪的节点（依赖已满足或无依赖）
    
    就绪条件：
    1. 节点状态为 QUEUED
    2. 所有上游依赖节点已成功启动（running/idle），或也在队列中但已完成启动
    3. 依赖节点不在 STARTING 状态（避免竞态）
    """
    ready = []
    blocked_info = {}
    
    for item in self._queue:
        if item.status != QueueStatus.QUEUED:
            continue
        
        # 获取该节点依赖的上游节点列表
        upstream = item.dependencies
        
        if not upstream:
            # 无依赖节点，直接就绪
            ready.append(item)
            continue
        
        # 检查上游是否已经启动成功或在队列中已完成
        blocked_by = []
        for up_node in upstream:
            up_status = self._get_node_status(up_node)
            
            if up_status in ('running', 'idle'):
                # 上游已成功启动
                continue
            elif up_status == 'success':
                # 上游在本次队列中已成功
                continue
            elif up_status == 'starting':
                # 上游正在启动中，等待
                blocked_by.append(f"{up_node} (启动中)")
            elif up_status == 'queued':
                # 上游也在队列中但还没启动
                blocked_by.append(f"{up_node} (排队中)")
            elif up_status == 'failed':
                # 上游启动失败，标记为阻塞
                blocked_by.append(f"{up_node} (启动失败)")
            elif up_status == 'blocked':
                # 上游也被阻塞
                blocked_by.append(f"{up_node} (阻塞中)")
            else:
                # 上游未启动或不存在
                blocked_by.append(f"{up_node} (未启动)")
        
        if blocked_by:
            # 依赖未满足，标记为阻塞状态
            item.status = QueueStatus.BLOCKED
            item.blocked_by = blocked_by
            blocked_info[item.node_name] = blocked_by
            logger.debug(f"节点 {item.node_name} 被阻塞: {blocked_by}")
        else:
            # 所有依赖已满足
            item.status = QueueStatus.QUEUED
            item.blocked_by = []
            ready.append(item)
    
    # 如果存在阻塞的节点，发送状态通知
    if blocked_info:
        self._notify_queue_updated(blocked_info=blocked_info)
    
    return ready
```

### 3.3 智能队列调度器（带启动间隔）

```python
def _process_queue(self):
    """队列调度主逻辑 - 智能DAG调度器
    
    核心特性：
    1. 并发控制：同时启动的节点数不超过 max_concurrent
    2. 依赖感知：只有依赖满足的节点才能启动
    3. 优先级调度：高优先级节点优先
    4. 平滑启动：批次间加入延迟，避免资源竞争
    """
    if self._stopped:
        return
    
    # 检查是否有空闲槽位
    running_count = len([item for item in self._queue 
                         if item.status == QueueStatus.STARTING])
    
    if running_count >= self._max_concurrent:
        # 槽位已满，稍后重试
        self._schedule_next_process()
        return
    
    # 步骤1: 获取当前就绪的节点（依赖已满足）
    ready_items = self._get_ready_nodes()
    
    if not ready_items:
        # 没有就绪节点，检查是否还有未完成的节点
        pending_items = [item for item in self._queue 
                         if item.status in (QueueStatus.QUEUED, QueueStatus.BLOCKED)]
        
        if pending_items:
            # 还有等待中的节点，继续轮询
            self._schedule_next_process(delay=500)
            return
        else:
            # 队列为空或已全部完成
            logger.info("队列调度完成")
            self._notify_queue_empty()
            return
    
    # 步骤2: 按优先级排序就绪节点
    ready_items.sort(key=lambda x: (-x.priority, x.enqueue_time))
    
    # 步骤3: 启动下一个就绪节点
    next_item = ready_items[0]
    self._start_node(next_item)
    
    # 步骤4: 调度下一次处理（带延迟）
    self._schedule_next_process()

def _schedule_next_process(self, delay=None):
    """调度下一次队列处理
    
    使用 QTimer.singleShot 递归触发，避免阻塞主线程
    相邻批次之间加入 200ms~500ms 的间隔，给系统留出资源释放时间
    """
    if delay is None:
        delay = self._batch_delay
    
    from PySide6.QtCore import QTimer
    QTimer.singleShot(delay, self._process_queue)

def _start_node(self, item):
    """启动单个节点（异步执行）"""
    item.status = QueueStatus.STARTING
    item.start_time = time.time()
    
    # 发送启动开始事件
    self._notify('node_starting', node_name=item.node_name)
    
    # 使用后台线程启动节点
    worker = NodeStartWorker(item, self._nodes_data)
    worker.finished.connect(lambda success, err: self._on_node_start_complete(item, success, err))
    worker.start()

def _on_node_start_complete(self, item, success, error):
    """节点启动完成回调"""
    if success:
        item.status = QueueStatus.SUCCESS
        item.complete_time = time.time()
        logger.info(f"节点启动成功: {item.node_name}")
        self._notify('node_started', node_name=item.node_name)
        
        # 触发重新调度（可能有节点因本节点成功而变为就绪）
        self._schedule_next_process(delay=100)
    else:
        item.error_message = error
        item.retry_count += 1
        
        if item.retry_count < self._max_retry:
            # 重试：将状态改回 QUEUED，等待下一轮调度
            item.status = QueueStatus.QUEUED
            logger.warning(f"节点启动失败，将重试 ({item.retry_count}/{self._max_retry}): {item.node_name}")
            self._notify('node_retry', node_name=item.node_name, retry_count=item.retry_count)
            self._schedule_next_process(delay=self._retry_delay)
        else:
            item.status = QueueStatus.FAILED
            logger.error(f"节点启动失败（已达最大重试次数）: {item.node_name} - {error}")
            self._notify('node_failed', node_name=item.node_name, error=error)
            
            # 检查是否有依赖该节点的其他节点需要处理
            self._handle_dependency_failure(item.node_name)
        
        # 继续处理队列
        self._schedule_next_process()

def _handle_dependency_failure(self, failed_node):
    """处理依赖节点启动失败的情况"""
    for item in self._queue:
        if failed_node in item.dependencies:
            # 通知用户该节点的启动被阻塞
            self._notify('node_blocked', 
                        node_name=item.node_name,
                        blocked_by=f"{failed_node} (启动失败)")
```

### 3.4 队列持久化机制

#### 快照数据结构

```python
class QueueSnapshot:
    """队列快照 - 用于持久化和恢复"""
    
    def __init__(self):
        self.items = []          # 队列项列表
        self.timestamp = 0       # 保存时间戳
        self.max_concurrent = 2  # 并发数配置
        self.max_retry = 3       # 重试配置
    
    def from_queue(self, queue_manager):
        """从队列管理器生成快照"""
        self.timestamp = time.time()
        self.max_concurrent = queue_manager._max_concurrent
        self.max_retry = queue_manager._max_retry
        
        for item in queue_manager._queue:
            if item.status in (QueueStatus.QUEUED, QueueStatus.BLOCKED, QueueStatus.STARTING):
                self.items.append({
                    'node_name': item.node_name,
                    'priority': item.priority,
                    'status': item.status.value,
                    'retry_count': item.retry_count,
                    'enqueue_time': item.enqueue_time,
                    'dependencies': item.dependencies
                })
    
    def to_queue(self, queue_manager):
        """从快照恢复队列"""
        for item_data in self.items:
            queue_manager.enqueue(
                node_name=item_data['node_name'],
                priority=item_data['priority']
            )
            # 恢复重试计数和依赖
            item = queue_manager._get_item(item_data['node_name'])
            if item:
                item.retry_count = item_data.get('retry_count', 0)
                item.dependencies = item_data.get('dependencies', [])
                item.status = QueueStatus(item_data['status'])
```

#### 持久化操作

```python
def save_snapshot(self):
    """保存队列快照到文件
    
    快照文件位置: <project_path>/.queue_snapshot.json
    """
    if not self._project_path:
        return False
    
    try:
        snapshot = QueueSnapshot()
        snapshot.from_queue(self)
        
        snapshot_path = os.path.join(self._project_path, '.queue_snapshot.json')
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump({
                'items': snapshot.items,
                'timestamp': snapshot.timestamp,
                'max_concurrent': snapshot.max_concurrent,
                'max_retry': snapshot.max_retry
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"队列快照已保存: {snapshot_path}")
        return True
    except Exception as e:
        logger.error(f"保存队列快照失败: {e}")
        return False

def load_snapshot(self):
    """加载队列快照
    
    Returns:
        bool: 是否成功加载
        bool: 是否有未完成的队列
    """
    if not self._project_path:
        return False, False
    
    snapshot_path = os.path.join(self._project_path, '.queue_snapshot.json')
    
    if not os.path.exists(snapshot_path):
        return True, False
    
    try:
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查快照是否过期（超过1小时视为过期）
        if time.time() - data.get('timestamp', 0) > 3600:
            logger.info("队列快照已过期，跳过加载")
            os.remove(snapshot_path)
            return True, False
        
        # 恢复队列
        for item_data in data.get('items', []):
            self.enqueue(
                node_name=item_data['node_name'],
                priority=item_data.get('priority', 0)
            )
            item = self._get_item(item_data['node_name'])
            if item:
                item.retry_count = item_data.get('retry_count', 0)
                item.dependencies = item_data.get('dependencies', [])
                item.status = QueueStatus(item_data.get('status', 'queued'))
        
        # 恢复配置
        if 'max_concurrent' in data:
            self._max_concurrent = data['max_concurrent']
        if 'max_retry' in data:
            self._max_retry = data['max_retry']
        
        # 删除快照文件（避免重复加载）
        os.remove(snapshot_path)
        
        logger.info(f"队列快照已加载，恢复 {len(data.get('items', []))} 个节点")
        return True, len(data.get('items', [])) > 0
    
    except Exception as e:
        logger.error(f"加载队列快照失败: {e}")
        return False, False
```

---

## 4. API 设计

### 4.1 公共接口

| 接口 | 描述 | 参数 | 返回 |
| :--- | :--- | :--- | :--- |
| `startup_queue.enqueue(node_name, priority, dependencies)` | 加入启动队列 | `node_name: str`, `priority: int`, `dependencies: List[str]` | `bool` |
| `startup_queue.dequeue(node_name)` | 从队列移除 | `node_name: str` | `bool` |
| `startup_queue.promote(node_name, priority)` | 提升优先级 | `node_name: str`, `priority: int` | `bool` |
| `startup_queue.clear()` | 清空队列 | - | `None` |
| `startup_queue.get_status(node_name)` | 获取节点排队状态 | `node_name: str` | `QueueStatus` |
| `startup_queue.get_queue_info()` | 获取队列整体信息 | - | `dict` |
| `startup_queue.resolve_dependencies()` | 从画布解析依赖 | - | `None` |
| `startup_queue.save_snapshot()` | 保存队列快照 | - | `bool` |
| `startup_queue.load_snapshot()` | 加载队列快照 | - | `(bool, bool)` |
| `startup_queue.is_ready(node_name)` | 检查节点是否就绪 | `node_name: str` | `(bool, List[str])` |

### 4.2 事件通知

| 事件 | 触发时机 | 参数 |
| :--- | :--- | :--- |
| `queue_updated` | 队列内容变化 | `queue_info: dict`, `blocked_info: dict` |
| `node_enqueued` | 节点入队 | `node_name: str`, `position: int`, `priority: int` |
| `node_dequeued` | 节点出队 | `node_name: str`, `status: QueueStatus` |
| `node_starting` | 节点开始启动 | `node_name: str` |
| `node_started` | 节点启动成功 | `node_name: str` |
| `node_failed` | 节点启动失败 | `node_name: str`, `error: str`, `retry_count: int` |
| `node_retry` | 节点准备重试 | `node_name: str`, `retry_count: int` |
| `node_blocked` | 节点被依赖阻塞 | `node_name: str`, `blocked_by: List[str]` |
| `queue_empty` | 队列处理完成 | - |

---

## 5. 集成方案

### 5.1 与现有启动流程集成

```python
# 修改 ui/main_window/node.py 中的 start_selected_node_by_name()

def start_selected_node_by_name(self, node_name):
    if node_name not in self.nodes_data:
        return
    
    node_info = self.nodes_data[node_name]
    
    # 已在运行或空闲状态
    if node_info['status'] in ('running', 'idle'):
        self.show_toast(t("_k_node_running").format(name=node_name), "info")
        return
    
    # 已在队列中
    if startup_queue.is_queued(node_name):
        status = startup_queue.get_status(node_name)
        if status == QueueStatus.BLOCKED:
            blocked_by = startup_queue.get_blocked_reason(node_name)
            self.show_toast(f"节点 {node_name} 已在队列中（等待: {', '.join(blocked_by)}）", "info")
        else:
            self.show_toast(f"节点 {node_name} 已在启动队列中", "info")
        return
    
    # 获取节点依赖（从画布连接关系）
    dependencies = []
    if self.canvas:
        dependencies = self.canvas.get_node_dependencies(node_name)
    
    # 加入队列
    success = startup_queue.enqueue(node_name, dependencies=dependencies)
    if success:
        # 更新 UI 显示排队状态
        self.node_list_panel.update_node_status(node_name, 'queued')
        if self.canvas:
            self.canvas.update_node_status(node_name, 'queued')
        if dependencies:
            self.show_toast(f"节点 {node_name} 已加入启动队列（等待: {', '.join(dependencies)}）", "info")
        else:
            self.show_toast(f"节点 {node_name} 已加入启动队列", "info")
    else:
        self.show_toast(f"加入队列失败", "error")
```

### 5.2 批量启动集成（智能排序）

```python
# 修改 ui/panels/node_list_ops.py 中的 batch_start_nodes()

def batch_start_nodes(self):
    selected_nodes = self.get_selected_nodes()
    if not selected_nodes:
        if self.parent_window:
            self.parent_window.show_toast("请先选中要启动的节点", "warning")
        return
    
    # 过滤掉已启动或已在队列中的节点
    to_start = [n for n in selected_nodes 
                if n in self.nodes_data 
                and self.nodes_data[n].get('status') == 'stopped'
                and not startup_queue.is_queued(n)]
    
    if not to_start:
        if self.parent_window:
            self.parent_window.show_toast("没有需要启动的节点", "info")
        return
    
    # 获取依赖关系并按拓扑排序
    if self.parent_window and hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
        sorted_nodes = self.parent_window.canvas.sort_nodes_by_dependency(to_start)
    else:
        sorted_nodes = to_start
    
    # 批量加入队列（按拓扑排序后的顺序）
    for node_name in sorted_nodes:
        # 获取该节点的依赖
        dependencies = []
        if self.parent_window and hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
            dependencies = self.parent_window.canvas.get_node_dependencies(node_name)
        
        startup_queue.enqueue(node_name, dependencies=dependencies)
    
    if self.parent_window:
        self.parent_window.show_toast(f"已将 {len(sorted_nodes)} 个节点加入启动队列", "info")
        
        # 如果存在依赖关系，提示用户
        has_dependencies = any(startup_queue.get_dependencies(n) for n in sorted_nodes)
        if has_dependencies:
            self.parent_window.show_toast("节点将按依赖顺序启动", "info")
```

### 5.3 应用启动时的队列恢复

```python
# 在 main_window 的初始化流程中添加

def _on_project_opened(self):
    """项目打开后的初始化"""
    # ... 现有代码 ...
    
    # 尝试加载队列快照
    success, has_pending = startup_queue.load_snapshot()
    
    if success and has_pending:
        # 显示恢复提示对话框
        from ui.core.utils.dialog_utils import themed_message
        reply = themed_message(
            self,
            "检测到未完成的启动队列",
            "是否继续上次未完成的节点启动？",
            "question"
        )
        
        if reply:
            # 继续启动队列
            startup_queue.start_queue()
            self.show_toast("继续启动队列中的节点...", "info")
        else:
            # 清空队列
            startup_queue.clear_queue()
            self.show_toast("已清空上次的启动队列", "info")
```

### 5.4 应用退出时的队列保存

```python
# 在 main_window 的 closeEvent 中添加

def closeEvent(self, event):
    """关闭主窗口时的清理工作"""
    # ... 现有代码 ...
    
    # 保存队列快照（如果队列中有未完成的任务）
    if startup_queue.has_pending_nodes():
        startup_queue.save_snapshot()
        logger.info("队列快照已保存，下次启动时可恢复")
    
    # ... 现有代码 ...
```

---

## 6. UI 更新

### 6.1 节点状态显示

| 状态 | 图标 | 颜色 | 显示文本 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| stopped | ○ | gray | 已停止 | 节点未启动 |
| queued | ◎ | blue | 排队中 | 等待启动 |
| blocked | ⚠ | orange | 阻塞中 | 等待依赖节点启动 |
| starting | ◐ | yellow | 启动中 | 正在启动 |
| running/idle | ● | green | 运行中/空闲 | 启动成功 |
| failed | ✗ | red | 启动失败 | 启动失败 |

### 6.2 队列管理面板

新增浮动面板 `QueueManagerPanel`，提供以下功能：
- 显示当前队列列表（按优先级+依赖顺序排序）
- 显示每个节点的依赖关系和阻塞状态
- 显示正在启动的节点
- 支持取消排队中的节点
- 支持调整优先级
- 显示队列统计信息（总数量、进行中数量、阻塞数量）
- 一键清空队列按钮
- 暂停/恢复队列调度

### 6.3 状态提示增强

当节点被阻塞时，鼠标悬停显示提示：
```
节点 B 正在等待以下节点启动：
• 节点 A (排队中)
• 节点 C (启动中)
```

---

## 7. 配置与默认值

| 配置项 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `max_concurrent` | 2 | 最大同时启动的节点数 |
| `max_retry` | 3 | 失败重试次数 |
| `retry_delay` | 5000 | 重试延迟（毫秒） |
| `batch_delay` | 300 | 批次启动间隔（毫秒），推荐 200~500 |
| `queue_timeout` | 60000 | 队列超时时间（毫秒） |
| `snapshot_ttl` | 3600 | 快照有效期（秒），超过后自动删除 |

---

## 8. 代码结构

```
ui/
├── core/
│   ├── node_startup_queue.py    # 新增：队列管理器（含依赖解析、持久化）
│   ├── node_process.py          # 修改：保持原有启动逻辑
│   └── node_control_service.py  # 修改：新增 queued/blocked 状态
├── main_window/
│   └── node.py                  # 修改：集成队列，添加快照恢复逻辑
├── panels/
│   ├── node_list_ops.py         # 修改：批量启动使用队列，支持拓扑排序
│   └── queue_manager_panel.py   # 新增：队列管理面板
└── canvas/
    └── ...                      # 修改：支持 queued/blocked 状态显示，添加依赖解析方法
```

---

## 9. 测试计划

### 9.1 单元测试

| 测试用例 | 预期结果 |
| :--- | :--- |
| 单节点入队 | 队列包含该节点，状态为 QUEUED |
| 多节点入队 | 队列按优先级排序 |
| 并发控制 | 同时启动的节点数不超过 max_concurrent |
| 优先级调度 | 高优先级节点优先启动 |
| 依赖解析 | 正确识别节点间的依赖关系 |
| 依赖阻塞 | 依赖节点未启动时，被依赖节点状态为 BLOCKED |
| 依赖就绪 | 依赖节点启动成功后，被依赖节点变为 QUEUED |
| 失败重试 | 失败节点自动重试指定次数 |
| 取消排队 | 节点从队列移除，状态为 CANCELLED |
| 队列持久化 | 退出后重启，队列状态可恢复 |
| 启动间隔 | 相邻批次间有配置的延迟 |

### 9.2 集成测试

| 测试场景 | 验证内容 |
| :--- | :--- |
| 批量启动10个节点（含依赖） | 队列按依赖顺序启动，无错误日志 |
| 启动过程中关闭应用 | 队列状态正确持久化 |
| 重启应用 | 显示恢复提示，可继续启动 |
| 依赖节点启动失败 | 被依赖节点显示阻塞状态，提示用户 |
| 网络异常场景 | 错误处理和重试机制正常工作 |
| UI 状态同步 | 队列变化正确反映到 UI |

---

## 10. 性能考虑

| 优化点 | 策略 |
| :--- | :--- |
| 队列遍历 | 使用优先级队列（heapq）提升排序效率 |
| 依赖解析 | 使用邻接表存储依赖关系，O(V+E) 复杂度 |
| 状态通知 | 使用 EventBus 批量通知，避免频繁 UI 更新 |
| 资源占用 | 限制并发数，避免资源竞争 |
| 启动延迟 | 使用 QTimer.singleShot 递归调度，给系统喘息时间 |
| 持久化 | 仅在退出时保存，避免频繁磁盘IO |

---

## 11. 向后兼容性

- 原有 `start_selected_node()` 方法保持兼容
- 新增 `queued`/`blocked` 状态不影响现有状态流转
- 配置项提供默认值，无需修改现有配置文件
- 队列持久化功能可选，不影响现有功能

---

## 12. 安全考虑

| 风险点 | 应对措施 |
| :--- | :--- |
| 队列溢出 | 限制队列最大长度，超过时拒绝入队 |
| 无限重试 | 设置最大重试次数上限 |
| 资源耗尽 | 并发数限制，超时机制 |
| 状态不一致 | 使用事件驱动保证状态同步 |
| 死锁检测 | 检测循环依赖，提前报错 |
| 快照篡改 | 使用 JSON 格式，不存储敏感信息 |

---

## 附录：深度解析

### 为什么这是一个"智能DAG调度器"

本方案的核心价值在于将简单的队列升级为**有向无环图（DAG）调度器**：

1. **依赖解析**：自动从画布连接关系提取节点依赖
2. **拓扑排序**：确保依赖节点先启动
3. **就绪检查**：实时评估每个节点的启动条件
4. **动态调整**：依赖满足后自动触发下游节点启动

这使得 BNOS 能够实现**零错误启动**的优雅体验，即使在复杂的节点连接场景下，也能保证数据流转的正确性。

### 与消息队列的对比

| 特性 | 本方案 | RabbitMQ |
| :--- | :--- | :--- |
| ACK 机制 | FAILED → QUEUED 重试闭环 | 消息确认/拒绝 |
| 优先级 | 支持 | 支持 |
| 持久化 | 本地 JSON 文件 | 磁盘持久化 |
| 消息路由 | 依赖拓扑 | Exchange/Queue |
| 适用场景 | 节点启动调度 | 分布式消息传递 |

本方案借鉴了成熟消息队列的核心思想（ACK重试、优先级），但针对节点启动场景进行了深度优化。
