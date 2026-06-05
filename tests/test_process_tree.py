"""
进程树终止机制测试脚本

测试场景：
1. 启动一个 Python 主进程
2. 主进程创建 Node.js 子进程
3. Node.js 子进程创建 Java 孙进程
4. 调用进程树终止机制
5. 验证所有进程都被终止

使用方法：
1. 运行此脚本启动测试进程树
2. 在 GUI 中停止节点
3. 检查所有进程是否都被终止
"""

import os
import sys
import time
import subprocess
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.core.node_process import _get_process_tree, _kill_process_tree


def create_test_process_tree():
    """创建测试进程树"""
    print("=" * 60)
    print("创建测试进程树")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="process_tree_test_")
    print(f"临时目录: {temp_dir}")
    
    # 创建 Python 主进程脚本
    main_script = os.path.join(temp_dir, "main.py")
    with open(main_script, "w", encoding="utf-8") as f:
        f.write("""
import subprocess
import time
import os
import sys

print(f"[主进程] PID={os.getpid()} 启动")

# 创建子进程（Python 子进程）
child_script = os.path.join(os.path.dirname(__file__), "child.py")
child = subprocess.Popen([sys.executable, child_script])
print(f"[主进程] 创建子进程 PID={child.pid}")

# 等待子进程
try:
    child.wait()
except KeyboardInterrupt:
    child.terminate()
    child.wait()

print("[主进程] 退出")
""")
    
    # 创建子进程脚本
    child_script = os.path.join(temp_dir, "child.py")
    with open(child_script, "w", encoding="utf-8") as f:
        f.write("""
import subprocess
import time
import os
import sys

print(f"[子进程] PID={os.getpid()} 启动")

# 创建孙进程（Python 孙进程）
grandchild_script = os.path.join(os.path.dirname(__file__), "grandchild.py")
grandchild = subprocess.Popen([sys.executable, grandchild_script])
print(f"[子进程] 创建孙进程 PID={grandchild.pid}")

# 等待孙进程
try:
    grandchild.wait()
except KeyboardInterrupt:
    grandchild.terminate()
    grandchild.wait()

print("[子进程] 退出")
""")
    
    # 创建孙进程脚本
    grandchild_script = os.path.join(temp_dir, "grandchild.py")
    with open(grandchild_script, "w", encoding="utf-8") as f:
        f.write("""
import time
import os

print(f"[孙进程] PID={os.getpid()} 启动")

# 持续运行
while True:
    time.sleep(1)
    print(f"[孙进程] PID={os.getpid()} 运行中...")
""")
    
    # 启动主进程
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    main_process = subprocess.Popen(
        [sys.executable, main_script],
        creationflags=creationflags,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"主进程 PID: {main_process.pid}")
    
    # 等待进程树建立
    time.sleep(2)
    
    return main_process, temp_dir


def test_process_tree():
    """测试进程树终止机制"""
    print("\n" + "=" * 60)
    print("测试进程树终止机制")
    print("=" * 60)
    
    # 创建测试进程树
    main_process, temp_dir = create_test_process_tree()
    root_pid = main_process.pid
    
    # 查询进程树
    print(f"\n查询进程树 (根 PID={root_pid}):")
    all_pids = _get_process_tree(root_pid)
    print(f"进程树包含 {len(all_pids)} 个进程: {all_pids}")
    
    # 验证进程是否存活
    print("\n验证进程存活状态:")
    for pid in all_pids:
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                alive = str(pid) in result.stdout
            else:
                os.kill(pid, 0)
                alive = True
        except (ProcessLookupError, OSError):
            alive = False
        
        print(f"  PID {pid}: {'存活' if alive else '已终止'}")
    
    # 等待用户确认
    print("\n" + "-" * 60)
    input("按 Enter 键开始终止进程树...")
    
    # 终止进程树
    print(f"\n终止进程树 (根 PID={root_pid}):")
    killed_count = _kill_process_tree(root_pid)
    print(f"成功终止 {killed_count} 个进程")
    
    # 等待进程终止
    time.sleep(1)
    
    # 验证进程是否都已终止
    print("\n验证进程终止状态:")
    all_terminated = True
    for pid in all_pids:
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                alive = str(pid) in result.stdout
            else:
                os.kill(pid, 0)
                alive = True
        except (ProcessLookupError, OSError):
            alive = False
        
        status = "存活 ❌" if alive else "已终止 ✅"
        print(f"  PID {pid}: {status}")
        if alive:
            all_terminated = False
    
    # 清理临时目录
    try:
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")
    except Exception as e:
        print(f"\n清理临时目录失败: {e}")
    
    # 输出结果
    print("\n" + "=" * 60)
    if all_terminated:
        print("✅ 测试通过：所有进程都已终止")
    else:
        print("❌ 测试失败：部分进程仍在运行")
    print("=" * 60)
    
    return all_terminated


def interactive_test():
    """交互式测试：只创建进程树，不自动终止"""
    print("\n" + "=" * 60)
    print("交互式测试模式")
    print("=" * 60)
    print("此模式将创建进程树并等待，您可以手动测试终止功能")
    print()
    
    # 创建测试进程树
    main_process, temp_dir = create_test_process_tree()
    root_pid = main_process.pid
    
    # 查询进程树
    print(f"\n进程树信息:")
    all_pids = _get_process_tree(root_pid)
    print(f"根进程 PID: {root_pid}")
    print(f"进程树包含 {len(all_pids)} 个进程: {all_pids}")
    
    print("\n" + "-" * 60)
    print("测试方法:")
    print("1. 打开任务管理器，查看上述 PID 的进程")
    print("2. 在 GUI 中停止节点，或手动调用 _kill_process_tree()")
    print("3. 检查所有进程是否都被终止")
    print("-" * 60)
    
    print(f"\n进程正在运行中...")
    print(f"临时目录: {temp_dir}")
    print(f"按 Ctrl+C 退出并清理")
    
    try:
        main_process.wait()
    except KeyboardInterrupt:
        print("\n收到中断信号，正在清理...")
        _kill_process_tree(root_pid)
        print("已终止进程树")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="进程树终止机制测试")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="交互式测试模式（不自动终止）")
    args = parser.parse_args()
    
    if args.interactive:
        interactive_test()
    else:
        test_process_tree()
