"""
快速测试：启动面板子进程

先启动主 GUI (python bnos_console.py)，再运行此脚本。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from ui.core.process_manager import ProcessManager

    app = QApplication.instance() or QApplication(sys.argv)

    pm = ProcessManager()
    pm.register("panel", "ui/panels/panel_process.py")
    proc = pm.get("panel")
    proc.crashed.connect(lambda pid: print("[崩溃] panel 退出，自动重启中..."))
    proc.started.connect(lambda pid: print(f"[启动] panel PID={proc.process.pid}"))
    proc.start()

    pid = proc.process.pid if proc.process else "?"
    print(f"面板子进程已启动 (PID={pid})")
    print("应弹出节点列表和属性面板两个窗口")
    print("关闭任一窗口 → 进程退出 → 自动重启")
    print("Ctrl+C 退出")

    try:
        app.exec()
    except KeyboardInterrupt:
        pm.stop_all()
        print("已停止")
