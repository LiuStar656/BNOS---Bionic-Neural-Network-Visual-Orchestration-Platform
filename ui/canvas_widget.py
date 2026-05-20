"""
节点画布 - 兼容层（Facade模式）

此文件保留以维持向后兼容性，实际实现已迁移到 ui.canvas 模块。
新代码应直接导入 ui.canvas.NodeCanvas。

⚠️ 注意：此文件将在未来版本中移除
"""

# 从新模块导入所有组件，保持原有API不变
from ui.canvas import AnchorItem, NodeItem, EdgeItem, NodeCanvas

# 导出所有类，保持与原文件相同的接口
__all__ = ['AnchorItem', 'NodeItem', 'EdgeItem', 'NodeCanvas']
