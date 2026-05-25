"""
JSON 节点启动器 - 从 JSON 配置文件读取节点信息并启动节点

功能：
1. 读取 JSON 配置文件（支持单个节点和节点数组）
2. 验证配置格式
3. 调用现有启动机制启动节点
4. 提供详细的错误处理和状态反馈
5. 支持批量启动

配置文件格式：
{
  "nodes": [
    {
      "name": "node_name",
      "path": "/path/to/node",
      "config": { ... }
    }
  ]
}

或单个节点：
{
  "name": "node_name",
  "path": "/path/to/node"
}
"""
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from ui.core.logger import logger
from ui.core.node_process import start_node_process, detect_running_nodes


class JsonNodeStarter:
    """从 JSON 配置读取并启动节点的组件"""
    
    def __init__(self):
        self._loaded_configs: Dict[str, dict] = {}  # 已加载的配置缓存
    
    def load_config(self, config_path: str) -> Tuple[bool, str, Optional[List[dict]]]:
        """
        加载 JSON 配置文件
        
        Args:
            config_path: JSON 配置文件路径
            
        Returns:
            (success: bool, message: str, nodes: Optional[List[dict]])
        """
        if not os.path.exists(config_path):
            return False, f"配置文件不存在: {config_path}", None
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 解析节点配置
            nodes = self._parse_nodes_from_config(data, config_path)
            
            if not nodes:
                return False, "配置文件中未找到有效的节点配置", None
                
            # 验证节点配置
            valid_nodes = []
            for node in nodes:
                is_valid, msg = self._validate_node_config(node)
                if is_valid:
                    valid_nodes.append(node)
                else:
                    logger.warning(f"节点配置验证失败: {node.get('name', '未知')} - {msg}")
            
            if not valid_nodes:
                return False, "没有有效的节点配置", None
                
            # 缓存配置
            self._loaded_configs[config_path] = valid_nodes
            return True, f"成功加载 {len(valid_nodes)} 个节点配置", valid_nodes
            
        except json.JSONDecodeError as e:
            return False, f"JSON 解析错误: {str(e)}", None
        except Exception as e:
            return False, f"加载配置失败: {str(e)}", None
    
    def _parse_nodes_from_config(self, data: dict, config_path: str) -> List[dict]:
        """从配置数据中解析节点列表"""
        nodes = []
        
        # 支持数组格式: {"nodes": [...]}
        if 'nodes' in data and isinstance(data['nodes'], list):
            for idx, node_data in enumerate(data['nodes']):
                if isinstance(node_data, dict):
                    node = self._normalize_node_config(node_data, config_path)
                    if node:
                        nodes.append(node)
                    else:
                        logger.warning(f"第 {idx+1} 个节点配置无效")
        
        # 支持单个节点格式
        elif 'name' in data or 'path' in data:
            node = self._normalize_node_config(data, config_path)
            if node:
                nodes.append(node)
        
        return nodes
    
    def _normalize_node_config(self, node_data: dict, config_path: str) -> Optional[dict]:
        """规范化节点配置，处理相对路径"""
        if not isinstance(node_data, dict):
            return None
            
        name = node_data.get('name')
        path = node_data.get('path')
        
        if not name:
            # 如果没有名称，从路径提取
            if path:
                name = os.path.basename(path.strip('/\\'))
            else:
                return None
                
        if path:
            # 处理相对路径（相对于配置文件所在目录）
            if not os.path.isabs(path):
                config_dir = os.path.dirname(os.path.abspath(config_path))
                path = os.path.normpath(os.path.join(config_dir, path))
            path = os.path.abspath(path)
        
        config = node_data.get('config', {})
        
        return {
            'name': name,
            'path': path,
            'config': config,
            'status': 'stopped',
            'process': None
        }
    
    def _validate_node_config(self, node: dict) -> Tuple[bool, str]:
        """验证节点配置的有效性"""
        if not node.get('name'):
            return False, "节点名称不能为空"
            
        path = node.get('path')
        if not path:
            return False, "节点路径不能为空"
            
        if not os.path.exists(path):
            return False, f"节点路径不存在: {path}"
            
        # 检查必要文件
        listener_py = os.path.join(path, "listener.py")
        if not os.path.exists(listener_py):
            return False, f"listener.py 不存在: {listener_py}"
            
        config_json = os.path.join(path, "config.json")
        if not os.path.exists(config_json):
            logger.warning(f"节点 {node['name']} 缺少 config.json")
            
        return True, "验证通过"
    
    def start_node(self, node_info: dict) -> Tuple[bool, str]:
        """
        启动单个节点
        
        Args:
            node_info: 节点信息字典（包含 name, path, config 等）
            
        Returns:
            (success: bool, message: str)
        """
        try:
            # 确保 node_info 有必要的字段
            if 'status' not in node_info:
                node_info['status'] = 'stopped'
            if 'process' not in node_info:
                node_info['process'] = None
                
            # 调用现有启动机制
            success, error_msg = start_node_process(node_info)
            
            if success:
                logger.info(f"节点启动成功: {node_info['name']}")
                return True, f"节点 {node_info['name']} 启动成功"
            else:
                logger.error(f"节点启动失败: {node_info['name']} - {error_msg}")
                return False, f"节点 {node_info['name']} 启动失败: {error_msg}"
                
        except Exception as e:
            logger.error(f"启动节点异常: {node_info.get('name', '未知')} - {str(e)}")
            return False, f"启动节点异常: {str(e)}"
    
    def start_nodes_from_config(self, config_path: str) -> Tuple[Dict[str, bool], str]:
        """
        从配置文件启动所有节点
        
        Args:
            config_path: JSON 配置文件路径
            
        Returns:
            (results: Dict[node_name -> success], summary: str)
        """
        # 先加载配置
        load_success, load_msg, nodes = self.load_config(config_path)
        if not load_success:
            return {}, f"加载配置失败: {load_msg}"
            
        assert nodes is not None
        
        results = {}
        success_count = 0
        fail_count = 0
        failed_nodes = []
        
        # 逐个启动节点
        for node in nodes:
            success, msg = self.start_node(node)
            results[node['name']] = success
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                failed_nodes.append(node['name'])
                logger.warning(f"启动失败: {node['name']}")
        
        # 生成摘要
        summary = f"批量启动完成: 成功 {success_count} 个, 失败 {fail_count} 个"
        if failed_nodes:
            summary += f"\n失败节点: {', '.join(failed_nodes)}"
            
        logger.info(summary)
        return results, summary
    
    def start_nodes(self, nodes: List[dict]) -> Tuple[Dict[str, bool], str]:
        """
        启动多个节点
        
        Args:
            nodes: 节点信息列表
            
        Returns:
            (results: Dict[node_name -> success], summary: str)
        """
        results = {}
        success_count = 0
        fail_count = 0
        failed_nodes = []
        
        for node in nodes:
            success, msg = self.start_node(node)
            results[node['name']] = success
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                failed_nodes.append(node['name'])
        
        summary = f"批量启动完成: 成功 {success_count} 个, 失败 {fail_count} 个"
        if failed_nodes:
            summary += f"\n失败节点: {', '.join(failed_nodes)}"
            
        return results, summary
    
    def detect_running_from_config(self, config_path: str) -> List[str]:
        """
        检测配置文件中已在运行的节点
        
        Args:
            config_path: JSON 配置文件路径
            
        Returns:
            正在运行的节点名称列表
        """
        load_success, _, nodes = self.load_config(config_path)
        if not load_success or not nodes:
            return []
            
        # 构建 nodes_data 格式
        nodes_data = {node['name']: node for node in nodes}
        
        # 调用检测函数
        detected = detect_running_nodes(nodes_data)
        
        return [name for name, pid in detected]
    
    def get_loaded_configs(self) -> Dict[str, List[dict]]:
        """获取已加载的所有配置"""
        return self._loaded_configs
    
    def clear_cache(self):
        """清除配置缓存"""
        self._loaded_configs.clear()


# 全局便捷实例
json_node_starter = JsonNodeStarter()


# 便捷函数
def load_and_start_nodes(config_path: str) -> Tuple[Dict[str, bool], str]:
    """
    便捷函数：加载配置并启动所有节点
    
    Args:
        config_path: JSON 配置文件路径
        
    Returns:
        (results: Dict[node_name -> success], summary: str)
    """
    return json_node_starter.start_nodes_from_config(config_path)


def start_node_from_json(node_json: str) -> Tuple[bool, str]:
    """
    从 JSON 字符串启动单个节点
    
    Args:
        node_json: 节点配置的 JSON 字符串
        
    Returns:
        (success: bool, message: str)
    """
    try:
        node_data = json.loads(node_json)
        return json_node_starter.start_node(node_data)
    except json.JSONDecodeError as e:
        return False, f"JSON 解析错误: {str(e)}"