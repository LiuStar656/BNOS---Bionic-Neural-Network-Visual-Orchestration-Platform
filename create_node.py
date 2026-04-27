import os
import sys
import json
import subprocess

def create_clean_node_with_empty_venv(node_name):
    base_dir = os.getcwd()
    node_dir = os.path.join(base_dir, f"node_{node_name}")

    if os.path.exists(node_dir):
        print(f"❌ 节点 {node_dir} 已存在")
        return

    os.makedirs(node_dir)
    os.makedirs(os.path.join(node_dir, "logs"))

    print(f"🔧 创建空虚拟环境 venv")
    subprocess.run([sys.executable, "-m", "venv", os.path.join(node_dir, "venv")], check=True)

    with open(os.path.join(node_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write("# 在此添加节点依赖\n")

    # ==============================
    # config.json
    # ==============================
    config = {
        "node_name": f"node_{node_name}",
        "listen_upper_file": "../data/upper_data.json",
        "output_file": "./output.json",
        "filter": {},
        "output_type": ""
    }
    with open(os.path.join(node_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # ==============================
    # packet.py
    # ==============================
    packet = '''UPPER_PACKET = {"data": None}
OUTPUT_PACKET = {"code": 0, "data": None}
'''
    with open(os.path.join(node_dir, "packet.py"), "w", encoding="utf-8") as f:
        f.write(packet.strip())

    # ==============================
    # listener.py
    # ==============================
    listener = '''import os
import json
import time
import subprocess
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
        f.write(line + "\\n")

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
log("当前环境: 独立虚拟环境")
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
'''
    with open(os.path.join(node_dir, "listener.py"), "w", encoding="utf-8") as f:
        f.write(listener.strip())

    # ==============================
    # main.py
    # ==============================
    main = '''import sys
import json
import os

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(NODE_DIR, "config.json")
with open(config_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

def process(data):
    return data.get("data")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"code": -1, "error": "no input"}))
        sys.exit(1)

    input_data = json.loads(sys.argv[1])
    result = process(input_data)

    print(json.dumps({
        "code": 0,
        "type": cfg["output_type"],
        "data": result
    }, ensure_ascii=False))
'''
    with open(os.path.join(node_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write(main.strip())

    # ==============================
    # output.json
    # ==============================
    with open(os.path.join(node_dir, "output.json"), "w", encoding="utf-8") as f:
        f.write('{"code":0,"data":null}')

    # ==============================
    # 自动生成启动脚本（双击即用）
    # ==============================
    if os.name == "nt":
        start_bat = '''@echo off
cls
echo ======================================
echo        BNOS Node Starter (Windows)
echo ======================================
echo.
cd /d "%~dp0"
chcp 65001 >nul
if not exist "venv\\Scripts\\python.exe" (
    echo ❌ 虚拟环境不存在！
    pause
    exit /b 1
)
call venv\\Scripts\\activate.bat
echo ✅ 启动监听程序...
echo.
venv\\Scripts\\python.exe listener.py
echo.
echo ❌ 程序已退出
pause
'''
        with open(os.path.join(node_dir, "start.bat"), "w", encoding="utf-8") as f:
            f.write(start_bat)
    else:
        start_sh = '''#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 listener.py
'''
        with open(os.path.join(node_dir, "start.sh"), "w", encoding="utf-8") as f:
            f.write(start_sh)
        os.chmod(os.path.join(node_dir, "start.sh"), 0o755)

    print(f"\n🎉 节点创建完成：{node_dir}")
    print(f"✅ 独立虚拟环境：venv")
    print(f"✅ 双击启动：start.bat / start.sh")
    print(f"✅ 100% 环境隔离！")

# ==============================
# 运行
# ==============================
if __name__ == "__main__":
    print("==================================")
    print("    BNOS 干净节点生成器（带独立venv）")
    print("==================================")
    name = input("输入节点名称：").strip()
    if name:
        create_clean_node_with_empty_venv(name)
    else:
        print("❌ 名称不能为空")
    input("\n按回车退出")