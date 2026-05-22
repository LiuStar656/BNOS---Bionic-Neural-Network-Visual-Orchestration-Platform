"""
BNOS Launcher — 纯 tkinter 启动动画，不依赖任何虚拟环境/PyQt6
打包: pyinstaller --onefile --windowed --name BNOS_Launcher launcher.py
"""
import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os
import tempfile
import time

# ── 配置 ──
WIDTH, HEIGHT = 620, 346
BG = "#1e1e1e"
FG = "#ffffff"
FG_DIM = "#aaa"
BORDER = "#777"
BAR_BG = "#2a2a2a"
BAR_FG = "#777"

ASCII_BNOS = [
    " █████╗     ███╗  ██╗     █████╗     ██████╗ ",
    " ██╔══██╗   ████╗ ██║    ██╔══██╗   ██╔════╝ ",
    " ██████╔╝   ██╔██╗██║    ██║  ██║   ╚█████╗  ",
    " ██╔══██╗   ██║╚████║    ██║  ██║    ╚═══██╗ ",
    " ██████╔╝   ██║ ╚███║    ╚█████╔╝   ██████╔╝ ",
    " ╚═════╝    ╚═╝  ╚══╝     ╚════╝    ╚═════╝  ",
]


def find_venv_python():
    """查找虚拟环境中的 Python"""
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "myenv_new", "Scripts", "python.exe"),
        os.path.join(base, "myenv_new", "bin", "python3"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return sys.executable


def main():
    marker = os.path.join(tempfile.gettempdir(), f"bnos_ready_{os.getpid()}.marker")
    # 清理旧标记
    if os.path.exists(marker):
        os.remove(marker)

    venv_python = find_venv_python()
    base = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(base, "bnos_console.py")

    # 启动主程序（后台）
    proc = subprocess.Popen(
        [venv_python, main_script, "--marker", marker],
        cwd=base,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # ── tkinter 闪屏 ──
    root = tk.Tk()
    root.overrideredirect(True)  # 无边框
    root.configure(bg=BG)
    root.attributes("-topmost", True)

    # 居中
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - WIDTH) // 2
    y = (sh - HEIGHT) // 2
    root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

    # 外边框用 Canvas 画
    cv = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0)
    cv.pack(fill="both", expand=True)
    cv.create_rectangle(2, 2, WIDTH - 2, HEIGHT - 2, outline=BORDER, width=3)

    content = tk.Frame(root, bg=BG)
    content.place(relx=0.5, rely=0.5, anchor="center", width=WIDTH - 40, height=HEIGHT - 30)

    # ASCII 标题
    for line in ASCII_BNOS:
        lbl = tk.Label(content, text=line, font=("Consolas", 12, "bold"),
                       fg=FG, bg=BG)
        lbl.pack()

    tk.Label(content, text="BNOS  CONSOLE", font=("Consolas", 11, "bold"),
             fg="#ccc", bg=BG).pack()
    tk.Label(content, text="Bionic Neural Network Program Operating System",
             font=("Consolas", 8), fg=FG_DIM, bg=BG).pack(pady=(0, 8))

    # 日志区
    log_frame = tk.Frame(content, bg=BG)
    log_frame.pack(fill="x")
    log_text = tk.Text(log_frame, height=4, bg=BG, fg=FG_DIM, font=("Consolas", 9),
                       bd=0, wrap="word", state="disabled")
    log_text.pack(fill="x")

    # 进度条
    bar_frame = tk.Frame(content, bg=BG)
    bar_frame.pack(fill="x", pady=(6, 0))
    bar_cv = tk.Canvas(bar_frame, height=10, bg=BAR_BG, highlightthickness=0)
    bar_cv.pack(fill="x")
    bar_rect = bar_cv.create_rectangle(0, 0, 0, 10, fill=BAR_FG, outline="")

    hint = tk.Label(content, text="Loading...", font=("Consolas", 9),
                    fg="#888", bg=BG)
    hint.pack(pady=(2, 0))

    def log(msg):
        log_text.config(state="normal")
        log_text.insert("end", msg + "\n")
        log_text.see("end")
        log_text.config(state="disabled")
        root.update()

    def progress(pct, msg=""):
        w = int(bar_cv.winfo_width() * pct / 100)
        bar_cv.coords(bar_rect, 0, 0, w, 10)
        if msg:
            hint.config(text=msg)
        root.update()

    log("[*] BNOS starting...")
    progress(10, "Launching...")

    # 轮询标记文件
    steps = [
        (20, "Loading config..."),
        (40, "Building main window..."),
        (70, "Loading UI components..."),
        (90, "Restoring project..."),
    ]
    step_idx = 0
    start_time = time.time()
    last_progress = 10

    while proc.poll() is None:
        if os.path.exists(marker):
            progress(100, "Ready")
            log("[+] BNOS launched successfully")
            root.update()
            time.sleep(0.5)
            root.destroy()
            break

        # 根据时间推进进度条
        elapsed = time.time() - start_time
        while step_idx < len(steps) and elapsed > steps[step_idx][0] * 0.15:
            p, msg = steps[step_idx]
            if p > last_progress:
                progress(p, msg)
                log(f"[*] {msg}")
                last_progress = p
            step_idx += 1

        root.update()
        time.sleep(0.1)

    if os.path.exists(marker):
        os.remove(marker)

    # 主进程异常退出
    if proc.poll() is not None and proc.poll() != 0:
        root.destroy()


if __name__ == "__main__":
    main()
