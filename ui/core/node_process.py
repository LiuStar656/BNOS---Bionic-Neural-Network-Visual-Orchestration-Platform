"""
节点进程管理 — 统一启动/停止逻辑，PID 文件持久化，健康检测，进程扫描兜底
"""
import os
import subprocess
import signal
from ui.core.logger import logger


def _pid_file(node_path):
    return os.path.join(node_path, ".pid")


def _write_pid(node_path, pid):
    try:
        with open(_pid_file(node_path), 'w') as f:
            f.write(str(pid))
    except Exception:
        pass


def _delete_pid(node_path):
    try:
        pf = _pid_file(node_path)
        if os.path.exists(pf):
            os.remove(pf)
    except Exception:
        pass


def _is_pid_alive(pid):
    """检查 PID 对应的进程是否仍在运行"""
    try:
        if os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


# ---- 进程扫描兜底（处理 PID 文件丢失 / start.bat 孤儿进程） ----

def _python_exe_for_node(node_path):
    """获取节点虚拟环境中的 Python 解释器路径"""
    if os.name == 'nt':
        return os.path.normpath(os.path.join(node_path, "venv", "Scripts", "python.exe"))
    else:
        return os.path.normpath(os.path.join(node_path, "venv", "bin", "python"))


def _find_node_processes(node_path):
    """扫描系统中属于该节点的所有 Python 进程（按 python.exe 路径精确匹配）
    
    Returns: list of PIDs
    """
    target_exe = _python_exe_for_node(node_path)
    target_exe_norm = os.path.normpath(target_exe).lower()
    pids = []
    try:
        if os.name == 'nt':
            # PowerShell 获取完整 ExecutablePath
            result = subprocess.run(
                ['powershell', '-Command',
                 f"Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                 f"ForEach-Object {{ $_.ProcessId.ToString() + '|' + ($_.ExecutablePath ?? '') }}"],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if '|' not in line:
                    continue
                pid_str, exe_path = line.split('|', 1)
                exe_path = os.path.normpath(exe_path.strip()).lower()
                if exe_path == target_exe_norm:
                    try:
                        pids.append(int(pid_str))
                    except ValueError:
                        pass
        else:
            # Linux/Mac: pgrep -f
            result = subprocess.run(
                ['pgrep', '-f', f'python.*{node_path}.*listener'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split('\n'):
                try:
                    pids.append(int(line.strip()))
                except ValueError:
                    pass
    except Exception as e:
        logger.debug("进程扫描异常: %s", e)
    return pids


def _kill_all_node_processes(node_path):
    """强制终止该节点的所有孤儿进程（PID 文件丢失时的兜底）"""
    pids = _find_node_processes(node_path)
    killed = 0
    for pid in pids:
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                               capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                os.kill(pid, signal.SIGKILL)
            killed += 1
            logger.info("已清理孤儿进程 PID=%d (节点: %s)", pid, os.path.basename(node_path))
        except Exception as e:
            logger.warning("清理孤儿进程 PID=%d 失败: %s", pid, e)
    if killed:
        logger.info("共清理 %d 个孤儿进程 (节点: %s)", killed, os.path.basename(node_path))


# ---- 核心 API ----

def start_node_process(node_info):
    """启动节点进程并写入 PID 文件（直接运行 Python 获取真实 PID）
    
    启动前自动清理该节点的所有旧孤儿进程，防止进程堆积。
    """
    node_path = node_info['path']
    node_name = os.path.basename(node_path)

    # 1. 先清理可能残留的旧进程（PID 文件丢失的孤儿）
    logger.debug("启动前清理残留进程: %s", node_name)
    _kill_all_node_processes(node_path)

    # 定位虚拟环境 Python 解释器
    python_exe = _python_exe_for_node(node_path)
    listener_py = os.path.join(node_path, "listener.py")

    # 回退：如果 venv Python 不存在，尝试 start.bat
    if not os.path.exists(python_exe):
        logger.warning("venv Python 不存在，回退到 start.bat")
        start_script = os.path.join(node_path, "start.bat" if os.name == 'nt' else "start.sh")
        if not os.path.exists(start_script):
            return False, f"启动脚本不存在: {start_script}"
        try:
            if os.name == 'nt':
                process = subprocess.Popen(
                    [start_script, "--no-pause"],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            else:
                os.chmod(start_script, 0o755)
                process = subprocess.Popen(
                    ["/bin/bash", start_script, "--no-pause"],
                    cwd=node_path, start_new_session=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            node_info['process'] = process
            node_info['status'] = 'running'
            _write_pid(node_path, process.pid)
            return True, None
        except Exception as e:
            return False, str(e)

    # 直接运行 listener.py（PID 即为实际 Python 进程）
    try:
        if os.name == 'nt':
            process = subprocess.Popen(
                [python_exe, listener_py],
                cwd=node_path,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            process = subprocess.Popen(
                [python_exe, listener_py],
                cwd=node_path, start_new_session=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        # 启动后短暂等待，检测进程是否立即崩溃（挂载的 venv 可能损坏）
        import time
        time.sleep(1.2)
        exit_code = process.poll()
        if exit_code is not None:
            # 进程已退出 → venv 损坏，回退到 start.bat
            logger.warning("直接启动失败 (exit=%d)，回退到 start.bat: %s", exit_code, node_name)
            _delete_pid(node_path)
            start_script = os.path.join(node_path, "start.bat" if os.name == 'nt' else "start.sh")
            if not os.path.exists(start_script):
                return False, f"venv 损坏且启动脚本不存在: {start_script}"
            if os.name == 'nt':
                process = subprocess.Popen(
                    [start_script, "--no-pause"],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            else:
                os.chmod(start_script, 0o755)
                process = subprocess.Popen(
                    ["/bin/bash", start_script, "--no-pause"],
                    cwd=node_path, start_new_session=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

        node_info['process'] = process
        node_info['status'] = 'running'
        _write_pid(node_path, process.pid)
        logger.info("节点已启动: %s PID=%d", node_name, process.pid)
        return True, None
    except Exception as e:
        return False, str(e)


def stop_node_process(node_info, force=False):
    """停止节点进程并删除 PID 文件
    
    先尝试通过 PID 文件终止，失败后使用进程扫描兜底强制清理。
    """
    node_path = node_info['path']
    node_name = os.path.basename(node_path)

    process = node_info.get('process')
    pid = process.pid if process else _read_pid(node_path)

    killed = False
    if pid is not None:
        try:
            if os.name == 'nt':
                result = subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                                        capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode == 0:
                    killed = True
                    logger.info("已终止进程 PID=%d (%s)", pid, node_name)
                else:
                    logger.warning("taskkill PID=%d 失败: %s", pid, result.stderr.decode(errors='ignore').strip())
            else:
                try:
                    os.kill(pid, signal.SIGTERM)
                    if process:
                        process.wait(timeout=5)
                    killed = True
                except ProcessLookupError:
                    pass
        except Exception as e:
            logger.warning("停止进程 PID=%d 异常: %s", pid, e)

    # 兜底：PID 方式失败或 PID 不存在，用进程扫描清理
    if not killed:
        remaining = _find_node_processes(node_path)
        if remaining:
            logger.warning("PID 方式未能终止 %s，使用进程扫描兜底清理 (发现 %d 个进程)",
                           node_name, len(remaining))
            _kill_all_node_processes(node_path)
        else:
            logger.debug("未发现 %s 的残留进程", node_name)

    node_info['process'] = None
    node_info['status'] = 'stopped'
    _delete_pid(node_path)
    return True, None


def resolve_selected_node(main_window):
    """获取选中的节点名称（优先画布，回退到节点列表）"""
    selected = main_window.canvas.get_selected_node()
    if not selected:
        from_list = main_window.node_list_panel.get_selected_nodes()
        selected = from_list[0] if from_list else None
    return selected


def detect_running_nodes(nodes_data):
    """扫描所有节点的 PID 文件，检测后台运行的进程并恢复状态
    
    用于 GUI 启动或项目载入时，恢复上一次会话中启动的节点状态。
    PID 文件丢失时，通过进程扫描兜底检测。
    
    Returns: list of (node_name, pid) for nodes detected as running
    """
    detected = []
    for name, info in nodes_data.items():
        if info.get('status') == 'running':
            continue  # 已标记运行，由 check_running_processes 验证

        node_path = info['path']

        # 优先通过 PID 文件检测
        pid = _read_pid(node_path)
        if pid is not None and _is_pid_alive(pid):
            info['status'] = 'running'
            detected.append((name, pid))
            logger.info("检测到后台运行节点(PID文件): %s (PID: %d)", name, pid)
            continue

        # 兜底：PID 文件不存在或 PID 已死，通过进程扫描检测
        orphan_pids = _find_node_processes(node_path)
        if orphan_pids:
            info['status'] = 'running'
            detected.append((name, orphan_pids[0]))
            # 写入 PID 文件以便后续管理
            _write_pid(node_path, orphan_pids[0])
            logger.info("检测到后台运行节点(进程扫描): %s (PIDs: %s)", name, orphan_pids)

    return detected


def _read_pid(node_path):
    """读取 PID 文件，返回 PID 或 None"""
    pf = _pid_file(node_path)
    if not os.path.exists(pf):
        return None
    try:
        with open(pf, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return None


def check_running_processes(nodes_data):
    """检测所有运行中节点的进程是否仍在运行
    
    先通过 process.poll() / PID 文件检查，再通过进程扫描兜底。
    """
    dead_nodes = []
    for name, info in nodes_data.items():
        if info.get('status') != 'running':
            continue

        node_path = info['path']
        process = info.get('process')
        pid = process.pid if process else _read_pid(node_path)

        # 有 PID 且进程存活 → 继续
        if pid is not None and _is_pid_alive(pid):
            continue

        # PID 检查失败 → 进程扫描兜底
        orphan_pids = _find_node_processes(node_path)
        if orphan_pids:
            # 进程实际还在运行（PID 文件可能存了错误 PID）
            _write_pid(node_path, orphan_pids[0])
            logger.debug("健康检测: %s PID 文件失效，进程扫描发现 %d 个存活进程，已修复", name, len(orphan_pids))
            continue

        # 确认进程已退出
        exit_code = process.poll() if process else None
        info['process'] = None
        info['status'] = 'stopped'
        _delete_pid(node_path)
        dead_nodes.append((name, exit_code))
        logger.info("节点 %s 进程已退出 (exit code: %s)", name, exit_code)

    return dead_nodes
