"""
节点进程管理 — 统一启动/停止逻辑，PID 文件持久化，健康检测，进程扫描兜底
"""
import os
import subprocess
import signal
from ui.core.logger import logger


def _pid_file(node_path):
    """获取标准 PID 文件路径 (.pid)"""
    return os.path.join(node_path, ".pid")


def _named_pid_file(node_path):
    """获取命名的 PID 文件路径 (node_python_<name>.pid)"""
    node_name = os.path.basename(node_path)
    return os.path.join(node_path, f"{node_name}.pid")


def _get_pid_file(node_path):
    """获取实际存在的 PID 文件路径（优先命名格式）"""
    named_pid = _named_pid_file(node_path)
    if os.path.exists(named_pid):
        return named_pid
    return _pid_file(node_path)


def _write_pid(node_path, pid):
    try:
        # 写入两种格式的 PID 文件
        # 1. 命名格式：node_python_<name>.pid
        named_pid = _named_pid_file(node_path)
        with open(named_pid, 'w') as f:
            f.write(str(pid))
        # 2. 标准格式：.pid（保持兼容性）
        with open(_pid_file(node_path), 'w') as f:
            f.write(str(pid))
    except Exception:
        pass


def _delete_pid(node_path):
    try:
        # 删除两种格式的 PID 文件
        pf = _pid_file(node_path)
        if os.path.exists(pf):
            os.remove(pf)
        named_pf = _named_pid_file(node_path)
        if os.path.exists(named_pf):
            os.remove(named_pf)
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
    """扫描系统中属于该节点的所有 Python 进程（按 python.exe/pythonw.exe 路径精确匹配）
    
    Returns: list of PIDs
    """
    target_exe = _python_exe_for_node(node_path)
    target_exe_norm = os.path.normpath(target_exe).lower()
    # 同时检测 pythonw.exe（无窗口模式）
    target_exe_norm_w = target_exe_norm.replace('python.exe', 'pythonw.exe')
    pids = []
    try:
        if os.name == 'nt':
            # PowerShell 获取完整 ExecutablePath（同时检测 python.exe 和 pythonw.exe）
            result = subprocess.run(
                ['powershell', '-Command',
                 f"Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
                 f"ForEach-Object {{ $_.ProcessId.ToString() + '|' + ($_.ExecutablePath ?? '') }}"],
                capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if '|' not in line:
                    continue
                pid_str, exe_path = line.split('|', 1)
                exe_path = os.path.normpath(exe_path.strip()).lower()
                # 匹配 python.exe 或 pythonw.exe
                if exe_path == target_exe_norm or exe_path == target_exe_norm_w:
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

def _load_start_json(node_path):
    """加载节点目录下的 start.json 配置文件"""
    start_json_path = os.path.join(node_path, "start.json")
    if not os.path.exists(start_json_path):
        logger.debug("start.json 不存在: %s", start_json_path)
        return None
    
    try:
        import json
        with open(start_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning("读取 start.json 失败: %s", e)
        return None


def start_node_process(node_info):
    """启动节点进程并写入 PID 文件（仅使用 JSON 配置启动）
    
    启动前自动清理该节点的所有旧孤儿进程，防止进程堆积。
    必须存在 start.json 配置文件才能启动节点。
    """
    node_path = node_info['path']
    node_name = os.path.basename(node_path)

    logger.info("开始启动节点: %s", node_name)
    logger.debug("节点路径: %s", node_path)

    # 1. 先清理可能残留的旧进程（PID 文件丢失的孤儿）
    logger.debug("启动前清理残留进程: %s", node_name)
    _kill_all_node_processes(node_path)

    # 2. 读取 start.json 配置（必须存在）
    start_config = _load_start_json(node_path)
    if not start_config:
        error_msg = f"start.json 配置文件不存在或读取失败: {node_path}"
        logger.error(error_msg)
        return False, error_msg
    
    logger.info("使用 start.json 配置启动节点")
    
    # 提取节点配置（支持单节点和多节点格式）
    if 'nodes' in start_config and isinstance(start_config['nodes'], list):
        # 查找当前节点的配置
        node_config = None
        for n in start_config['nodes']:
            if n.get('name') == node_name or n.get('path') == node_path:
                node_config = n
                break
        if node_config:
            # 更新 node_info 中的配置
            if 'config' in node_config:
                node_info['config'] = node_config['config']
                logger.debug("从 start.json 加载配置: %s", node_config['config'])
    elif 'config' in start_config:
        # 单节点格式
        node_info['config'] = start_config['config']
        logger.debug("从 start.json 加载配置: %s", start_config['config'])

    # 3. 定位虚拟环境 Python 解释器
    python_exe = _python_exe_for_node(node_path)
    listener_py = os.path.join(node_path, "listener.py")

    logger.debug("Python 解释器: %s", python_exe)
    logger.debug("Listener 脚本: %s", listener_py)

    # 检查必要文件是否存在
    if not os.path.exists(python_exe):
        error_msg = f"虚拟环境 Python 解释器不存在: {python_exe}"
        logger.error(error_msg)
        return False, error_msg
    
    if not os.path.exists(listener_py):
        error_msg = f"Listener 脚本不存在: {listener_py}"
        logger.error(error_msg)
        return False, error_msg

    # 直接运行 listener.py（PID 即为实际 Python 进程）
    try:
        if os.name == 'nt':
            process = subprocess.Popen(
                [python_exe, listener_py],
                cwd=node_path,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                [python_exe, listener_py],
                cwd=node_path, 
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        import time
        time.sleep(2.0)
        
        exit_code = process.poll()
        if exit_code is not None:
            stdout, stderr = process.communicate(timeout=5)
            error_msg = f"启动失败 (exit={exit_code}): {stderr}"
            logger.error("启动失败 (exit=%d): %s", exit_code, node_name)
            logger.error("stdout: %s", stdout)
            logger.error("stderr: %s", stderr)
            return False, error_msg

        node_info['process'] = process
        node_info['status'] = 'running'
        _write_pid(node_path, process.pid)
        logger.info("节点已启动: %s PID=%d", node_name, process.pid)
        return True, None
        
    except Exception as e:
        error_msg = f"启动异常: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


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
    selected = None
    
    # 优先从画布获取选中节点
    if main_window.canvas:
        selected = main_window.canvas.get_selected_node()
    
    # 如果画布没有选中，从节点列表获取
    if not selected:
        if main_window.node_list_panel:
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
    """读取 PID 文件，返回 PID 或 None
    
    优先读取命名格式的 PID 文件 (node_python_<name>.pid)，
    如果不存在则读取标准格式 (.pid)。
    """
    # 优先尝试命名格式
    named_pf = _named_pid_file(node_path)
    if os.path.exists(named_pf):
        try:
            with open(named_pf, 'r') as f:
                return int(f.read().strip())
        except Exception:
            pass
    
    # 回退到标准格式
    pf = _pid_file(node_path)
    if os.path.exists(pf):
        try:
            with open(pf, 'r') as f:
                return int(f.read().strip())
        except Exception:
            pass
    
    return None


def _get_child_pids(parent_pid):
    """获取 parent_pid 的所有子进程 PID（使用 psutil 遍历进程树）"""
    try:
        import psutil
        children = []
        for proc in psutil.process_iter(["pid", "ppid", "name"]):
            if proc.info["ppid"] == parent_pid:
                children.append(proc.info["pid"])
        return children
    except ImportError:
        # 无 psutil → 仅检查 PID 存活（退化为二态：运行/停止）
        return []


def _listener_has_active_child(pid):
    """listener 是否有名为 main 的活跃子进程（正在执行任务）"""
    child_pids = _get_child_pids(pid)
    if not child_pids:
        return False
    try:
        import psutil
        for cp in child_pids:
            try:
                proc = psutil.Process(cp)
                if "main" in proc.name().lower():
                    return True
            except psutil.NoSuchProcess:
                continue
    except ImportError:
        pass
    return False


def check_running_processes(nodes_data):
    """检测所有节点进程状态（三态：running/idle/stopped）
    
    先通过进程扫描检测实际的 Python 进程，再回退到 PID 文件和 process 对象。
    区分 idle（listener 运行但无 main 子进程）和 running（listener + main 都在运行）。
    
    关键修复：优先通过进程扫描检测，避免脚本启动时记录的是脚本进程而非 Python 进程的问题。
    """
    dead_nodes = []
    for name, info in nodes_data.items():
        if info.get('status') not in ('running', 'idle'):
            continue

        node_path = info['path']
        process = info.get('process')
        pid = process.pid if process else _read_pid(node_path)

        # 优先通过进程扫描检测实际运行的 Python 进程
        # 这是关键修复：脚本启动时记录的 process 可能是脚本进程而非 Python 进程
        actual_pids = _find_node_processes(node_path)
        
        if actual_pids:
            # 找到了实际运行的 Python 进程
            actual_pid = actual_pids[0]
            
            # 更新 PID 文件（如果记录的 PID 不正确）
            if pid != actual_pid:
                _write_pid(node_path, actual_pid)
            
            new_status = 'running' if _listener_has_active_child(actual_pid) else 'idle'
            if info.get('status') != new_status:
                info['status'] = new_status
                dead_nodes.append((name, None, new_status))  # None=状态变更,非退出
            continue

        # 进程扫描未找到 Python 进程 → 检查记录的 PID 是否仍存活
        if pid is not None and _is_pid_alive(pid):
            # 进程仍在运行，但不是预期的 Python 进程（可能是脚本进程）
            # 由于没有找到实际的 listener.py 进程，标记为 stopped
            pass  # 继续到下面的逻辑处理
            
        # 确认进程已退出
        exit_code = process.poll() if process else None
        info['process'] = None
        info['status'] = 'stopped'
        _delete_pid(node_path)
        dead_nodes.append((name, exit_code, 'stopped'))
        logger.info("节点 %s 进程已退出 (exit code: %s)", name, exit_code)

    return dead_nodes