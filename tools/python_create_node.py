from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def extract_node_pack(dest_dir: Path | str, pack_file: Path | str | None = None) -> bool:
    """解压 bnos.py.node.pack 压缩包到指定目录"""
    dest_dir = Path(dest_dir)

    if pack_file is None:
        pack_file = Path(__file__).parent / "bnos.py.node.pack"
    else:
        pack_file = Path(pack_file)

    if not pack_file.exists():
        return False
    if not dest_dir.exists():
        return False

    try:
        with zipfile.ZipFile(str(pack_file), "r") as zip_ref:
            zip_ref.extractall(str(dest_dir))
        return True
    except zipfile.BadZipFile:
        return False
    except OSError:
        return False


def create_node() -> None:
    """交互式创建 Python 节点"""

    node_name = input("请输入节点名称（name）：").strip()
    if not node_name:
        sys.exit(1)

    entry_script = input("请输入入口脚本名称（默认 listener.py）：").strip()
    if not entry_script:
        entry_script = "listener.py"

    node_dir_name = f"python_node_{node_name}"
    full_node_dir = Path.cwd() / node_dir_name

    if full_node_dir.exists():
        overwrite = input(f"\u26a0\ufe0f 目录 {node_dir_name} 已存在，是否覆盖？(y/n)：").strip().lower()
        if overwrite != "y":
            sys.exit(0)
        shutil.rmtree(full_node_dir)

    full_node_dir.mkdir(parents=True)

    venv_dir = full_node_dir / "venv"

    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        result = subprocess.run(
            [sys.executable, "-m", "venv", "--copies", str(venv_dir)],
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            print(f"[警告] venv 创建失败: {result.stderr.strip()}", file=sys.stderr)
            return

        # 安装 requirements.txt（如存在）
        requirements_path = full_node_dir / "requirements.txt"
        if requirements_path.exists():
            if os.name == "nt":
                pip_path = venv_dir / "Scripts" / "pip.exe"
            else:
                pip_path = venv_dir / "bin" / "pip"

            result = subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_path)],
                capture_output=True,
                text=True,
                timeout=180,
                creationflags=creationflags,
            )
            if result.returncode != 0:
                print(f"[警告] 依赖安装失败: {result.stderr.strip()}", file=sys.stderr)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"[警告] 环境创建异常: {e}", file=sys.stderr)

    # 生成统一的 node_config.json（新格式）
    unified_config = {
        "node_name": f"node_python_{node_name}",
        "entry": entry_script,
        "python_exe": "",
        "listen_upper_file": "",
        "output_file": "./output.json",
        "filter": {},
        "output_type": "",
        "parameters": [],
        "input_ports": [],
        "output_ports": [],
        "port_mappings": {},
        "resource_limit": {"memory_mb": 1024, "cpu_percent": 100},
    }

    # 生成向后兼容的 config.json 和 start.json
    config_content = {
        "node_name": f"node_python_{node_name}",
        "listen_upper_file": "",
        "output_file": "./output.json",
        "filter": {},
        "output_type": "",
        "parameters": [],
        "input_ports": [],
        "output_ports": [],
        "port_mappings": {},
        "resource_limit": {"memory_mb": 1024, "cpu_percent": 100},
    }

    start_content = {
        "nodes": [
            {
                "name": f"node_python_{node_name}",
                "entry": entry_script,
                "python_exe": "",
                "config": {"listen_upper_file": "", "output_file": "./output.json"},
            }
        ]
    }

    # 写入统一配置文件（新格式）
    unified_path = full_node_dir / "node_config.json"
    unified_path.write_text(json.dumps(unified_config, indent=2, ensure_ascii=False), encoding="utf-8")

    # 写入向后兼容的配置文件
    config_path = full_node_dir / "config.json"
    config_path.write_text(json.dumps(config_content, indent=2, ensure_ascii=False), encoding="utf-8")

    start_path = full_node_dir / "start.json"
    start_path.write_text(json.dumps(start_content, indent=2, ensure_ascii=False), encoding="utf-8")

    extract_node_pack(full_node_dir)

    print(f"\n✅ 节点已创建: {full_node_dir}")


if __name__ == "__main__":
    create_node()
