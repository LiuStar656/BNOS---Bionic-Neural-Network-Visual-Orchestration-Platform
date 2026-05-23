"""
多画布上下文隔离 - 管理每个画布的独立状态
"""
import os
import json
from ui.core.logger import logger


class TabContext:
    """单个标签页的上下文"""
    
    def __init__(self, project_path=None):
        self.project_path = project_path
        self.nodes_data = {}
        self.process_manager = None
        self.layout_data = {}
        self.color_settings = {}
        
        # 加载项目数据
        if project_path:
            self._load_project_data()
    
    def _load_project_data(self):
        """加载项目数据"""
        if not self.project_path:
            return
        
        # 加载节点数据
        nodes_file = os.path.join(self.project_path, 'nodes.json')
        if os.path.exists(nodes_file):
            try:
                with open(nodes_file, 'r', encoding='utf-8') as f:
                    self.nodes_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load nodes.json: {e}")
        
        # 加载颜色设置
        color_file = os.path.join(self.project_path, 'color_settings.json')
        if os.path.exists(color_file):
            try:
                with open(color_file, 'r', encoding='utf-8') as f:
                    self.color_settings = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load color_settings.json: {e}")
    
    def save_project_data(self):
        """保存项目数据"""
        if not self.project_path:
            return
        
        # 保存节点数据
        nodes_file = os.path.join(self.project_path, 'nodes.json')
        try:
            with open(nodes_file, 'w', encoding='utf-8') as f:
                json.dump(self.nodes_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save nodes.json: {e}")
        
        # 保存颜色设置
        color_file = os.path.join(self.project_path, 'color_settings.json')
        try:
            with open(color_file, 'w', encoding='utf-8') as f:
                json.dump(self.color_settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save color_settings.json: {e}")
    
    def update_node_status(self, node_name, status):
        """更新节点状态"""
        if node_name in self.nodes_data:
            self.nodes_data[node_name]['status'] = status
    
    def get_node_status(self, node_name):
        """获取节点状态"""
        return self.nodes_data.get(node_name, {}).get('status', 'stopped')


class TabContextManager:
    """多标签页上下文管理器"""
    
    def __init__(self):
        self._contexts = {}  # tab_index -> TabContext
        self._current_index = -1
    
    def add_context(self, index, project_path=None):
        """添加上下文"""
        self._contexts[index] = TabContext(project_path)
    
    def remove_context(self, index):
        """移除上下文"""
        if index in self._contexts:
            # 保存数据
            self._contexts[index].save_project_data()
            del self._contexts[index]
        
        # 更新索引
        new_contexts = {}
        for old_idx, context in self._contexts.items():
            if old_idx < index:
                new_contexts[old_idx] = context
            elif old_idx > index:
                new_contexts[old_idx - 1] = context
        self._contexts = new_contexts
        
        if self._current_index >= index and self._current_index > 0:
            self._current_index -= 1
    
    def set_current_index(self, index):
        """设置当前上下文索引"""
        # 保存当前上下文数据
        if self._current_index >= 0 and self._current_index in self._contexts:
            self._contexts[self._current_index].save_project_data()
        
        self._current_index = index
    
    def get_current_context(self):
        """获取当前上下文"""
        if self._current_index >= 0 and self._current_index in self._contexts:
            return self._contexts[self._current_index]
        return None
    
    def get_context(self, index):
        """获取指定索引的上下文"""
        return self._contexts.get(index)
    
    def get_all_contexts(self):
        """获取所有上下文"""
        return list(self._contexts.values())
    
    def update_current_node_status(self, node_name, status):
        """更新当前上下文的节点状态"""
        context = self.get_current_context()
        if context:
            context.update_node_status(node_name, status)
    
    def save_all_contexts(self):
        """保存所有上下文数据"""
        for context in self._contexts.values():
            context.save_project_data()