"""
BNOS 桌面可视化节点编排平台 - 主入口
基于PyQt6的纯桌面端GUI应用
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_window import BNOSMainWindow


def main():
    """应用程序主入口"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("BNOS 节点编排平台")
        app.setOrganizationName("BNOS")
        
        # 创建并显示主窗口
        window = BNOSMainWindow()
        window.show()
        
        sys.exit(app.exec())
    
    except KeyboardInterrupt:
        # 用户按下 Ctrl+C，优雅退出
        print("\n\n👋 BNOS 已安全关闭")
        sys.exit(0)
    
    except Exception as e:
        # 其他未预期异常
        print(f"\n❌ BNOS 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
