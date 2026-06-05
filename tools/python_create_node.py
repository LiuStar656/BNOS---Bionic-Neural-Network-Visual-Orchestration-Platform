import os
import sys
import json
import shutil
import zipfile
import subprocess

def extract_node_pack(dest_dir: str, pack_file: str = None) -> bool:
    """
    解压 bnos.py.node.pack 压缩包到指定目录
    
    Args:
        dest_dir: 目标解压目录
        pack_file: 压缩包路径（可选，默认从 tools 目录查找）
        
    Returns:
        bool: 是否解压成功
    """
    if not pack_file:
        # 默认从 tools 目录查找
        pack_file = os.path.join(os.path.dirname(__file__), "bnos.py.node.pack")
        pack_file = os.path.abspath(pack_file)
    
    if not os.path.exists(pack_file):
        print(f"⚠️ 未找到压缩包: {pack_file}")
        return False
    
    if not os.path.exists(dest_dir):
        print(f"❌ 目标目录不存在: {dest_dir}")
        return False
    
    print(f"📦 从 {os.path.basename(pack_file)} 解压文件到 {dest_dir}...")
    
    try:
        with zipfile.ZipFile(pack_file, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        print("✅ 解压成功")
        return True
    except zipfile.BadZipFile:
        print(f"❌ 压缩包损坏: {pack_file}")
        return False
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return False


def create_node():
    print("=" * 50)
    print("Python 节点创建工具")
    print("=" * 50)
    
    node_name = input("请输入节点名称（name）：").strip()
    if not node_name:
        print("❌ 节点名称不能为空")
        sys.exit(1)
    
    node_dir = f"python_node_{node_name}"
    full_node_dir = os.path.join(os.getcwd(), node_dir)
    full_node_dir = os.path.abspath(full_node_dir)
    
    if os.path.exists(full_node_dir):
        overwrite = input(f"⚠️ 目录 {node_dir} 已存在，是否覆盖？(y/n)：").strip().lower()
        if overwrite != 'y':
            print("✅ 操作已取消")
            sys.exit(0)
        shutil.rmtree(full_node_dir)
    
    print(f"📁 创建节点目录: {node_dir}")
    os.makedirs(full_node_dir)
    
    print("📝 生成 config.json")
    config = {
        "node_name": f"node_python_{node_name}",
        "listen_upper_file": "../data/upper_data.json",
        "output_file": "./output.json",
        "filter": {},
        "output_type": ""
    }
    
    config_path = os.path.join(full_node_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("🔧 创建虚拟环境...")
    venv_path = os.path.join(full_node_dir, "venv")
    python_exe_path = None
    
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            [sys.executable, "-m", "venv", venv_path],
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=creationflags
        )
        if result.returncode == 0:
            print("✅ 虚拟环境创建成功")
            
            # 确定 Python 解释器路径
            if os.name == "nt":
                python_exe_path = os.path.join(venv_path, "Scripts", "python.exe")
                pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
            else:
                python_exe_path = os.path.join(venv_path, "bin", "python")
                pip_path = os.path.join(venv_path, "bin", "pip")
            
            # 确保路径是绝对路径
            python_exe_path = os.path.abspath(python_exe_path)
            
            requirements_path = os.path.join(full_node_dir, "requirements.txt")
            if os.path.exists(requirements_path):
                print("📦 安装依赖包...")
                result = subprocess.run(
                    [pip_path, "install", "-r", requirements_path],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    creationflags=creationflags
                )
                if result.returncode == 0:
                    print("✅ 依赖安装成功")
                else:
                    print(f"❌ 依赖安装失败: {result.stderr}")
        else:
            print(f"❌ 虚拟环境创建失败: {result.stderr}")
    except Exception as e:
        print(f"❌ 虚拟环境创建异常: {e}")
    
    print("📝 生成 start.json")
    start_content = {
        "nodes": [
            {
                "name": f"node_python_{node_name}",
                "path": full_node_dir,
                "python_exe": python_exe_path,
                "config": {
                    "listen_upper_file": "../data/upper_data.json",
                    "output_file": "./output.json"
                }
            }
        ]
    }
    start_path = os.path.join(full_node_dir, "start.json")
    with open(start_path, "w", encoding="utf-8") as f:
        json.dump(start_content, f, indent=2, ensure_ascii=False)
    
    extract_node_pack(full_node_dir)
    
    print("=" * 50)
    print(f"✅ 节点 {node_dir} 创建成功！")
    print(f"📂 节点路径: {full_node_dir}")
    print("=" * 50)

if __name__ == "__main__":
    create_node()