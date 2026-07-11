"""
Composite Node Factory

Routes composite node creation to the appropriate language-specific builder.
Currently supports Python; extensible to Rust, Node.js, etc.
"""
import os
import json
import uuid
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from ui.core.logger import logger
from ui.core.i18n.i18n import t
from ui.core.i18n.translation_keys import TK
from ui.core.node.language_detector import LanguageDetector


class CompositeNodeFactory:
    """
    Factory that selects the right builder based on node language.

    Usage:
        factory = CompositeNodeFactory(project_path, canvas, group_manager)
        ok, msg, comp_id = factory.build(node_names, display_name, nodes_data)
    """

    def __init__(self, project_path: str, canvas=None, group_manager=None):
        self._project_path = project_path
        self._canvas = canvas
        self._group_manager = group_manager

    def build(self, node_names: List[str], display_name: str,
              nodes_data: dict) -> Tuple[bool, str, Optional[str]]:
        """Build a composite node. Returns (ok, msg, comp_id)."""
        # 1. Detect language
        node_paths = []
        for n in node_names:
            nd = nodes_data.get(n, {})
            path = nd.get('path', '') or os.path.join(self._project_path, "nodes", n)
            node_paths.append(path)

        lang_result = LanguageDetector.detect_multi(node_paths)
        if "|" in lang_result:
            # Mixed languages — map each node to its language for error message
            node_langs = {}
            for n in node_names:
                nd = nodes_data.get(n, {})
                path = nd.get('path', '') or os.path.join(self._project_path, "nodes", n)
                node_langs[n] = LanguageDetector.detect(path)
            lang_summary = {}
            for n, l in node_langs.items():
                lang_summary.setdefault(l, []).append(n)
            msg_parts = [f"{lang}({'、'.join(names)})" for lang, names in lang_summary.items()]
            return False, t(TK.COMPOSITE_LANGUAGE_MISMATCH).format(details=" | ".join(msg_parts)), None

        if lang_result == "Unknown":
            return False, t(TK.COMPOSITE_UNKNOWN_LANGUAGE).format(nodes=", ".join(node_names)), None

        # 2. Route to builder
        comp_id = f"composite_{uuid.uuid4().hex[:8]}"

        if lang_result == "Python":
            builder = PythonCompositeBuilder(
                self._project_path, self._canvas, self._group_manager
            )
        else:
            return False, t(TK.COMPOSITE_UNKNOWN_LANGUAGE).format(
                nodes=f"{lang_result}({'、'.join(node_names)})"
            ), None

        # 3. Build language-specific assets
        ok, msg = builder.build(comp_id, display_name, node_names, nodes_data)
        if not ok:
            return False, msg, None

        return True, t(TK._COMPOSITE_COMPRESSED).format(n=len(node_names)), comp_id


class PythonCompositeBuilder:
    """
    Builder for Python-language composite nodes.

    Handles:
      - Requirements merging
      - Isolated venv creation
      - Orchestrator script generation
    """

    def __init__(self, project_path: str, canvas=None, group_manager=None):
        self._project_path = project_path
        self._canvas = canvas
        self._group_manager = group_manager

    def build(self, comp_id: str, display_name: str,
              node_names: List[str], nodes_data: dict) -> Tuple[bool, str]:
        """Build Python-specific assets for a composite node.

        Returns (ok, msg). On success, the composite data is stored for later use.
        """
        # Merge requirements and create isolated venv
        ok, msg = self._merge_requirements(
            comp_id, display_name, node_names, nodes_data
        )
        if not ok:
            return False, msg

        return True, msg

    def generate_orchestrator(self, comp_id: str, node_names: List[str],
                              dag: List[dict], ports: dict) -> str:
        """Generate orchestrator.py for the composite node."""
        from ui.core.node.composite_orchestrator import render_orchestrator_script

        node_modules = []
        for name in node_names:
            node_modules.append({
                "name": name,
                "module": f"nodes.{name}.main",
                "path": f"./nodes/{name}"
            })

        code = render_orchestrator_script(
            comp_id=comp_id,
            node_modules=node_modules,
            dag=dag,
            external_ports=ports
        )
        orch_path = os.path.join(self._project_path, f"orchestrator_{comp_id}.py")
        with open(orch_path, 'w', encoding='utf-8') as f:
            f.write(code)
        return orch_path

    def _merge_requirements(self, comp_id: str, display_name: str,
                            node_names: List[str], nodes_data: dict
                            ) -> Tuple[bool, str]:
        """Merge child node requirements into composite isolated venv."""
        from ui.core.node.composite_env import (
            merge_requirements as _merge,
            comp_venv_path
        )
        return _merge(
            self._project_path, comp_id, display_name,
            node_names, nodes_data, logger
        )
