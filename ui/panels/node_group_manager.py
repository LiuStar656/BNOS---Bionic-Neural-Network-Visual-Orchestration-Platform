"""
节点组管理器 - 负责节点分组的创建、管理和持久化
遵循非侵入式原则，独立于原有代码
"""
import json
import os
from typing import Dict, List, Optional


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
            print("⚠️  未设置项目路径，无法加载节点组配置")
            return
        
        config_file = os.path.join(path, "node_groups.json")
        
        if not os.path.exists(config_file):
            print(f"ℹ️  未找到节点组配置文件: {config_file}")
            self.groups.clear()
            self.node_to_group.clear()
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.groups = data.get('groups', {})
            self.node_to_group = data.get('node_to_group', {})
            
            print(f"✅ 已加载 {len(self.groups)} 个节点组")
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  加载节点组配置失败: {e}")
            # 备份损坏的文件
            try:
                import shutil
                backup_file = config_file + ".bak"
                shutil.copy2(config_file, backup_file)
                print(f"📦 已备份损坏的配置文件: {backup_file}")
            except:
                pass
            
            self.groups.clear()
            self.node_to_group.clear()
    
    def save_groups(self):
        """保存节点组信息到配置文件"""
        if not self.project_path:
            print("⚠️  未设置项目路径，无法保存节点组配置")
            return False
        
        config_file = self.get_config_file_path()
        
        try:
            data = {
                'groups': self.groups,
                'node_to_group': self.node_to_group
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 节点组配置已保存到: {config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存节点组配置失败: {e}")
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
        print(f"✅ 创建节点组: {group_name}")
        return True
    
    def delete_group(self, group_name: str) -> bool:
        """删除节点组（不删除组内节点）
        
        Args:
            group_name: 组名称
            
        Returns:
            是否删除成功
        """
        if group_name not in self.groups:
            return False
        
        # 清除组内节点的组归属
        for node_name in self.groups[group_name]['nodes']:
            if node_name in self.node_to_group:
                del self.node_to_group[node_name]
        
        # 删除组
        del self.groups[group_name]
        
        self.save_groups()
        print(f"✅ 删除节点组: {group_name}")
        return True
    
    def rename_group(self, old_name: str, new_name: str) -> bool:
        """重命名节点组
        
        Args:
            old_name: 原组名
            new_name: 新组名
            
        Returns:
            是否重命名成功
        """
        if old_name not in self.groups or new_name in self.groups:
            return False
        
        # 复制组数据
        self.groups[new_name] = self.groups[old_name]
        del self.groups[old_name]
        
        # 更新节点归属
        for node_name in self.groups[new_name]['nodes']:
            if node_name in self.node_to_group:
                self.node_to_group[node_name] = new_name
        
        self.save_groups()
        print(f"✅ 重命名节点组: {old_name} -> {new_name}")
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
            print(f"✅ 添加 {added_count} 个节点到组: {group_name}")
        
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
            print(f"✅ 从组 {group_name} 移除 {removed_count} 个节点")
        
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
        self.save_groups()
        print("✅ 已清空所有节点组")
