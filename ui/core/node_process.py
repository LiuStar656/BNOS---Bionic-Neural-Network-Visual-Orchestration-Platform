"""
节点进程管理 — 统一启动/停止逻辑，消除 main_window 中 4 处重复代码
"""
import os
import subprocess
import signal
from ui.core.logger import logger


def start_node_process(node_info):
    """启动节点进程（使用节点文件夹内的启动脚本）
    
    Returns: (success, message)
    """
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
        return True, None
    except Exception as e:
        return False, str(e)


def stop_node_process(node_info, force=False):
    """停止节点进程
    
    Returns: (success, message)
    """
    process = node_info.get('process')
    if not process:
        node_info['status'] = 'stopped'
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
    return True, None


def resolve_selected_node(main_window):
    """获取选中的节点名称（优先画布，回退到节点列表）"""
    selected = main_window.canvas.get_selected_node()
    if not selected:
        from_list = main_window.node_list_panel.get_selected_nodes()
        selected = from_list[0] if from_list else None
    return selected


def check_running_processes(nodes_data):
    """检测所有运行中节点的进程是否仍在运行
    
    对每个 status='running' 且有 process 对象的节点调用 poll()，
    如果进程已退出（poll() 返回非 None），自动标记为 'stopped'。
    
    Returns: list of (node_name, exit_code) for nodes that exited
    """
    dead_nodes = []
    for name, info in nodes_data.items():
        if info.get('status') != 'running':
            continue
        process = info.get('process')
        if not process:
            info['status'] = 'stopped'
            continue
        exit_code = process.poll()
        if exit_code is not None:
            info['process'] = None
            info['status'] = 'stopped'
            dead_nodes.append((name, exit_code))
            logger.info("节点 %s 进程已退出 (exit code: %s)", name, exit_code)
    return dead_nodes

