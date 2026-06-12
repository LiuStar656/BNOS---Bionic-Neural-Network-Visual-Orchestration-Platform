"""
验证器模块 - 提供节点名称、路径和配置值的验证功能

用法:
    from ui.core.validators import NodeNameValidator
    
    valid, message = NodeNameValidator.validate("my_node")
    if not valid:
        print(message)
"""
import re
import os


class NodeNameValidator:
    """节点名称验证器"""
    
    MAX_LENGTH = 64
    ALLOWED_CHARS = r'^[A-Za-z0-9_\u4e00-\u9fa5]+$'
    
    @staticmethod
    def validate(name):
        """验证节点名称是否合法
        
        Args:
            name: 节点名称
            
        Returns:
            tuple: (valid: bool, message: str)
        """
        if not name:
            return False, "节点名称不能为空"
        
        if len(name) > NodeNameValidator.MAX_LENGTH:
            return False, f"节点名称不能超过 {NodeNameValidator.MAX_LENGTH} 个字符"
        
        if not re.match(NodeNameValidator.ALLOWED_CHARS, name):
            return False, "节点名称只能包含字母、数字、下划线和中文"
        
        if any(c in name for c in ('/', '\\', ':', '*', '?', '"', '<', '>', '|')):
            return False, "节点名称不能包含特殊字符"
        
        return True, ""
    
    @staticmethod
    def sanitize(name):
        """清理节点名称，移除非法字符
        
        Args:
            name: 原始节点名称
            
        Returns:
            str: 清理后的名称
        """
        if not name:
            return ""
        
        # 移除非法字符
        cleaned = re.sub(r'[/\\:*?"<>|]', '', name)
        
        # 截断过长名称
        if len(cleaned) > NodeNameValidator.MAX_LENGTH:
            cleaned = cleaned[:NodeNameValidator.MAX_LENGTH]
        
        return cleaned


class PathValidator:
    """路径验证器"""
    
    @staticmethod
    def validate_path(path):
        """验证路径是否合法
        
        Args:
            path: 文件或目录路径
            
        Returns:
            tuple: (valid: bool, message: str)
        """
        if not path:
            return False, "路径不能为空"
        
        # 检查路径穿越
        normalized = os.path.normpath(path)
        if '..' in normalized.split(os.sep):
            return False, "路径不能包含父目录引用"
        
        return True, ""
    
    @staticmethod
    def is_within_directory(path, parent_dir):
        """检查路径是否在指定目录内
        
        Args:
            path: 要检查的路径
            parent_dir: 父目录
            
        Returns:
            bool: 是否在父目录内
        """
        import os
        abs_path = os.path.abspath(path)
        abs_parent = os.path.abspath(parent_dir)
        
        # 确保路径以父目录开头
        return abs_path.startswith(abs_parent + os.sep) or abs_path == abs_parent


class ConfigValueValidator:
    """配置值验证器"""
    
    @staticmethod
    def validate_int(value, min_val=None, max_val=None):
        """验证整数值
        
        Args:
            value: 要验证的值
            min_val: 最小值（可选）
            max_val: 最大值（可选）
            
        Returns:
            tuple: (valid: bool, message: str)
        """
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                return False, f"值不能小于 {min_val}"
            
            if max_val is not None and int_val > max_val:
                return False, f"值不能大于 {max_val}"
            
            return True, ""
            
        except ValueError:
            return False, "值必须是整数"
    
    @staticmethod
    def validate_float(value, min_val=None, max_val=None):
        """验证浮点数值
        
        Args:
            value: 要验证的值
            min_val: 最小值（可选）
            max_val: 最大值（可选）
            
        Returns:
            tuple: (valid: bool, message: str)
        """
        try:
            float_val = float(value)
            
            if min_val is not None and float_val < min_val:
                return False, f"值不能小于 {min_val}"
            
            if max_val is not None and float_val > max_val:
                return False, f"值不能大于 {max_val}"
            
            return True, ""
            
        except ValueError:
            return False, "值必须是数字"
    
    @staticmethod
    def validate_string(value, min_length=0, max_length=None):
        """验证字符串值
        
        Args:
            value: 要验证的字符串
            min_length: 最小长度（可选，默认0）
            max_length: 最大长度（可选）
            
        Returns:
            tuple: (valid: bool, message: str)
        """
        if not isinstance(value, str):
            return False, "值必须是字符串"
        
        if len(value) < min_length:
            return False, f"字符串长度不能小于 {min_length}"
        
        if max_length is not None and len(value) > max_length:
            return False, f"字符串长度不能大于 {max_length}"
        
        return True, ""
