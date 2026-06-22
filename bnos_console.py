"""
BNOS 桌面可视化节点编排平台 - 主入口
基于PySide6的纯桌面端应用
"""
import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
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

        # 高DPI支持 - 必须在创建QApplication之前设置
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs)
        QApplication.setStyle("Fusion")
        app = QApplication(sys.argv)
        app.setApplicationName(t("_k_app_name"))
        app.setOrganizationName("BNOS")
        
        # 设置应用程序默认字体（避免系统缺少特定字体导致警告）
        from PySide6.QtGui import QFont
        default_font = QFont()
        default_font.setFamilies(["Segoe UI", "Microsoft YaHei", "Arial", "Helvetica", "sans-serif"])
        app.setFont(default_font)

        # 初始化图标系统（加载 Codicon 字体）
        codicon.init()

        # 初始化应用上下文
        from ui.core.application_context import ApplicationContext
        app_context = ApplicationContext()
        app_context.initialize()

        if progress_file:
            _progress(progress_file, 45, "Qt initialized")

        # ---- 创建主窗口 ----
        if progress_file:
            _progress(progress_file, 55, "Building main window...")
        window = BNOSMainWindow()
        
        # 初始化依赖主窗口的 UI 服务
        app_context.initialize_ui_services(window)

        if progress_file:
            _progress(progress_file, 80, "Main window ready")

        # ---- 加载项目 ----
        if progress_file:
            _progress(progress_file, 90, "Restoring project...")
            _progress(progress_file, 100, "BNOS ready")
            time.sleep(0.3)  # 给启动器读文件的时间

        window.show()
        ret = app.exec()
        
        # 关闭应用上下文
        app_context.shutdown()
        
        if ret == 42:
            # 使用重启脚本，确保先完全关闭再启动新进程
            import subprocess
            restart_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "restart_helper.py")
            main_script = os.path.abspath(__file__)
            subprocess.Popen(
                [sys.executable, restart_script, main_script] + args,
                cwd=os.getcwd(),
                close_fds=True
            )
        sys.exit(ret)

    except KeyboardInterrupt:
        logger.info("BNOS shutdown")
        sys.exit(0)

    except Exception as e:
        logger.critical("BNOS fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()