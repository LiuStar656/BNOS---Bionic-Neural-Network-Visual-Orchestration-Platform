"""
BNOS 桌面可视化节点编排平台 - 主入口
基于PyQt6的纯桌面端GUI应用
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import BNOSMainWindow
from ui.core.logger import logger
from ui.core.i18n import init_i18n, t


def main():
    """应用程序主入口"""
    try:
        # 读取保存的语言设置
        from ui.core.app_config import AppConfig
        saved_lang = AppConfig().get("language", "cn")
        init_i18n(saved_lang)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
        QApplication.setStyle("Fusion")  # Fusion确保QSS完全控制
        app = QApplication(sys.argv)
        app.setApplicationName(t("_k_app_name"))
        app.setOrganizationName("BNOS")
        
        # 创建并显示主窗口
        window = BNOSMainWindow()
        window.show()
        
        sys.exit(app.exec())
    
    except KeyboardInterrupt:
        logger.info("BNOS 已安全关闭")
        sys.exit(0)
    
    except Exception as e:
        logger.critical("BNOS 发生错误: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
