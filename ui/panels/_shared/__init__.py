"""
面板共享模块 — 消除 NodeMonitor / ResourceMonitor / NodeList 双面板之间的重复代码

提供:
  - SystemResourceCollector: 系统+节点资源数据采集（纯数据层，不涉及 UI）
  - BaseNodeLogSubPanel: 节点日志子面板共享基类
  - NodePanelSyncMixin: NodeMonitor 面板节点同步逻辑 Mixin
"""
