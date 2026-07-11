"""
项目加载 Worker — 把磁盘扫描/JSON 解析等耗时操作放到 QThread，避免阻塞 GUI

设计原则：
  • Worker 内只做纯数据操作，**绝不触碰任何 UI 对象**（main_window、QGraphicsScene、QTreeWidget 等）
  • 数据通过 signal 在 run() 结束后传回主线程，由主线程更新 UI
  • progress 信号每处理 ~5 个节点 emit 一次，避免信号风暴
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ui.core.logger import logger
from ui.core.node.node_process import detect_running_nodes
from ui.core.node.node_registry import NodeRegistry


class ProjectLoadWorker(QThread):
    """项目加载 Worker

    Signals:
        progress(int, str): 进度（0-100），当前操作描述
        finished(dict, list, list): 成功 → (nodes_data, mounted_nodes, running_nodes)
        failed(str): 失败 → 错误信息
    """

    progress = Signal(int, str)
    finished = Signal(dict, list, list)
    failed = Signal(str)

    def __init__(self, project_path, parent=None):
        super().__init__(parent)
        self._project_path = Path(project_path).resolve()
        self._nodes_dir = self._project_path / "nodes"

    # ---- 主入口 ----
    def run(self):
        nodes_data = {}
        mounted_nodes = []
        running_nodes = []
        try:
            # 1) 节点目录扫描
            self.progress.emit(5, "扫描节点目录")
            if not self._nodes_dir.is_dir():
                logger.debug("nodes 目录不存在，创建: %s", self._nodes_dir)
                self._nodes_dir.mkdir(parents=True, exist_ok=True)

            # 2) 逐个节点读取 config.json
            dir_items = sorted(self._nodes_dir.iterdir())
            total = len(dir_items)
            self.progress.emit(10, f"发现 {total} 个文件夹，加载节点配置")

            for idx, item in enumerate(dir_items):
                node_path = item.resolve()

                if not node_path.is_dir():
                    continue

                config_path = node_path / "config.json"
                if not config_path.is_file():
                    logger.info("跳过非节点目录（无 config.json）: %s", item.name)
                    continue

                try:
                    config = json.loads(config_path.read_text(encoding="utf-8"))
                    node_name = config.get("node_name", item.name)

                    expected_path = (self._nodes_dir / item.name).resolve()
                    if node_path != expected_path:
                        logger.warning("节点 '%s' 路径不一致: 期望=%s, 实际=%s", item.name, expected_path, node_path)
                        node_path = expected_path

                    nodes_data[node_name] = {
                        "config": config,
                        "path": str(node_path),
                        "process": None,
                        "status": "stopped",
                    }
                    logger.info("加载节点: %s (文件夹=%s)", node_name, item.name)
                except Exception as e:
                    logger.error("加载节点 %s 失败: %s", item.name, e)

                # 每 5 个节点 emit 一次进度（0 - 70 区间）
                if idx % 5 == 0:
                    pct = 10 + int((idx / max(total, 1)) * 60)
                    self.progress.emit(pct, f"已加载 {idx}/{total} 个节点")

            self.progress.emit(72, f"共加载 {len(nodes_data)} 个节点")

            # 3) 同步节点注册表（纯数据操作）
            self.progress.emit(75, "同步节点注册表")
            try:
                registry = NodeRegistry(str(self._project_path))
                registry.load()
                scan_result = {name: info["path"] for name, info in nodes_data.items()}
                registry.sync_from_scan(scan_result)
                registry.save()
                logger.info(
                    "节点注册表已同步: active=%d, missing=%d, total=%d",
                    registry.active_count,
                    registry.missing_count,
                    registry.node_count,
                )

                mounted = registry.get_mounted_nodes()
                for m_name, m_info in mounted.items():
                    if m_name not in nodes_data and m_info.get("status") == "active":
                        m_path = m_info.get("path", "")
                        m_config_path = Path(m_path) / "config.json"
                        m_mount_root = m_info.get("mount_root", "")
                        try:
                            if m_config_path.exists():
                                m_config = json.loads(m_config_path.read_text(encoding="utf-8"))
                            else:
                                m_config = {"node_name": m_name}
                            nodes_data[m_name] = {
                                "config": m_config,
                                "path": m_path,
                                "process": None,
                                "status": "stopped",
                                "mounted": True,
                                "mount_root": m_mount_root,
                            }
                            mounted_nodes.append(
                                {
                                    "name": m_name,
                                    "mount_root": m_mount_root,
                                }
                            )
                            logger.info("恢复挂载节点: %s (mount_root=%s)", m_name, m_mount_root)
                        except Exception as ex:
                            logger.warning("恢复挂载节点 %s 失败: %s", m_name, ex)
            except Exception as e:
                logger.warning("节点注册表同步失败: %s", e)

            # 4) 检测后台运行节点
            self.progress.emit(88, "检测后台运行节点")
            running_nodes = list(detect_running_nodes(nodes_data))

            self.progress.emit(100, "加载完成")
            logger.info("项目加载完成，共 %d 个节点, %d 个后台运行", len(nodes_data), len(running_nodes))

            self.finished.emit(nodes_data, mounted_nodes, running_nodes)

        except Exception as e:
            import traceback

            traceback.print_exc()
            self.failed.emit(str(e))
