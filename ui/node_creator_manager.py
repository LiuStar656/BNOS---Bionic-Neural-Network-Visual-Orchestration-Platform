"""
BNOS 节点创建管理器 - 统一管理多语言节点创建

非侵入式设计：
- 独立模块，不修改原有代码
- 通过注册机制动态加载各语言创建器
- 提供统一的调用接口
- 支持扩展新的语言类型

使用示例:
    from ui.node_creator_manager import NodeCreatorManager
    
    # 初始化（在 MainWindow.__init__ 中调用一次）
    creator = NodeCreatorManager.get_instance()
    
    # 创建 Python 节点
    creator.create_node("python", "my_python_node")
    
    # 创建 Rust 节点
    creator.create_node("rust", "my_rust_node")
    
    # 获取所有支持的类型
    supported = creator.get_supported_languages()
"""

import os
import sys
import importlib.util
from typing import Dict, Callable, Optional


class NodeCreatorManager:
    """节点创建管理器 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 防止重复初始化
        if NodeCreatorManager._initialized:
            return
        
        NodeCreatorManager._initialized = True
        
        # 节点创建器注册表 {language: create_function}
        self._creators: Dict[str, Callable] = {}
        
        # 自动注册内置的创建器
        self._register_builtin_creators()
        
        print(f"✅ 节点创建管理器已初始化，支持的语言: {list(self._creators.keys())}")
    
    @classmethod
    def get_instance(cls) -> 'NodeCreatorManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _register_builtin_creators(self):
        """注册内置的节点创建器"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 注册 Python 节点创建器
        python_creator_path = os.path.join(base_dir, "python_create_node.py")
        if os.path.exists(python_creator_path):
            try:
                spec = importlib.util.spec_from_file_location(
                    "python_create_node_module",
                    python_creator_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 注册创建函数
                if hasattr(module, 'create_clean_node_with_empty_venv'):
                    self.register_creator("python", module.create_clean_node_with_empty_venv)
                    print(f"✅ 已注册 Python 节点创建器")
            except Exception as e:
                print(f"⚠️ 注册 Python 创建器失败: {e}")
        
        # 注册 Rust 节点创建器
        rust_creator_path = os.path.join(base_dir, "rust_create_node.py")
        if os.path.exists(rust_creator_path):
            try:
                spec = importlib.util.spec_from_file_location(
                    "rust_create_node_module",
                    rust_creator_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 注册创建函数（使用 generate_node 函数）
                if hasattr(module, 'generate_node'):
                    # 包装函数，使其符合标准接口 func(node_name: str)
                    def rust_creator_wrapper(node_name: str):
                        module.generate_node(node_name)
                    
                    self.register_creator("rust", rust_creator_wrapper)
                    print(f"✅ 已注册 Rust 节点创建器")
                elif hasattr(module, 'main'):
                    # 如果没有专门的创建函数，尝试适配 main 函数
                    self.register_creator("rust", lambda name: self._adapt_rust_main(module, name))
                    print(f"✅ 已注册 Rust 节点创建器（适配器模式）")
            except Exception as e:
                print(f"⚠️ 注册 Rust 创建器失败: {e}")
    
    def _adapt_rust_main(self, module, node_name: str):
        """适配器：将 rust_create_node.py 的 main 函数适配为标准接口"""
        # 保存原始 sys.argv
        original_argv = sys.argv.copy()
        
        try:
            # 模拟命令行参数
            sys.argv = ["rust_create_node.py", node_name]
            
            # 调用 main 函数
            if hasattr(module, 'main'):
                module.main()
            else:
                raise AttributeError("rust_create_node.py 缺少 main 函数")
        finally:
            # 恢复原始 sys.argv
            sys.argv = original_argv
    
    def register_creator(self, language: str, creator_func: Callable):
        """
        注册节点创建器
        
        Args:
            language: 语言标识（如 "python", "rust", "nodejs"）
            creator_func: 创建函数，签名为 func(node_name: str)
        """
        self._creators[language.lower()] = creator_func
        print(f"📝 注册节点创建器: {language}")
    
    def unregister_creator(self, language: str):
        """注销节点创建器"""
        lang = language.lower()
        if lang in self._creators:
            del self._creators[lang]
            print(f"❌ 注销节点创建器: {language}")
    
    def create_node(self, language: str, node_name: str) -> bool:
        """
        创建节点（统一入口）
        
        Args:
            language: 语言类型（"python", "rust", "nodejs" 等）
            node_name: 节点名称
            
        Returns:
            bool: 是否创建成功
        """
        lang = language.lower()
        
        # 检查是否支持该语言
        if lang not in self._creators:
            print(f"❌ 不支持的语言类型: {language}")
            print(f"   支持的语言: {list(self._creators.keys())}")
            return False
        
        # 验证节点名称
        if not node_name or not node_name.strip():
            print("❌ 节点名称不能为空")
            return False
        
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', node_name):
            print("❌ 节点名称只能包含字母、数字、下划线和连字符")
            return False
        
        try:
            print(f"🚀 开始创建 {lang.upper()} 节点: {node_name}")
            creator_func = self._creators[lang]
            creator_func(node_name)
            print(f"✅ {lang.upper()} 节点创建成功: {node_name}")
            return True
        except Exception as e:
            print(f"❌ 创建节点失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_supported_languages(self) -> list:
        """获取所有支持的语言类型"""
        return list(self._creators.keys())
    
    def has_creator(self, language: str) -> bool:
        """检查是否支持指定语言"""
        return language.lower() in self._creators
    
    def get_creator_count(self) -> int:
        """获取已注册的创建器数量"""
        return len(self._creators)


# ==================== 便捷函数（供外部直接调用）====================

def create_python_node(node_name: str) -> bool:
    """便捷函数：创建 Python 节点"""
    manager = NodeCreatorManager.get_instance()
    return manager.create_node("python", node_name)


def create_rust_node(node_name: str) -> bool:
    """便捷函数：创建 Rust 节点"""
    manager = NodeCreatorManager.get_instance()
    return manager.create_node("rust", node_name)


def get_supported_languages() -> list:
    """便捷函数：获取支持的语言列表"""
    manager = NodeCreatorManager.get_instance()
    return manager.get_supported_languages()


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("节点创建管理器测试")
    print("=" * 60)
    
    # 获取管理器实例
    manager = NodeCreatorManager.get_instance()
    
    # 显示支持的语言
    print(f"\n支持的语言: {manager.get_supported_languages()}")
    print(f"创建器数量: {manager.get_creator_count()}")
    
    # 测试创建 Python 节点
    print("\n--- 测试创建 Python 节点 ---")
    success = manager.create_node("python", "test_python_node")
    print(f"结果: {'成功' if success else '失败'}")
    
    # 测试创建 Rust 节点
    print("\n--- 测试创建 Rust 节点 ---")
    success = manager.create_node("rust", "test_rust_node")
    print(f"结果: {'成功' if success else '失败'}")
    
    print("\n" + "=" * 60)
