"""
节点进程管理 — 统一启动/停止逻辑，PID 文件持久化，健康检测
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


def start_node_process(node_info):
    """启动节点进程并写入 PID 文件"""
    node_path = node_info['path']

    if os.name == 'nt':
        start_script = os.path.join(node_path, "start.bat")
    else:
        start_script = os.path.join(node_path, "start.sh")

    if not os.path.exists(start_script):
        return False, f"启动脚本不存在: {start_script}"

    try:
        if os.name == 'nt':
            process = subprocess.Popen(
                [start_script, "--no-pause"],
                cwd=node_path,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            os.chmod(start_script, 0o755)
            process = subprocess.Popen(
                ["/bin/bash", start_script, "--no-pause"],
                cwd=node_path,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        node_info['process'] = process
        node_info['status'] = 'running'
        _write_pid(node_path, process.pid)
        return True, None
    except Exception as e:
        return False, str(e)


def stop_node_process(node_info, force=False):
    """停止节点进程并删除 PID 文件"""
    process = node_info.get('process')
    if not process:
        node_info['status'] = 'stopped'
        _delete_pid(node_info['path'])
        return True, None

    try:
        if os.name == 'nt':
            try:
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                    capture_output=True, timeout=10
                )
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                    process.wait(timeout=3)
                except Exception:
                    pass
            except Exception as e:
                logger.error("taskkill 执行失败: %s", e)
                try:
                    process.kill()
                    process.wait(timeout=3)
                except Exception:
                    pass
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
    except Exception as e:
        logger.error("停止进程异常: %s", e)
        return False, str(e)

    node_info['process'] = None
    node_info['status'] = 'stopped'
    _delete_pid(node_info['path'])
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
    
    Returns: list of (node_name, pid) for nodes detected as running
    """
    detected = []
    for name, info in nodes_data.items():
        if info.get('status') == 'running':
            continue  # 已标记运行，由 check_running_processes 验证
        
        pid = _read_pid(info['path'])
        if pid is not None and _is_pid_alive(pid):
            info['status'] = 'running'
            detected.append((name, pid))
            logger.info("检测到后台运行节点: %s (PID: %d)", name, pid)
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
    """检测所有运行中节点的进程是否仍在运行"""
    dead_nodes = []
    for name, info in nodes_data.items():
        if info.get('status') != 'running':
            continue
        process = info.get('process')
        if not process:
            info['status'] = 'stopped'
            _delete_pid(info['path'])
            continue
        exit_code = process.poll()
        if exit_code is not None:
            info['process'] = None
            info['status'] = 'stopped'
            _delete_pid(info['path'])
            dead_nodes.append((name, exit_code))
            logger.info("节点 %s 进程已退出 (exit code: %s)", name, exit_code)
    return dead_nodes
