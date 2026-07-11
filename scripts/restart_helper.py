"""
BNOS 重启辅助脚本
先完全关闭旧进程，再启动新进程
"""

from __future__ import annotations

import os
import subprocess
import sys
import time


def is_process_running(pid):
    """检查指定 PID 的进程是否还在运行"""
    try:
        if os.name == "nt":  # Windows
            # 使用 tasklist 检查
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return str(pid) in result.stdout
        else:  # Unix-like
            # 发送信号 0，不发送实际信号但检查进程是否存在
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.SubprocessError):
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        return 1

    main_script = sys.argv[1]
    args = sys.argv[2:]

    # 获取父进程 PID（从环境变量中获取，或者使用 os.getppid()）
    parent_pid = os.getppid()

    # 构造新进程命令
    python_exe = sys.executable
    cmd = [python_exe, main_script] + args
    cwd = os.getcwd()

    # 等待父进程完全退出（最多等待 3 秒）
    wait_start = time.time()
    while is_process_running(parent_pid) and (time.time() - wait_start) < 3:
        time.sleep(0.1)

    if is_process_running(parent_pid):
        pass  # 父进程仍在运行，继续等待

    # 稍等一下，确保所有资源都已释放
    time.sleep(0.3)

    # 启动新进程
    try:
        subprocess.Popen(cmd, cwd=cwd, close_fds=True)
        return 0
    except Exception:
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
