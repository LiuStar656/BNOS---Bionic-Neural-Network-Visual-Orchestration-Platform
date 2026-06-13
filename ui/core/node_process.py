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

def _python_exe_for_node(node_path, start_config=None, node_name=None):
    """获取节点虚拟环境中的 Python 解释器路径
    
    优先从 start.json 的 python_exe 字段读取，若未配置则回退到默认路径。
    
    Args:
        node_path: 节点路径
        start_config: start.json 配置（可选）
        node_name: 节点名称（可选，用于在多节点配置中查找）
    
    Returns:
        str: Python 解释器路径
    """
    # 优先从 start_config 中读取 python_exe 配置
    if start_config and 'nodes' in start_config and isinstance(start_config['nodes'], list):
        for n in start_config['nodes']:
            if (node_name and n.get('name') == node_name) or n.get('path') == node_path:
                if 'python_exe' in n and n['python_exe']:
                    logger.debug("从 start.json 获取 Python 解释器: %s", n['python_exe'])
                    return os.path.normpath(n['python_exe'])
    elif start_config and 'python_exe' in start_config and start_config['python_exe']:
        # 单节点格式
        logger.debug("从 start.json 获取 Python 解释器: %s", start_config['python_exe'])
        return os.path.normpath(start_config['python_exe'])
    
    # 回退到默认路径
    if os.name == 'nt':
        return os.path.normpath(os.path.join(node_path, "venv", "Scripts", "python.exe"))
    else:
        return os.path.normpath(os.path.join(node_path, "venv", "bin", "python"))


def _validate_venv(python_exe):
    """验证虚拟环境是否有效
    
    Args:
        python_exe: Python 解释器路径
    
    Returns:
        tuple: (valid: bool, error_msg: str)
    """
    # 检查 Python 可执行文件是否存在且可执行
    if not os.path.isfile(python_exe):
        return False, f"Python 解释器文件不存在: {python_exe}"
    
    # 检查是否具有执行权限
    if os.name != 'nt' and not os.access(python_exe, os.X_OK):
        return False, f"Python 解释器没有执行权限: {python_exe}"
    
    # 尝试获取 Python 版本信息，验证解释器是否正常工作
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            [python_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=creationflags
        )
        
        if result.returncode != 0:
            return False, f"无法获取 Python 版本信息，虚拟环境可能损坏: {python_exe}"
        
        logger.debug("虚拟环境 Python 版本: %s", result.stdout.strip())
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"获取 Python 版本超时: {python_exe}"
    except Exception as e:
        return False, f"验证虚拟环境时发生错误: {str(e)}"


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


def _kill_process_tree(root_pid):
    """原子杀整棵进程树（使用系统级 /T 递归，无竞态窗口）
    
    Windows:  taskkill /F /T /PID  ← 内核递归杀所有后代
    Linux:    killpg(sig=SIGKILL)  ← 杀进程组
    
    Returns:
        bool: True 表示至少有一个进程被成功终止
    """
    try:
        if os.name == 'nt':
            result = subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(root_pid)],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # taskkill /T 返回 0 表示成功终止了至少一个进程
            # 255 通常是"进程名不存在但 PID 不匹配"或"拒绝访问"
            if result.returncode == 0:
                logger.info("已终止进程树 PID=%d", root_pid)
                return True
            else:
                logger.warning("终止进程树 PID=%d 失败 (exit=%d): %s",
                               root_pid, result.returncode, result.stderr.strip())
                return False
        else:
            os.killpg(os.getpgid(root_pid), signal.SIGKILL)
            logger.info("已终止进程组 PGID=%d", root_pid)
            return True
    except (ProcessLookupError, OSError):
        # 进程已不存在
        logger.debug("进程 PID=%d 已不存在", root_pid)
        return True  # 已死 = 成功
    except Exception as e:
        logger.warning("终止进程树 PID=%d 异常: %s", root_pid, e)
        return False


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


def _check_directory_permissions(node_path):
    """检查节点目录权限
    
    Returns:
        tuple: (valid: bool, error_msg: str)
    """
    if not os.path.exists(node_path):
        return False, f"节点目录不存在: {node_path}"
    
    # 检查读取权限
    if not os.access(node_path, os.R_OK):
        return False, f"无法读取节点目录（权限不足）: {node_path}"
    
    # 检查写入权限（需要创建日志文件等）
    if not os.access(node_path, os.W_OK):
        return False, f"无法写入节点目录（权限不足）: {node_path}"
    
    return True, ""


def start_node_process(node_info):
    """启动节点进程并写入 PID 文件（仅使用 JSON 配置启动）
    
    启动前自动清理该节点的所有旧孤儿进程，防止进程堆积。
    必须存在 start.json 配置文件才能启动节点。
    """
    node_path = node_info['path']
    node_name = os.path.basename(node_path)

    logger.info("开始启动节点: %s", node_name)
    logger.debug("节点路径: %s", node_path)

    # 0. 检查目录权限
    perm_valid, perm_error = _check_directory_permissions(node_path)
    if not perm_valid:
        logger.error("节点目录权限检查失败: %s", perm_error)
        return False, perm_error

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
    python_exe = _python_exe_for_node(node_path, start_config, node_name)
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
    
    # 验证虚拟环境有效性
    venv_valid, venv_error = _validate_venv(python_exe)
    if not venv_valid:
        logger.error(venv_error)
        return False, venv_error

    # 直接运行 listener.py（PID 即为实际 Python 进程）
    try:
        if os.name == 'nt':
            process = subprocess.Popen(
                [python_exe, listener_py],
                cwd=node_path,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
        else:
            process = subprocess.Popen(
                [python_exe, listener_py],
                cwd=node_path, 
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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

    使用 taskkill /F /T 原子杀整棵进程树（支持任意语言）。
    核心改进：先确认进程死亡，再改状态和删 PID 文件，不撒谎。
    
    Returns:
        tuple: (success: bool, error_msg: str|None)
    """
    node_path = node_info['path']
    node_name = os.path.basename(node_path)

    process = node_info.get('process')
    pid = process.pid if process else _read_pid(node_path)

    killed = False
    if pid is not None:
        try:
            killed = _kill_process_tree(pid)
            if killed:
                logger.info("已终止进程树 PID=%d (%s)", pid, node_name)
                # 二次确认：等 0.5 秒后检查进程是否真的死了
                import time
                time.sleep(0.3)
                if not _is_pid_alive(pid):
                    logger.debug("PID=%d 确认已死亡", pid)
                else:
                    logger.warning("PID=%d 仍在运行，尝试进程扫描兜底", pid)
                    killed = False
            else:
                logger.warning("进程树终止失败 PID=%d (%s)", pid, node_name)
        except Exception as e:
            logger.warning("停止进程 PID=%d 异常: %s", pid, e)

    # 兜底：PID 方式失败，用进程扫描清理
    if not killed:
        remaining = _find_node_processes(node_path)
        if remaining:
            logger.warning("PID 方式未能终止 %s，使用进程扫描兜底清理 (发现 %d 个进程)",
                           node_name, len(remaining))
            _kill_all_node_processes(node_path)
            import time
            time.sleep(0.3)
            remaining = _find_node_processes(node_path)
            if remaining:
                logger.error("兜底清理仍失败，%s 仍有 %d 个进程存活", node_name, len(remaining))
                return False, f"无法终止进程 (剩余 {len(remaining)} 个)"
        else:
            logger.debug("未发现 %s 的残留进程", node_name)

    # 确认死亡后才改状态
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
    """检测所有节点进程状态（PID 优先，进程扫描兜底，性能安全）

    检测策略：
      running/idle/stopping → PID 存活检测（毫秒）→ 进程扫描兜底（仅 PID 死时触发）
      stopped              → 仅 PID 文件检测（发现僵尸），无 PID 则跳过

    核心改进：
      - 主路径仅 OpenProcess 调用，避免每轮 PowerShell 全量扫描
      - stopped 节点不触发昂贵的进程扫描
      - 僵尸进程（stopped 但 PID 存活）能被及时发现并修正
    """
    dead_nodes = []
    for name, info in nodes_data.items():
        current_status = info.get('status', 'stopped')
        node_path = info['path']

        # 获取最优 PID 来源
        process = info.get('process')
        pid = process.pid if (process and process.poll() is None) else _read_pid(node_path)

        # ── running / idle / stopping：PID 优先 ──
        if current_status in ('running', 'idle', 'stopping'):
            if pid and _is_pid_alive(pid):
                new_status = 'running' if _listener_has_active_child(pid) else 'idle'
                if current_status != new_status:
                    info['status'] = new_status
                    dead_nodes.append((name, None, new_status))
                _write_pid(node_path, pid)
                continue

            # PID 不存活 → 兜底进程扫描
            actual_pids = _find_node_processes(node_path)
            if actual_pids:
                actual_pid = actual_pids[0]
                _write_pid(node_path, actual_pid)
                new_status = 'running' if _listener_has_active_child(actual_pid) else 'idle'
                if current_status != new_status:
                    info['status'] = new_status
                dead_nodes.append((name, None, new_status))
            else:
                # 确认进程已退出
                info['process'] = None
                info['status'] = 'stopped'
                _delete_pid(node_path)
                dead_nodes.append((name, 0, 'stopped'))
                logger.info("节点 %s 进程已退出", name)

        # ── stopped：仅 PID 文件检测僵尸（不触发进程扫描）──
        elif current_status == 'stopped':
            if pid and _is_pid_alive(pid):
                # 僵尸！状态是 stopped 但 PID 仍存活
                new_status = 'running' if _listener_has_active_child(pid) else 'idle'
                logger.warning("检测到僵尸进程: %s PID=%d，状态从 %s 修正为 %s",
                               name, pid, current_status, new_status)
                info['status'] = new_status
                dead_nodes.append((name, None, new_status))
            # 无 PID 文件且 status=stopped → 跳过（无扫描价值）

    return dead_nodes