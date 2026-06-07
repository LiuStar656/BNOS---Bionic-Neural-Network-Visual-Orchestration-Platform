"""
BNOS 重启辅助脚本
先完全关闭旧进程，再启动新进程
"""
import sys
import os
import time
import subprocess


def is_process_running(pid):
    """检查指定 PID 的进程是否还在运行"""
    try:
        if os.name == 'nt':  # Windows
            # 使用 tasklist 检查
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
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
        print("Usage: python restart_helper.py <main_script> [args...]")
        return 1
    
    main_script = sys.argv[1]
    args = sys.argv[2:]
    
    # 获取父进程 PID（从环境变量中获取，或者使用 os.getppid()）
    parent_pid = os.getppid()
    
    print(f"[Restart Helper] 准备重启 BNOS...")
    print(f"[Restart Helper] 父进程 PID: {parent_pid}")
    print(f"[Restart Helper] 主脚本: {main_script}")
    print(f"[Restart Helper] 参数: {args}")
    
    # 构造新进程命令
    python_exe = sys.executable
    cmd = [python_exe, main_script] + args
    cwd = os.getcwd()
    
    print(f"[Restart Helper] 工作目录: {cwd}")
    print(f"[Restart Helper] 命令: {cmd}")
    
    # 等待父进程完全退出（最多等待 3 秒）
    print(f"[Restart Helper] 等待父进程退出...")
    wait_start = time.time()
    while is_process_running(parent_pid) and (time.time() - wait_start) < 3:
        time.sleep(0.1)
    
    if is_process_running(parent_pid):
        print(f"[Restart Helper] 警告：父进程未在 3 秒内退出，继续启动新进程")
    else:
        print(f"[Restart Helper] 父进程已退出")
    
    # 稍等一下，确保所有资源都已释放
    time.sleep(0.3)
    
    # 启动新进程
    print(f"[Restart Helper] 正在启动新进程...")
    try:
        subprocess.Popen(cmd, cwd=cwd, close_fds=True)
        print(f"[Restart Helper] 新进程已启动！")
        return 0
    except Exception as e:
        print(f"[Restart Helper] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
