"""
自动修改 main_window.py 以支持纯菜单栏设计
"""
import re

def modify_main_window():
    file_path = r"f:\Bionic Neural Network Program Operating System\ui\main_window.py"
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"原始文件大小: {len(content)} 字符")
    
    # 修改1: 删除QToolBar导入
    content = re.sub(
        r'from PyQt6\.QtWidgets import \(\s+QMainWindow.*?QToolBar.*?\)',
        lambda m: m.group(0).replace('QToolBar, ', '').replace(', QToolBar', ''),
        content,
        flags=re.DOTALL
    )
    print("✅ 修改1: 删除QToolBar导入")
    
    # 修改2: 替换init_toolbar和init_menu调用为MenuManager
    old_init = """        # 初始化UI
        self.init_ui()
        self.init_toolbar()
        self.init_menu()"""
    
    new_init = """        # 初始化UI
        self.init_ui()
        
        # 初始化菜单栏（使用MenuManager）
        from ui.menu_manager import MenuManager
        MenuManager.init_menu(self)"""
    
    content = content.replace(old_init, new_init)
    print("✅ 修改2: 替换菜单初始化代码")
    
    # 修改3: 调整y坐标（三处）
    # init_ui中的y坐标
    content = re.sub(
        r'(panel_y = window_pos\.y\(\) \+) 100(\s+# 主窗口顶部 \+ 100px.*?工具栏)',
        r'\g<1>60\g<2>'.replace('100px（留出两层工具栏空间）', '60px（留出菜单栏空间）'),
        content
    )
    
    # moveEvent中的y坐标
    content = re.sub(
        r'(panel_y = window_pos\.y\(\) \+) 100(\s+# 主窗口顶部 \+ 100px.*?工具栏\))',
        r'\g<1>60\g<2>'.replace('100px（留出两层工具栏）', '60px（留出菜单栏空间）'),
        content
    )
    
    # resizeEvent中的y坐标
    content = re.sub(
        r'(panel_y = window_pos\.y\(\) \+) 100(\s+# 主窗口顶部 \+ 100px.*?工具栏\))',
        r'\g<1>60\g<2>'.replace('100px（留出两层工具栏）', '60px（留出菜单栏空间）'),
        content
    )
    print("✅ 修改3: 调整y坐标从100改为60")
    
    # 修改4: 在clear_connections之后添加辅助方法
    helper_methods = '''
    def create_new_node_with_language(self, language):
        """使用指定语言创建新节点（委托给MenuManager）"""
        from ui.menu_manager import MenuManager
        MenuManager.create_new_node_with_language(self, language)
    
    def show_about(self):
        """显示关于对话框（委托给MenuManager）"""
        from ui.menu_manager import MenuManager
        MenuManager.show_about(self)
'''
    
    # 在clear_connections方法后插入
    pattern = r'(        self\.show_toast\("已清空所有连线", "success"\)\n)'
    replacement = r'\1' + helper_methods
    content = re.sub(pattern, replacement, content)
    print("✅ 修改4: 添加辅助方法")
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"修改后文件大小: {len(content)} 字符")
    print("✅ 所有修改完成！")

if __name__ == "__main__":
    modify_main_window()
