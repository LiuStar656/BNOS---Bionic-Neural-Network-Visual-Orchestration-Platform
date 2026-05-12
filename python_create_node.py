import os
import sys
import json
import subprocess
import shutil

def create_portable_venv(node_dir):
    """
    创建可迁移的虚拟环境
    优先使用 virtualenv 工具，回退到标准 venv
    """
    venv_path = os.path.join(node_dir, "venv")
    
    # 方法1: 尝试使用 virtualenv（如果已安装）
    try:
        print("🔧 尝试使用 virtualenv 创建可迁移环境...")
        result = subprocess.run(
            [sys.executable, "-m", "virtualenv", "--copies", venv_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("✅ 使用 virtualenv 创建成功（--copies 模式）")
            return True
        else:
            print(f"⚠️ virtualenv 失败: {result.stderr}")
    except FileNotFoundError:
        print("⚠️ virtualenv 未安装，使用标准 venv")
    except subprocess.TimeoutExpired:
        print("⚠️ virtualenv 超时，使用标准 venv")
    except Exception as e:
        print(f"⚠️ virtualenv 异常: {e}，使用标准 venv")
    
    # 方法2: 使用标准 venv + 后处理
    print("🔧 使用标准 venv 创建环境...")
    try:
        # Python 3.12+ 可以使用 --copies 参数
        if sys.version_info >= (3, 12):
            result = subprocess.run(
                [sys.executable, "-m", "venv", "--copies", venv_path],
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ 使用 venv --copies 创建成功")
        else:
            # Python 3.11 及以下
            result = subprocess.run(
                [sys.executable, "-m", "venv", venv_path],
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ 使用标准 venv 创建成功")
            
            # 后处理：修改 pyvenv.cfg 使其更可迁移
            fix_pyvenv_cfg(venv_path)
        
        return True
    except Exception as e:
        print(f"❌ 创建虚拟环境失败: {e}")
        return False

def fix_pyvenv_cfg(venv_path):
    """
    修复 pyvenv.cfg 文件，添加可迁移标记
    """
    cfg_path = os.path.join(venv_path, "pyvenv.cfg")
    if not os.path.exists(cfg_path):
        return
    
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 检查是否已经修复过
        already_fixed = any('BNOS portable' in line for line in lines)
        if already_fixed:
            return
        
        # 添加注释说明这是 BNOS 管理的可迁移环境
        with open(cfg_path, 'a', encoding='utf-8') as f:
            f.write('\n# BNOS portable mode - environment can be moved\n')
            f.write('# If moved, delete venv folder and recreate node\n')
        
        print("✅ 已标记为可迁移模式")
    except Exception as e:
        print(f"⚠️ 修复 pyvenv.cfg 失败: {e}")

def auto_repair_venv(node_dir):
    """
    自动检测并修复虚拟环境（自愈逻辑）
    在节点启动时调用，检测venv是否缺失/损坏，自动重建
    """
    venv_path = os.path.join(node_dir, "venv")
    
    # 检测1: venv目录是否存在
    if not os.path.exists(venv_path):
        print("⚠️ 检测到虚拟环境缺失，开始自动重建...")
        return create_portable_venv(node_dir)
    
    # 检测2: Python解释器是否存在
    if os.name == "nt":
        python_exe = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_path, "bin", "python")
    
    if not os.path.exists(python_exe):
        print("⚠️ 检测到Python解释器缺失，开始自动重建...")
        # 删除损坏的venv
        try:
            shutil.rmtree(venv_path, ignore_errors=True)
            print("✅ 已清理损坏的虚拟环境")
        except Exception as e:
            print(f"❌ 清理失败: {e}")
            return False
        return create_portable_venv(node_dir)
    
    # 检测3: 尝试运行Python，检查是否真正可用
    try:
        result = subprocess.run(
            [python_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("⚠️ 检测到虚拟环境损坏，开始自动重建...")
            shutil.rmtree(venv_path, ignore_errors=True)
            return create_portable_venv(node_dir)
    except Exception:
        print("⚠️ 检测到虚拟环境异常，开始自动重建...")
        shutil.rmtree(venv_path, ignore_errors=True)
        return create_portable_venv(node_dir)
    
    # 环境正常
    print("✅ 虚拟环境检测通过")
    return True

def install_requirements(node_dir):
    """
    安装requirements.txt中的依赖
    """
    req_file = os.path.join(node_dir, "requirements.txt")
    if not os.path.exists(req_file):
        return True
    
    # 检查是否有实际依赖（跳过注释和空行）
    has_deps = False
    with open(req_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                has_deps = True
                break
    
    if not has_deps:
        return True
    
    print("📦 检测到依赖项，开始安装...")
    
    if os.name == "nt":
        python_exe = os.path.join(node_dir, "venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join(node_dir, "venv", "bin", "python")
    
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "-r", req_file],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        if result.returncode == 0:
            print("✅ 依赖安装成功")
            return True
        else:
            print(f"❌ 依赖安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 依赖安装异常: {e}")
        return False

def create_clean_node_with_empty_venv(node_name):
    base_dir = os.getcwd()
    node_dir = os.path.join(base_dir, f"node_python_{node_name}")

    if os.path.exists(node_dir):
        print(f"❌ 节点 {node_dir} 已存在")
        return

    os.makedirs(node_dir)
    os.makedirs(os.path.join(node_dir, "logs"))

    # 🔧 使用改进的可迁移虚拟环境创建方法
    print(f"🔧 创建可迁移虚拟环境 venv")
    success = create_portable_venv(node_dir)
    
    if not success:
        print(f"❌ 虚拟环境创建失败，终止节点创建")
        import shutil
        shutil.rmtree(node_dir, ignore_errors=True)
        return

    with open(os.path.join(node_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write("# 在此添加节点依赖\\n")

    # ==============================
    # config.json
    # ==============================
    config = {
        "node_name": f"node_python_{node_name}",
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
        f.write(line + "\\n")

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
        create_node_script = os.path.join(software_root, "..", "python_create_node.py")
        
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
    # 自动生成启动脚本（双击即用，支持可迁移+自愈）
    # ==============================
    if os.name == "nt":
        start_bat = '''@echo off
cls
chcp 65001 >nul
echo ======================================
echo        BNOS Node Starter (Windows)
echo ======================================
echo.
cd /d "%~dp0"

REM ==================== 环境检测与自愈 ====================
echo 🔍 检测虚拟环境状态...

if not exist "venv\\Scripts\\python.exe" (
    echo ⚠️ 检测到虚拟环境缺失或损坏
    echo.
    echo 🔧 开始自动修复...
    echo.
    
    REM 调用python_create_node.py进行修复
    if exist "..\\..\\python_create_node.py" (
        python ..\\..\\python_create_node.py --repair-only "%CD%"
        if errorlevel 1 (
            echo.
            echo ❌ 自动修复失败
            echo 💡 请手动删除venv文件夹后重新创建节点
            pause
            exit /b 1
        )
        echo.
        echo ✅ 虚拟环境重建成功
    ) else (
        echo ❌ 找不到python_create_node.py，无法自动修复
        echo 💡 请手动删除venv文件夹后重新创建节点
        pause
        exit /b 1
    )
)

REM ==================== 启动节点 ====================
echo 🔍 检测到虚拟环境正常
echo.
echo 🔧 启动节点...
echo.

python listener.py

echo.
echo ✅ 节点已停止
pause
'''
        with open(os.path.join(node_dir, "start.bat"), "w", encoding="utf-8") as f:
            f.write(start_bat.strip())
    
    else:
        start_sh = '''#!/bin/bash

echo "======================================"
echo "       BNOS Node Starter (Linux/Mac)"
echo "======================================"
echo ""

cd "$(dirname "$0")"

# ==================== 环境检测与自愈 ====================
echo "🔍 检测虚拟环境状态..."

if [ ! -f "venv/bin/python" ]; then
    echo "⚠️ 检测到虚拟环境缺失或损坏"
    echo ""
    echo "🔧 开始自动修复..."
    echo ""
    
    # 调用python_create_node.py进行修复
    if [ -f "../../python_create_node.py" ]; then
        python3 ../../python_create_node.py --repair-only "$(pwd)"
        if [ $? -ne 0 ]; then
            echo ""
            echo "❌ 自动修复失败"
            echo "💡 请手动删除venv文件夹后重新创建节点"
            read -p "按回车键退出..."
            exit 1
        fi
        echo ""
        echo "✅ 虚拟环境重建成功"
    else
        echo "❌ 找不到python_create_node.py，无法自动修复"
        echo "💡 请手动删除venv文件夹后重新创建节点"
        exit 1
    fi
else
    echo "✅ 虚拟环境检测通过"
fi

echo ""
# ==================== 依赖安装检查 ====================
if [ -f "requirements.txt" ]; then
    if grep -v "^#" requirements.txt | grep -q "[^[:space:]]"; then
        echo "📦 检测到依赖项，检查安装状态..."
        venv/bin/python -c "import pkg_resources; pkg_resources.working_set.require(open('requirements.txt').read().splitlines())" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "🔧 开始安装依赖..."
            venv/bin/python -m pip install -r requirements.txt
            if [ $? -eq 0 ]; then
                echo "✅ 依赖安装成功"
            else
                echo "⚠️ 依赖安装失败，但将继续启动"
            fi
        else
            echo "✅ 依赖已安装"
        fi
    fi
fi

source venv/bin/activate
python3 listener.py
'''
        with open(os.path.join(node_dir, "start.sh"), "w", encoding="utf-8") as f:
            f.write(start_sh.strip())
        os.chmod(os.path.join(node_dir, "start.sh"), 0o755)


# ==================== 独立运行入口 ====================
def main():
    """
    独立运行模式：交互式创建节点或修复环境
    
    用法：
        python python_create_node.py                                    # 交互模式
        python python_create_node.py <节点名称>                         # 直接创建
        python python_create_node.py --repair-only <节点目录路径>       # 仅修复虚拟环境
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="BNOS Python 节点创建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python python_create_node.py                    # 进入交互模式
  python python_create_node.py my_node            # 直接创建名为 my_node 的节点
  python python_create_node.py --repair-only ./node_python_my_node  # 修复指定节点的虚拟环境
        """
    )
    
    parser.add_argument(
        'node_name',
        nargs='?',
        help='节点名称（将创建 node_python_<节点名称> 目录）'
    )
    
    parser.add_argument(
        '--repair-only',
        metavar='NODE_DIR',
        help='仅修复指定节点目录的虚拟环境（不创建新节点）'
    )
    
    args = parser.parse_args()
    
    # 模式1: 仅修复虚拟环境
    if args.repair_only:
        node_dir = os.path.abspath(args.repair_only)
        
        if not os.path.exists(node_dir):
            print(f"❌ 节点目录不存在: {node_dir}")
            sys.exit(1)
        
        print(f"🔧 开始修复节点: {node_dir}")
        success = auto_repair_venv(node_dir)
        
        if success:
            # 尝试安装依赖
            install_requirements(node_dir)
            print("✅ 节点修复完成！")
            sys.exit(0)
        else:
            print("❌ 节点修复失败")
            sys.exit(1)
    
    # 模式2: 提供了节点名称参数，直接创建
    elif args.node_name:
        node_name = args.node_name
        
        # 验证节点名称
        if not node_name or not node_name.strip():
            print("❌ 节点名称不能为空")
            sys.exit(1)
        
        # 清理节点名称（只允许字母、数字、下划线、连字符）
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', node_name):
            print("❌ 节点名称只能包含字母、数字、下划线和连字符")
            sys.exit(1)
        
        print(f"🚀 开始创建节点: {node_name}")
        print("=" * 60)
        
        try:
            create_clean_node_with_empty_venv(node_name)
            
            node_dir = os.path.join(os.getcwd(), f"node_python_{node_name}")
            
            if os.path.exists(node_dir):
                print("=" * 60)
                print(f"✅ 节点创建成功！")
                print(f"📁 节点目录: {node_dir}")
                print(f"💡 使用方法:")
                print(f"   1. 进入节点目录: cd {node_dir}")
                print(f"   2. 编辑 main.py 实现业务逻辑")
                print(f"   3. 如需依赖，编辑 requirements.txt")
                print(f"   4. 双击 start.bat (Windows) 或运行 ./start.sh (Linux/Mac)")
                print("=" * 60)
                sys.exit(0)
            else:
                print("❌ 节点创建失败")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ 节点创建异常: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # 模式3: 没有提供参数，进入交互模式
    else:
        print("=" * 60)
        print("   BNOS Python 节点创建工具 - 交互模式")
        print("=" * 60)
        print()
        
        while True:
            try:
                # 获取用户输入
                node_name = input("📝 请输入节点名称（输入 'q' 退出）: ").strip()
                
                # 检查是否退出
                if node_name.lower() in ['q', 'quit', 'exit']:
                    print("👋 再见！")
                    sys.exit(0)
                
                # 验证输入
                if not node_name:
                    print("⚠️  节点名称不能为空，请重新输入\n")
                    continue
                
                # 验证节点名称格式
                import re
                if not re.match(r'^[a-zA-Z0-9_-]+$', node_name):
                    print("⚠️  节点名称只能包含字母、数字、下划线和连字符，请重新输入\n")
                    continue
                
                # 检查节点是否已存在
                node_dir = os.path.join(os.getcwd(), f"node_python_{node_name}")
                if os.path.exists(node_dir):
                    confirm = input(f"⚠️  节点 '{node_name}' 已存在，是否覆盖？(y/n): ").strip().lower()
                    if confirm != 'y':
                        print("❌ 已取消创建\n")
                        continue
                    
                    # 删除已存在的节点
                    try:
                        shutil.rmtree(node_dir)
                        print(f"✅ 已删除旧节点\n")
                    except Exception as e:
                        print(f"❌ 删除失败: {e}\n")
                        continue
                
                # 创建节点
                print(f"\n🚀 开始创建节点: {node_name}")
                print("-" * 60)
                
                create_clean_node_with_empty_venv(node_name)
                
                if os.path.exists(node_dir):
                    print("-" * 60)
                    print(f"✅ 节点创建成功！")
                    print(f"📁 节点目录: {node_dir}")
                    print(f"💡 下一步:")
                    print(f"   1. 进入节点目录: cd {node_dir}")
                    print(f"   2. 编辑 main.py 实现业务逻辑")
                    print(f"   3. 如需依赖，编辑 requirements.txt")
                    print(f"   4. 双击 start.bat (Windows) 或运行 ./start.sh (Linux/Mac)")
                    print("=" * 60)
                    print()
                    
                    # 询问是否继续创建
                    again = input("是否继续创建其他节点？(y/n): ").strip().lower()
                    if again != 'y':
                        print("👋 再见！")
                        sys.exit(0)
                    print()
                else:
                    print("❌ 节点创建失败\n")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，再见！")
                sys.exit(0)
            except EOFError:
                print("\n\n👋 输入结束，再见！")
                sys.exit(0)
            except Exception as e:
                print(f"❌ 发生错误: {e}")
                import traceback
                traceback.print_exc()
                print()


if __name__ == "__main__":
    main()
