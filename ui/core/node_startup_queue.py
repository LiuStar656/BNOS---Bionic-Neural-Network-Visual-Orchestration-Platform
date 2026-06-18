"""
节点启动排队系统 V2.0 - 智能调度器

核心特性：
- 并发控制：可配置同时启动的节点数量
- 优先级调度：支持设置节点启动优先级
- 状态反馈：新增 queued 状态
- 错误重试：支持失败自动重试
- 启动间隔控制：批次间平滑延迟
- 队列持久化：退出时保存队列状态，重启后恢复
"""
import os
import json
import time
import heapq
from enum import Enum
from typing import Dict, List, Optional, Callable, Tuple
from PySide6.QtCore import QObject, QThread, Signal, QTimer, Qt

from ui.core.logger import logger


class QueueStatus(Enum):
    QUEUED = "queued"
    BLOCKED = "blocked"
    STARTING = "starting"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueueItem:
    def __init__(self, node_name: str, priority: int = 0):
        self.node_name = node_name
        self.priority = priority
        self.status = QueueStatus.QUEUED
        self.retry_count = 0
        self.enqueue_time = time.time()
        self.start_time = None
        self.complete_time = None
        self.error_message = None
        self.dependencies = []
        self.blocked_by = []


class _SchedulerSignals(QObject):
    schedule_process = Signal(int)


class NodeStartupQueueManager:
    def __init__(self, max_concurrent: int = 2, max_retry: int = 3, batch_delay: int = 300, retry_delay: int = 5000):
        self._max_concurrent = max_concurrent
        self._max_retry = max_retry
        self._batch_delay = batch_delay
        self._retry_delay = retry_delay
        self._stopped = True
        self._queue: List[QueueItem] = []
        self._project_path: Optional[str] = None
        self._nodes_data: Optional[Dict] = None
        self._canvas_layout = None
        self._event_callbacks: Dict[str, List[Callable]] = {}
        self._timer = None
        self._running_workers: List[QThread] = []
        self._scheduler_signals = _SchedulerSignals()
        self._scheduler_signals.schedule_process.connect(self._schedule_next_process_slot)

    def set_project_context(self, project_path: str, nodes_data: Dict, canvas_layout = None):
        self._project_path = project_path
        self._nodes_data = nodes_data
        self._canvas_layout = canvas_layout

    def enqueue(self, node_name: str, priority: int = 0, dependencies: List[str] = None) -> bool:
        if node_name in [item.node_name for item in self._queue]:
            return False

        item = QueueItem(node_name, priority)
        self._queue.append(item)
        logger.info(f"节点已加入启动队列: {node_name} (优先级: {priority})")
        self._notify('node_enqueued', node_name=node_name, position=len(self._queue), priority=priority)

        if self._stopped:
            self.start_queue()

        return True

    def dequeue(self, node_name: str) -> bool:
        for i, item in enumerate(self._queue):
            if item.node_name == node_name:
                item.status = QueueStatus.CANCELLED
                del self._queue[i]
                logger.info(f"节点已从队列移除: {node_name}")
                self._notify('node_dequeued', node_name=node_name, status=QueueStatus.CANCELLED)
                return True
        return False

    def start_queue(self):
        if not self._stopped:
            return
        self._stopped = False
        logger.info("启动队列调度器")
        self._schedule_next_process()

    def stop_queue(self):
        self._stopped = True
        if self._timer:
            self._timer.stop()
            self._timer = None
        
        for worker in self._running_workers[:]:
            worker.quit()
            worker.wait(3000)
            self._running_workers.remove(worker)
        
        logger.info("队列调度器已停止")

    def clear_queue(self):
        for item in self._queue:
            if item.status not in (QueueStatus.SUCCESS, QueueStatus.FAILED):
                item.status = QueueStatus.CANCELLED
        self._queue = []
        self.stop_queue()
        logger.info("队列已清空")

    def get_queue_status(self) -> Dict:
        status = {
            'total': len(self._queue),
            'queued': len([i for i in self._queue if i.status == QueueStatus.QUEUED]),
            'blocked': len([i for i in self._queue if i.status == QueueStatus.BLOCKED]),
            'starting': len([i for i in self._queue if i.status == QueueStatus.STARTING]),
            'success': len([i for i in self._queue if i.status == QueueStatus.SUCCESS]),
            'failed': len([i for i in self._queue if i.status == QueueStatus.FAILED]),
        }
        return status

    def get_queued_nodes(self) -> List[str]:
        return [item.node_name for item in self._queue if item.status in (QueueStatus.QUEUED, QueueStatus.BLOCKED)]

    def is_queued(self, node_name: str) -> bool:
        return node_name in self.get_queued_nodes()

    def get_status(self, node_name: str) -> Optional[QueueStatus]:
        for item in self._queue:
            if item.node_name == node_name:
                return item.status
        return None

    def promote_node(self, node_name: str, new_priority: int) -> bool:
        for item in self._queue:
            if item.node_name == node_name:
                item.priority = new_priority
                logger.info(f"节点优先级已提升: {node_name} -> {new_priority}")
                return True
        return False

    def get_blocked_reason(self, node_name: str) -> List[str]:
        for item in self._queue:
            if item.node_name == node_name and item.status == QueueStatus.BLOCKED:
                return item.blocked_by
        return []

    def get_dependencies(self, node_name: str) -> List[str]:
        for item in self._queue:
            if item.node_name == node_name:
                return item.dependencies
        return []

    def resolve_dependencies(self):
        if not self._canvas_layout:
            return

        for item in self._queue:
            item.dependencies = []

        connections = self._canvas_layout.get_connections() if hasattr(self._canvas_layout, 'get_connections') else []
        for conn in connections:
            source_node = conn.get('source_node')
            target_node = conn.get('target_node')
            if source_node and target_node:
                for item in self._queue:
                    if item.node_name == target_node:
                        if source_node not in item.dependencies:
                            item.dependencies.append(source_node)
                            logger.debug(f"解析依赖: {target_node} 依赖 {source_node}")

    def save_snapshot(self) -> bool:
        if not self._project_path:
            return False

        try:
            snapshot_path = os.path.join(self._project_path, '.queue_snapshot.json')
            items_data = []
            for item in self._queue:
                if item.status in (QueueStatus.QUEUED, QueueStatus.BLOCKED, QueueStatus.STARTING):
                    items_data.append({
                        'node_name': item.node_name,
                        'priority': item.priority,
                        'status': item.status.value,
                        'retry_count': item.retry_count,
                        'enqueue_time': item.enqueue_time,
                        'dependencies': item.dependencies
                    })

            with open(snapshot_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'items': items_data,
                    'timestamp': time.time(),
                    'max_concurrent': self._max_concurrent,
                    'max_retry': self._max_retry
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"队列快照已保存: {snapshot_path}")
            return True
        except Exception as e:
            logger.error(f"保存队列快照失败: {e}")
            return False

    def load_snapshot(self) -> Tuple[bool, bool]:
        if not self._project_path:
            return False, False

        snapshot_path = os.path.join(self._project_path, '.queue_snapshot.json')
        if not os.path.exists(snapshot_path):
            return True, False

        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if time.time() - data.get('timestamp', 0) > 3600:
                logger.info("队列快照已过期，跳过加载")
                os.remove(snapshot_path)
                return True, False

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

            if 'max_concurrent' in data:
                self._max_concurrent = data['max_concurrent']
            if 'max_retry' in data:
                self._max_retry = data['max_retry']

            os.remove(snapshot_path)
            logger.info(f"队列快照已加载，恢复 {len(data.get('items', []))} 个节点")
            return True, len(data.get('items', [])) > 0

        except Exception as e:
            logger.error(f"加载队列快照失败: {e}")
            return False, False

    def has_pending_nodes(self) -> bool:
        return len(self.get_queued_nodes()) > 0

    def is_ready(self, node_name: str) -> Tuple[bool, List[str]]:
        item = self._get_item(node_name)
        if not item:
            return False, []
        return item.status == QueueStatus.QUEUED, []

    def on(self, event_name: str, callback: Callable):
        if event_name not in self._event_callbacks:
            self._event_callbacks[event_name] = []
        self._event_callbacks[event_name].append(callback)

    def off(self, event_name: str, callback: Callable):
        if event_name in self._event_callbacks:
            try:
                self._event_callbacks[event_name].remove(callback)
            except ValueError:
                pass

    def _notify(self, event_name: str, **kwargs):
        for cb in self._event_callbacks.get(event_name, []):
            try:
                cb(**kwargs)
            except Exception as e:
                logger.warning(f"事件回调异常: {e}")

    def _get_item(self, node_name: str) -> Optional[QueueItem]:
        for item in self._queue:
            if item.node_name == node_name:
                return item
        return None

    def _get_node_status(self, node_name: str) -> str:
        if self._nodes_data and node_name in self._nodes_data:
            return self._nodes_data[node_name].get('status', 'stopped')

        for item in self._queue:
            if item.node_name == node_name:
                return item.status.value

        return 'stopped'

    def _get_ready_nodes(self) -> List[QueueItem]:
        ready = [item for item in self._queue if item.status == QueueStatus.QUEUED]
        self._notify('queue_updated', queue_info=self.get_queue_status(), blocked_info={})
        return ready

    def _process_queue(self):
        if self._stopped:
            return

        running_count = len([item for item in self._queue if item.status == QueueStatus.STARTING])
        if running_count >= self._max_concurrent:
            self._schedule_next_process()
            return

        ready_items = self._get_ready_nodes()
        if not ready_items:
            pending_items = [item for item in self._queue if item.status in (QueueStatus.QUEUED, QueueStatus.BLOCKED)]
            if pending_items:
                self._schedule_next_process(delay=500)
                return
            else:
                logger.info("队列调度完成")
                self._stopped = True
                self._notify('queue_empty')
                return

        ready_items.sort(key=lambda x: (-x.priority, x.enqueue_time))
        next_item = ready_items[0]
        self._start_node(next_item)

        self._schedule_next_process()

    def _schedule_next_process(self, delay=None):
        if delay is None:
            delay = self._batch_delay
        
        self._scheduler_signals.schedule_process.emit(delay)

    def _schedule_next_process_slot(self, delay):
        QTimer.singleShot(delay, self._process_queue)

    def _start_node(self, item):
        item.status = QueueStatus.STARTING
        item.start_time = time.time()
        self._notify('node_starting', node_name=item.node_name)

        worker = NodeStartWorker(item, self._nodes_data)
        worker.finished.connect(lambda success, err: self._on_node_start_complete(item, success, err))
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.start()
        self._running_workers.append(worker)

    def _on_worker_finished(self, worker):
        if worker in self._running_workers:
            self._running_workers.remove(worker)

    def _on_node_start_complete(self, item, success, error):
        if success:
            item.status = QueueStatus.SUCCESS
            item.complete_time = time.time()
            logger.info(f"节点启动成功: {item.node_name}")
            self._notify('node_started', node_name=item.node_name)
            self._schedule_next_process(delay=100)
        else:
            item.error_message = error
            item.retry_count += 1

            if item.retry_count < self._max_retry:
                item.status = QueueStatus.QUEUED
                logger.warning(f"节点启动失败，将重试 ({item.retry_count}/{self._max_retry}): {item.node_name}")
                self._notify('node_retry', node_name=item.node_name, retry_count=item.retry_count)
                self._schedule_next_process(delay=self._retry_delay)
            else:
                item.status = QueueStatus.FAILED
                logger.error(f"节点启动失败（已达最大重试次数）: {item.node_name} - {error}")
                self._notify('node_failed', node_name=item.node_name, error=error)

            self._schedule_next_process()

    def _handle_dependency_failure(self, failed_node):
        pass


class NodeStartWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, item: QueueItem, nodes_data: Dict, parent=None):
        super().__init__(parent)
        self._item = item
        self._nodes_data = nodes_data

    def run(self):
        from ui.core.node_process import start_node_process

        node_name = self._item.node_name
        if node_name not in self._nodes_data:
            self.finished.emit(False, f"节点不存在: {node_name}")
            return

        node_info = self._nodes_data[node_name]
        success, err = start_node_process(node_info)
        self.finished.emit(success, err)


startup_queue = NodeStartupQueueManager()
