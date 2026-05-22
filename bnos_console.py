"""
BNOS 桌面可视化节点编排平台 - 主入口
基于PyQt6的纯桌面端应用
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from ui.main_window import BNOSMainWindow
from ui.core.logger import logger
from ui.core.i18n import init_i18n, t


def main():
    """应用程序主入口"""
    try:
        # ---- 加载语言（在闪屏之前）----
        from ui.core.app_config import AppConfig
        saved_lang = AppConfig().get("language", "cn")
        init_i18n(saved_lang)

        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
        QApplication.setStyle("Fusion")
        app = QApplication(sys.argv)
        app.setApplicationName(t("_k_app_name"))
        app.setOrganizationName("BNOS")

        # ---- 启动闪屏（此时语言已就绪）----
        from ui.core.splash_screen import SplashScreen
        splash = SplashScreen()
        splash.show()
        splash.append_log(t("_k_splash_starting"))

        # ---- 进度 ----
        splash.set_progress(10, t("_k_splash_config") % saved_lang)
        splash.append_log(t("_k_splash_config") % saved_lang)

        splash.set_progress(20, t("_k_splash_logger"))
        splash.append_log(t("_k_splash_logger"))

        # ---- 创建主窗口 ----
        splash.set_progress(40, t("_k_splash_main_win"))
        splash.append_log(t("_k_splash_main_win"))
        window = BNOSMainWindow()

        splash.set_progress(75, t("_k_splash_main_ready"))
        splash.append_log(t("_k_splash_main_ready"))

        splash.set_progress(90, t("_k_splash_project"))
        splash.append_log(t("_k_splash_project"))

        # ---- 完成 ----
        splash.set_progress(100, "BNOS")
        splash.append_log(t("_k_splash_done"))

        window.show()
        # 主页面打开 2 秒后再关闭闪屏
        QTimer.singleShot(2000, splash.close_splash)

        ret = app.exec()
        if ret == 42:
            import subprocess
            subprocess.Popen([sys.executable, *sys.argv], cwd=os.getcwd())
        sys.exit(ret)

    except KeyboardInterrupt:
        logger.info("BNOS shutdown")
        sys.exit(0)

    except Exception as e:
        logger.critical("BNOS fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
