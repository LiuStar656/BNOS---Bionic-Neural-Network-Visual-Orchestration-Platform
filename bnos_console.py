"""
BNOS 桌面可视化节点编排平台 - 主入口
基于PyQt6的纯桌面端应用
"""
import sys
import os
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import BNOSMainWindow
from ui.core.logger import logger
from ui.core.i18n import init_i18n, t
from ui.icons import codicon


def _progress(progress_file, pct, msg):
    """向启动器发送进度"""
    if not progress_file:
        return
    try:
        with open(progress_file, 'a', encoding='utf-8') as f:
            f.write(f"{pct}|{msg}\n")
            f.flush()
    except Exception as e:
        print(f"[!] Progress write failed: {e}", file=sys.stderr)


def main():
    """应用程序主入口"""
    try:
        # ---- 进度文件（启动器通过 --progress 传递）----
        progress_file = None
        args = sys.argv[:]
        for i, a in enumerate(args):
            if a.startswith("--progress="):
                progress_file = a.split("=", 1)[1]
                args.remove(a)
                break
            elif a == "--progress" and i + 1 < len(args):
                progress_file = args[i + 1]
                del args[i:i + 2]
                break

        # ---- 加载语言 ----
        from ui.core.app_config import AppConfig
        saved_lang = AppConfig().get("language", "cn")
        init_i18n(saved_lang)
        if progress_file:
            _progress(progress_file, 35, "Config loaded (" + saved_lang + ")")

        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
        QApplication.setStyle("Fusion")
        app = QApplication(sys.argv)
        app.setApplicationName(t("_k_app_name"))
        app.setOrganizationName("BNOS")

        # 初始化图标系统（加载 Codicon 字体）
        codicon.init()

        if progress_file:
            _progress(progress_file, 45, "Qt initialized")

        # ---- 创建主窗口 ----
        if progress_file:
            _progress(progress_file, 55, "Building main window...")
        window = BNOSMainWindow()

        if progress_file:
            _progress(progress_file, 80, "Main window ready")

        # ---- 加载项目 ----
        if progress_file:
            _progress(progress_file, 90, "Restoring project...")
            _progress(progress_file, 100, "BNOS ready")
            time.sleep(0.3)  # 给启动器读文件的时间

        window.show()
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