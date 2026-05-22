"""
节点组管理器 - 负责节点分组的创建、管理和持久化
遵循非侵入式原则，独立于原有代码
"""
import json
import os
from typing import Dict, List, Optional, Set
from ui.core.logger import logger
from ui.core.i18n import t


class NodeGroupManager:
    """节点组管理器 - 管理节点分组信息
    
    功能：
    1. 创建/删除/重命名节点组
    2. 添加/移除节点到组
    3. 获取组内节点列表
    4. 配置持久化（跟随项目）
    """
    
    def __init__(self, project_path: str = None):
        """初始化节点组管理器
        
        Args:
            project_path: 项目路径，用于保存/加载配置文件
        """
        self.project_path = project_path
        self.groups: Dict[str, dict] = {}  # {group_name: {"nodes": [], "color": "#..."}}
        self.node_to_group: Dict[str, str] = {}  # {node_name: group_name}
        self._locked_groups: Set[str] = set()  # 锁定组集合（节点无法移入/移出）
        
        # 如果提供了项目路径，立即加载配置
        if project_path:
            self.load_groups(project_path)
    
    def set_project_path(self, project_path: str):
        """设置项目路径并加载配置
        
        Args:
            project_path: 项目根目录路径
        """
        self.project_path = project_path
        self.load_groups(project_path)
    
    def get_config_file_path(self) -> str:
        """获取配置文件路径
        
        Returns:
            配置文件完整路径
        """
        if not self.project_path:
            return ""
        return os.path.join(self.project_path, "node_groups.json")
    
    def load_groups(self, project_path: str = None):
        """从配置文件加载节点组信息
        
        Args:
            project_path: 项目路径（可选，如果未提供则使用已设置的路径）
        """
        path = project_path or self.project_path
        if not path:
            logger.warning(t("k_group_config_load_fail"))
            return
        
        config_file = os.path.join(path, "node_groups.json")
        
        if not os.path.exists(config_file):
            logger.info("未找到节点组配置文件: %s", config_file)
            self.groups.clear()
            self.node_to_group.clear()
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.groups = data.get('groups', {})
            self.node_to_group = data.get('node_to_group', {})
            # 加载锁定组列表
            locked_data = data.get('locked_groups', [])
            self._locked_groups = set(locked_data) if isinstance(locked_data, list) else set()
            
            logger.info("已加载 %d 个节点组", len(self.groups))
            
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("加载节点组配置失败: %s", e)
            # 备份损坏的文件
            try:
                import shutil
                backup_file = config_file + ".bak"
                shutil.copy2(config_file, backup_file)
                logger.info("已备份损坏的配置文件: %s", backup_file)
            except:
                pass
            
            self.groups.clear()
            self.node_to_group.clear()
    
    def save_groups(self):
        """保存节点组信息到配置文件"""
        if not self.project_path:
            logger.warning(t("k_group_config_save_fail"))
            return False
        
        config_file = self.get_config_file_path()
        
        try:
            data = {
                'groups': self.groups,
                'node_to_group': self.node_to_group,
                'locked_groups': list(self._locked_groups)
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info("节点组配置已保存到: %s", config_file)
            return True
            
        except Exception as e:
            logger.error("保存节点组配置失败: %s", e)
            return False
    
    def create_group(self, group_name: str, color: str = "#4A90E2") -> bool:
        """创建新的节点组
        
        Args:
            group_name: 组名称
            color: 组颜色（十六进制）
            
        Returns:
            是否创建成功
        """
        if not group_name or group_name in self.groups:
            return False
        
        self.groups[group_name] = {
            'nodes': [],
            'color': color
        }
        
        self.save_groups()
        logger.info("创建节点组: %s", group_name)
        return True
    
    def delete_group(self, group_name: str) -> bool:
        if group_name not in self.groups:
            return False
        for node_name in self.groups[group_name]['nodes']:
            if node_name in self.node_to_group:
                del self.node_to_group[node_name]
        del self.groups[group_name]
        self.save_groups()
        logger.info("删除节点组: %s", group_name)
        return True
    
    def rename_group(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.groups or new_name in self.groups:
            return False
        self.groups[new_name] = self.groups[old_name]
        del self.groups[old_name]
        for node_name in self.groups[new_name]['nodes']:
            if node_name in self.node_to_group:
                self.node_to_group[node_name] = new_name
        self.save_groups()
        logger.info("重命名节点组: %s -> %s", old_name, new_name)
        return True
    
    def add_nodes_to_group(self, group_name: str, node_names: List[str]) -> bool:
        """批量添加节点到组
        
        Args:
            group_name: 组名称
            node_names: 节点名称列表
            
        Returns:
            是否添加成功
        """
        if group_name not in self.groups:
            return False
        
        added_count = 0
        for node_name in node_names:
            # 如果节点已在其他组，先移除
            if node_name in self.node_to_group:
                old_group = self.node_to_group[node_name]
                if old_group != group_name and old_group in self.groups:
                    if node_name in self.groups[old_group]['nodes']:
                        self.groups[old_group]['nodes'].remove(node_name)
            
            # 添加到新组（避免重复）
            if node_name not in self.groups[group_name]['nodes']:
                self.groups[group_name]['nodes'].append(node_name)
                self.node_to_group[node_name] = group_name
                added_count += 1
        
        if added_count > 0:
            self.save_groups()
            logger.info("添加 %d 个节点到组: %s", added_count, group_name)
        
        return added_count > 0
    
    def remove_nodes_from_group(self, group_name: str, node_names: List[str]) -> bool:
        """从组中移除节点
        
        Args:
            group_name: 组名称
            node_names: 节点名称列表
            
        Returns:
            是否移除成功
        """
        if group_name not in self.groups:
            return False
        
        removed_count = 0
        for node_name in node_names:
            if node_name in self.groups[group_name]['nodes']:
                self.groups[group_name]['nodes'].remove(node_name)
                removed_count += 1
            
            # 清除节点归属
            if node_name in self.node_to_group:
                del self.node_to_group[node_name]
        
        if removed_count > 0:
            self.save_groups()
            logger.info("从组 %s 移除 %d 个节点", group_name, removed_count)
        
        return removed_count > 0
    
    def get_group_nodes(self, group_name: str) -> List[str]:
        """获取组内所有节点
        
        Args:
            group_name: 组名称
            
        Returns:
            节点名称列表
        """
        if group_name not in self.groups:
            return []
        return self.groups[group_name]['nodes'].copy()
    
    def get_node_group(self, node_name: str) -> Optional[str]:
        """获取节点所属的组
        
        Args:
            node_name: 节点名称
            
        Returns:
            组名称，如果节点不属于任何组则返回None
        """
        return self.node_to_group.get(node_name)
    
    def get_all_groups(self) -> Dict[str, dict]:
        """获取所有节点组
        
        Returns:
            所有组的字典
        """
        return self.groups.copy()
    
    def get_ungrouped_nodes(self, all_nodes: List[str]) -> List[str]:
        """获取未分组的节点
        
        Args:
            all_nodes: 所有节点名称列表
            
        Returns:
            未分组的节点列表
        """
        grouped_nodes = set(self.node_to_group.keys())
        return [node for node in all_nodes if node not in grouped_nodes]
    
    def clear_all_groups(self):
        """清空所有分组（不删除节点）"""
        self.groups.clear()
        self.node_to_group.clear()
        self._locked_groups.clear()
        self.save_groups()
        logger.info(t("k_group_cleared_all"))

    # ---- 锁定组管理（用于外部挂载节点）----
    def lock_group(self, group_name: str) -> bool:
        """锁定组，禁止节点移入和移出
        
        Args:
            group_name: 组名称
            
        Returns:
            是否锁定成功
        """
        if group_name not in self.groups:
            return False
        if group_name not in self._locked_groups:
            self._locked_groups.add(group_name)
            self.save_groups()
            logger.info("已锁定节点组: %s", group_name)
        return True

    def unlock_group(self, group_name: str) -> bool:
        """解锁组
        
        Args:
            group_name: 组名称
            
        Returns:
            是否解锁成功
        """
        if group_name in self._locked_groups:
            self._locked_groups.discard(group_name)
            self.save_groups()
            logger.info("已解锁节点组: %s", group_name)
            return True
        return False

    def is_group_locked(self, group_name: str) -> bool:
        """检查组是否被锁定
        
        Args:
            group_name: 组名称
            
        Returns:
            是否被锁定
        """
        return group_name in self._locked_groups

    def get_locked_groups(self) -> Set[str]:
        """获取所有锁定组名称"""
        return self._locked_groups.copy()
