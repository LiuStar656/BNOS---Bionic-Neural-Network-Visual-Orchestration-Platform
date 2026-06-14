"""
快速测试：启动画布子进程

先启动主 GUI (python bnos_console.py)，再新开终端运行此脚本。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from ui.core.process_manager import ProcessManager

    app = QApplication.instance() or QApplication(sys.argv)

    pm = ProcessManager()
    pm.register("canvas", "ui/canvas/canvas_process.py")
    proc = pm.get("canvas")
    proc.crashed.connect(lambda pid: print(f"[崩溃] canvas 退出，自动重启中..."))
    proc.started.connect(lambda pid: print(f"[启动] canvas PID={proc.process.pid}"))
    proc.start()

    pid = proc.process.pid if proc.process else "?"
    print(f"画布子进程已启动 (PID={pid})")
    print("测试：关闭画布窗口 → 应自动重启（最多5次）")
    print("Ctrl+C 退出")

    try:
        app.exec()
    except KeyboardInterrupt:
        pm.stop_all()
        print("已停止")
