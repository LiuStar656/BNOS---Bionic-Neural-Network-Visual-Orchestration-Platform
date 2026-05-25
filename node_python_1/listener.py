import os
import sys
import json
import time
import subprocess
import shutil
from datetime import datetime

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(NODE_DIR, "config.json")
LOG_DIR = os.path.join(NODE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def log(msg, level="INFO"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{level}] {msg}"
    print(line)
    with open(os.path.join(LOG_DIR, "listener.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ==================== 自愈逻辑：启动前环境检测与修复 ====================
def check_and_repair_environment():
    """检测并修复虚拟环境"""
    venv_path = os.path.join(NODE_DIR, "venv")
    
    # 检测Python解释器
    if os.name == "nt":
        python_exe = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_path, "bin", "python")
    
    if not os.path.exists(python_exe):
        log("⚠️ 检测到虚拟环境异常，尝试自动修复...", "WARNING")
        
        # 清理损坏的venv
        if os.path.exists(venv_path):
            try:
                shutil.rmtree(venv_path, ignore_errors=True)
                log("✅ 已清理损坏的虚拟环境")
            except Exception as e:
                log(f"❌ 清理失败: {e}", "ERROR")
                return False
        
        # 调用python_create_node.py重建
        software_root = os.path.dirname(NODE_DIR)  # nodes目录的父目录
        create_node_script = os.path.join(software_root, "tools", "python_create_node.py")
        
        if os.path.exists(create_node_script):
            log("🔧 开始重建虚拟环境...")
            try:
                result = subprocess.run(
                    [sys.executable, create_node_script, "--repair-only", NODE_DIR],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    encoding="utf-8"
                )
                if result.returncode == 0:
                    log("✅ 虚拟环境重建成功")
                    return True
                else:
                    log(f"❌ 重建失败: {result.stderr}", "ERROR")
                    return False
            except Exception as e:
                log(f"❌ 重建异常: {e}", "ERROR")
                return False
        else:
            log("❌ 找不到python_create_node.py，无法自动修复", "ERROR")
            log("💡 请手动删除venv文件夹后重新创建节点", "WARNING")
            return False
    
    return True

# 执行环境检测
if not check_and_repair_environment():
    log("❌ 环境修复失败，程序退出", "ERROR")
    sys.exit(1)
# ==================== 自愈逻辑结束 ====================

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception as e:
    log(f"配置加载失败: {e}", "ERROR")
    exit(1)

UPPER_FILE = os.path.abspath(os.path.join(NODE_DIR, cfg["listen_upper_file"]))
OUTPUT_FILE = os.path.abspath(os.path.join(NODE_DIR, cfg["output_file"]))
NODE_NAME = cfg["node_name"]
MY_FILTER = cfg.get("filter", {})
PROCESS_FLAG = f"_processed_{NODE_NAME}"

def is_my_data(data):
    if not MY_FILTER:
        return True
    for k, v in MY_FILTER.items():
        if data.get(k) != v:
            return False
    return True

log("=" * 50)
log(f"节点启动: {NODE_NAME}")
log(f"监听: {UPPER_FILE}")
log(f"过滤: {MY_FILTER}")
log("当前环境: 独立虚拟环境（可迁移模式+自愈）")
log("=" * 50)

while True:
    try:
        if not os.path.exists(UPPER_FILE):
            time.sleep(0.2)
            continue

        with open(UPPER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get(PROCESS_FLAG):
            time.sleep(0.2)
            continue

        if not is_my_data(data):
            time.sleep(0.2)
            continue

        log("✅ 开始处理数据")

        # 【关键】只用自己虚拟环境运行 main.py
        if os.name == "nt":
            py_path = os.path.join(NODE_DIR, "venv", "Scripts", "python.exe")
        else:
            py_path = os.path.join(NODE_DIR, "venv", "bin", "python")

        res = subprocess.run(
            [py_path, os.path.join(NODE_DIR, "main.py"), json.dumps(data)],
            capture_output=True, text=True, encoding="utf-8"
        )

        output = res.stdout.strip()
        if not output:
            log("⚠️ 返回空数据")
            continue

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)

        data[PROCESS_FLAG] = True
        with open(UPPER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        log(f"✅ 处理完成: {PROCESS_FLAG}")

    except json.JSONDecodeError:
        log("❌ 数据包格式错误", "ERROR")
        time.sleep(1)
    except Exception as e:
        log(f"❌ 异常: {e}", "ERROR")
        time.sleep(1)

    time.sleep(0.2)