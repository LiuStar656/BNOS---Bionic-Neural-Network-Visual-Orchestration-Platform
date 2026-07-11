"""
BNOS Launcher — 纯 tkinter 启动动画 + 启动虚拟环境 + 监控主程序加载进度

运行方式:
  1. 直接运行:   python launcher.py
  2. 打包成 EXE: pyinstaller --onefile --windowed --name "BNOS_Console" launcher.py
     然后双击 BNOS_Console.exe 即可启动

工作流程:
  launcher 显示闪屏 → 后台启动 venv python bnos_console.py --progress=<file>
  → 主程序逐步写入进度 → launcher 实时更新闪屏 → 主程序就绪 → 闪屏关闭
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk

    HAS_TK = True
except ImportError:
    HAS_TK = False

# ── 闪屏配置 ──
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
    try:
        base = Path(__file__).resolve().parent
    except NameError:
        base = Path.cwd()
    # Windows 优先 pythonw（无控制台窗口）
    candidates = [
        base / "venv" / "Scripts" / "pythonw.exe",
        base / "venv" / "Scripts" / "python.exe",
        base / "venv" / "bin" / "python3",
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path(sys.executable)


def main():
    if not HAS_TK:
        _fallback_launch()
        return

    base = Path(__file__).resolve().parent
    main_script = base / "bnos_console.py"

    # 进度文件：主程序写入，启动器读取
    progress_file = Path(tempfile.gettempdir()) / f"bnos_progress_{os.getpid()}.txt"
    if progress_file.exists():
        progress_file.unlink()

    # ── tkinter 闪屏 ──
    root = tk.Tk()
    root.overrideredirect(True)
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{WIDTH}x{HEIGHT}+{(sw - WIDTH) // 2}+{(sh - HEIGHT) // 2}")

    cv = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0)
    cv.pack(fill="both", expand=True)
    cv.create_rectangle(2, 2, WIDTH - 2, HEIGHT - 2, outline=BORDER, width=3)

    content = tk.Frame(root, bg=BG)
    content.place(relx=0.5, rely=0.5, anchor="center", width=WIDTH - 40, height=HEIGHT - 30)

    for line in ASCII_BNOS:
        tk.Label(content, text=line, font=("Consolas", 12, "bold"), fg=FG, bg=BG).pack()

    tk.Label(content, text="BNOS  CONSOLE", font=("Consolas", 11, "bold"), fg="#ccc", bg=BG).pack()
    tk.Label(
        content, text="Bionic Neural Network Program Operating System", font=("Consolas", 8), fg=FG_DIM, bg=BG
    ).pack(pady=(0, 8))

    # 日志区
    log_frame = tk.Frame(content, bg=BG)
    log_frame.pack(fill="x")
    log_text = tk.Text(log_frame, height=4, bg=BG, fg=FG_DIM, font=("Consolas", 9), bd=0, wrap="word", state="disabled")
    log_text.pack(fill="x")

    # 进度条
    bar_frame = tk.Frame(content, bg=BG)
    bar_frame.pack(fill="x", pady=(6, 0))
    bar_cv = tk.Canvas(bar_frame, height=10, bg=BAR_BG, highlightthickness=0)
    bar_cv.pack(fill="x")
    bar_rect = bar_cv.create_rectangle(0, 0, 0, 10, fill=BAR_FG, outline="")

    hint = tk.Label(content, text="Loading...", font=("Consolas", 9), fg="#888", bg=BG)
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

    # ── 步骤 1: 加载虚拟环境 ──
    progress(5, "Checking environment...")
    log("[*] Checking virtual environment...")
    root.update()

    venv_python = find_venv_python()
    if not venv_python.exists():
        log("[!] Virtual environment not found")
        log("[!] Please run: python -m venv venv")
        log("[!] Then: venv\\Scripts\\pip install -r requirements.txt")
        progress(0, "Virtual environment missing")
        root.update()
        time.sleep(3)
        root.destroy()
        sys.exit(1)

    progress(15, "Virtual environment ready")
    log("[+] Virtual environment: " + str(venv_python))
    root.update()

    # ── 步骤 2: 启动主程序 ──
    progress(25, "Launching BNOS...")
    log("[*] Starting BNOS Console...")
    root.update()

    proc = subprocess.Popen(
        [str(venv_python), str(main_script), "--progress", str(progress_file)],
        cwd=str(base),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # ── 步骤 3: 等待主程序就绪（平滑动画进度条）──
    target_pct = 25  # 目标进度（从文件读取）
    display_pct = 25  # 当前显示进度（动画过渡）
    last_read_pos = 0
    start_time = time.time()
    finish_time = None  # 主程序完成时间

    while True:
        # 读取进度文件（更新目标值）
        if progress_file.exists():
            try:
                with progress_file.open(encoding="utf-8") as f:
                    f.seek(last_read_pos)
                    for line in f:
                        line = line.strip()
                        if "|" in line:
                            p_str, msg = line.split("|", 1)
                            try:
                                p = int(p_str)
                                if p > target_pct:
                                    target_pct = p
                                    log("[*] " + msg)
                            except ValueError:
                                pass
                    last_read_pos = f.tell()
            except Exception:
                pass

        # 进度条：新数据立即跳到目标，最后 5% 平滑收尾
        if display_pct < target_pct:
            gap = target_pct - display_pct
            if gap > 5:
                display_pct = target_pct  # 大步直接跳跃
            else:
                display_pct = min(display_pct + 1, target_pct)  # 收尾 1% 精调
            progress(display_pct, "")
            if display_pct >= 100 and finish_time is None:
                finish_time = time.time()

        # 主程序已退出 → 强制 100%
        if proc.poll() is not None and finish_time is None:
            target_pct = 100

        # 100% 后短暂延迟关闭
        if finish_time and time.time() - finish_time > 1:
            break

        # 超时兜底
        elapsed = time.time() - start_time
        if target_pct < 90 and elapsed > 8:
            target_pct = min(90, target_pct + 5)

        root.update()
        time.sleep(0.03)

    progress(100, "Ready")
    root.update()
    time.sleep(0.4)
    root.destroy()

    # 清理
    try:
        progress_file.unlink()
    except Exception:
        pass


def _fallback_launch():
    """无 tkinter 时的降级方案：直接启动主程序"""
    base = Path(__file__).resolve().parent
    venv_python = find_venv_python()
    main_script = base / "bnos_console.py"
    if not venv_python.exists():
        sys.exit(1)
    sys.exit(subprocess.call([str(venv_python), str(main_script)], cwd=str(base)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
