"""
快速测试：启动核心业务子进程

先启动主 GUI (python bnos_gui.py)，再运行此脚本。
核心进程无 UI，只输出日志。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if __name__ == "__main__":
    from PyQt6.QtCore import QCoreApplication
    from ui.core.process_manager import ProcessManager

    app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    pm = ProcessManager()
    pm.register("core", "ui/core/core_process.py")
    proc = pm.get("core")
    proc.crashed.connect(lambda pid: print("[崩溃] core 退出，自动重启中..."))
    proc.started.connect(lambda pid: print(f"[启动] core PID={proc.process.pid}"))
    proc.start()

    pid = proc.process.pid if proc.process else "?"
    print(f"核心进程已启动 (PID={pid})，无GUI，查看日志")
    print("Ctrl+C 退出")

    try:
        app.exec()
    except KeyboardInterrupt:
        pm.stop_all()
        print("已停止")
