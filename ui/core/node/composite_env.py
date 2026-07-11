"""
ui/core/composite_env.py
复合节点虚拟环境管理 — 创建 / 合并依赖 / 路径解析。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ui.core.i18n.i18n import t
from ui.core.i18n.translation_keys import TK


def comp_venv_path(project_path: str, comp_id: str, display_name: str = "") -> str:
    """获取复合节点的 venv 目录路径。

    venv 路径: nodes/{display_name}_venv/（无命名时使用 nodes/__comp__{comp_id}_venv/）
    """
    if display_name:
        return str(Path(project_path) / "nodes" / f"{display_name}_venv")
    return str(Path(project_path) / "nodes" / f"__comp__{comp_id}_venv")


def get_python_exe(comp_dir: str) -> str | None:
    """获取复合节点 venv 中的 Python 解释器路径。"""
    if os.name == "nt":
        py = Path(comp_dir) / "venv" / "Scripts" / "python.exe"
    else:
        py = Path(comp_dir) / "venv" / "bin" / "python3"
    return str(py) if py.exists() else None


def merge_requirements(
    project_path: str, comp_id: str, display_name: str, node_names: list[str], nodes_data: dict, logger
) -> tuple[bool, str]:
    """合并子节点的 requirements.txt 到复合节点独立 venv。

    复合节点 orchestrator 在独立 venv 中运行，需要所有子节点依赖。
    """
    merged = set()
    nodes_with_reqs = []
    project = Path(project_path)
    for n in node_names:
        node_data = nodes_data.get(n, {})
        node_path_str = node_data.get("path", "")
        if not node_path_str:
            node_path = project / "nodes" / n
        else:
            node_path = Path(node_path_str)
        req_path = node_path / "requirements.txt"
        if req_path.is_file():
            try:
                with req_path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            merged.add(line)
                nodes_with_reqs.append(n)
            except Exception as e:
                logger.warning("读取 %s 的 requirements.txt 失败: %s", n, e)

    # 复合节点独立 venv 路径
    comp_dir = Path(comp_venv_path(project_path, comp_id, display_name))
    venv_dir = comp_dir / "venv"
    if os.name == "nt":
        python_exe = venv_dir / "Scripts" / "python.exe"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        python_exe = venv_dir / "bin" / "python3"
        pip_exe = venv_dir / "bin" / "pip"

    # 创建 venv
    try:
        if not python_exe.exists():
            comp_dir.mkdir(parents=True, exist_ok=True)
            logger.info("为复合节点 %s 创建独立 venv: %s", comp_id, venv_dir)
            result = subprocess.run(
                [sys.executable, "-m", "venv", "--copies", str(venv_dir)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(project),
            )
            if result.returncode != 0:
                logger.error("创建复合节点 venv 失败: %s", result.stderr[-300:])
                import shutil

                shutil.rmtree(comp_dir, ignore_errors=True)
                return False, t(TK.COMPOSITE_VENV_CREATE_FAILED).format(error=result.stderr[-200:])
    except subprocess.TimeoutExpired:
        return False, t(TK.COMPOSITE_VENV_TIMEOUT)
    except Exception as e:
        logger.error("创建复合节点 venv 异常: %s", e)
        import shutil

        shutil.rmtree(comp_dir, ignore_errors=True)
        return False, t(TK.COMPOSITE_VENV_ERROR).format(error=str(e))

    if not merged:
        logger.info("子节点均无 requirements.txt，venv 已就绪（空依赖）")
        return True, ""

    # 安装合并依赖
    merged_path = project / ".composite_reqs_tmp.txt"
    try:
        with merged_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(sorted(merged)) + "\n")

        logger.info(
            "复合节点 %s: 合并 %d 个子节点的依赖 (%d 个包): %s",
            comp_id,
            len(nodes_with_reqs),
            len(merged),
            ", ".join(sorted(merged)),
        )
        result = subprocess.run(
            [str(pip_exe), "install", "-r", str(merged_path)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(project),
        )
        if result.returncode != 0:
            logger.error("pip install 合并依赖失败: %s", result.stderr[-500:])
            return False, t(TK.COMPOSITE_DEPS_INSTALL_FAILED).format(error=result.stderr[-300:])
        logger.info("复合节点 %s 依赖合并成功", comp_id)
        return True, ""
    except subprocess.TimeoutExpired:
        return False, t(TK.COMPOSITE_DEPS_INSTALL_TIMEOUT)
    except Exception as e:
        logger.error("合并依赖异常: %s", e)
        return False, t(TK.COMPOSITE_DEPS_INSTALL_ERROR).format(error=str(e))
    finally:
        try:
            merged_path.unlink()
        except OSError:
            pass


def remove_comp_env(project_path: str, comp_id: str, display_name: str, logger) -> None:
    """删除复合节点的独立 venv 目录。"""
    import shutil

    comp_dir = Path(comp_venv_path(project_path, comp_id, display_name))
    if comp_dir.is_dir():
        try:
            shutil.rmtree(comp_dir, ignore_errors=True)
            logger.info("已删除复合节点 venv: %s", comp_dir)
        except Exception as e:
            logger.warning("删除复合节点 venv 失败: %s", e)
