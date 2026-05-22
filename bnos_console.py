"""
BNOS 桌面可视化节点编排平台 - 主入口
基于PyQt6的纯桌面端应用
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
        # ---- 标记文件（启动器通过 --marker 传递）----
        marker_file = None
        args = sys.argv[:]
        for a in args:
            if a.startswith("--marker="):
                marker_file = a.split("=", 1)[1]
                args.remove(a)
                break

        # ---- 加载语言 ----
        from ui.core.app_config import AppConfig
        saved_lang = AppConfig().get("language", "cn")
        init_i18n(saved_lang)

        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
        QApplication.setStyle("Fusion")
        app = QApplication(sys.argv)
        app.setApplicationName(t("_k_app_name"))
        app.setOrganizationName("BNOS")

        # ---- 创建主窗口 ----
        window = BNOSMainWindow()
        window.show()

        # ---- 通知启动器 ----
        if marker_file:
            try:
                with open(marker_file, 'w') as f:
                    f.write("ready")
            except Exception:
                pass

        ret = app.exec()
        if ret == 42:
            import subprocess
            subprocess.Popen([sys.executable, *args], cwd=os.getcwd())
        sys.exit(ret)

    except KeyboardInterrupt:
        logger.info("BNOS shutdown")
        sys.exit(0)

    except Exception as e:
        logger.critical("BNOS fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
