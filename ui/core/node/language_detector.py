"""
Node Language Detector

Detects the programming language of a node by inspecting its file system structure.
Used by composite node factory to route creation to the correct builder.
"""

from __future__ import annotations

import json
from pathlib import Path


class LanguageDetector:
    """
    Detects the programming language of a BNOS node.

    Detection priority (high to low):
      1. node_config.json 'entry' field extension（统一配置）
      2. Signature files (requirements.txt, Cargo.toml, package.json, etc.)
      3. Main source file existence check
    """

    # Language signature files: filename -> language
    SIGNATURE_FILES = {
        "requirements.txt": "Python",
        "Cargo.toml": "Rust",
        "package.json": "Node.js",
        "go.mod": "Go",
        "CMakeLists.txt": "C++",
    }

    # Entry extension -> language mapping
    ENTRY_EXT_MAP = {
        ".py": "Python",
        ".rs": "Rust",
        ".js": "Node.js",
        ".go": "Go",
        ".java": "Java",
        ".cpp": "C++",
        ".sh": "Shell",
        ".bat": "Shell",
    }

    # Main file checks (fallback)
    MAIN_FILE_CHECKS = [
        ("main.py", "Python"),
        ("main.js", "Node.js"),
        ("main.go", "Go"),
        ("Main.java", "Java"),
        ("main.cpp", "C++"),
        ("src/main.rs", "Rust"),
        ("main.sh", "Shell"),
        ("listener.py", "Python"),
    ]

    @staticmethod
    def detect(node_path: str) -> str:
        """
        Detect the language of a single node.

        Args:
            node_path: Absolute path to the node directory

        Returns:
            "Python" | "Rust" | "Node.js" | "Go" | "Java" | "C++" | "Shell" | "Unknown"
        """
        if not node_path or not Path(node_path).is_dir():
            return "Unknown"

        # 1. Check node_config.json entry field (unified config)
        unified_json = Path(node_path) / "node_config.json"
        if unified_json.is_file():
            try:
                with unified_json.open(encoding="utf-8") as f:
                    data = json.load(f)
                entry = data.get("entry", "")
                if entry:
                    ext = Path(entry).suffix
                    lang = LanguageDetector.ENTRY_EXT_MAP.get(ext.lower())
                    if lang:
                        return lang
            except (json.JSONDecodeError, OSError):
                pass

        # 2. Check signature files
        np = Path(node_path)
        for filename, lang in LanguageDetector.SIGNATURE_FILES.items():
            if (np / filename).is_file():
                return lang

        # 3. Check main files
        for path_rel, lang in LanguageDetector.MAIN_FILE_CHECKS:
            if (np / path_rel).is_file():
                return lang

        return "Unknown"

    @staticmethod
    def detect_multi(node_paths: list[str]) -> str:
        """
        Detect the language for multiple nodes. All must be the same language.

        Args:
            node_paths: List of absolute paths to node directories

        Returns:
            Language string if all nodes share the same language,
            or a collision string like "Python|Rust" if mixed
        """
        langs = set()
        for p in node_paths:
            langs.add(LanguageDetector.detect(p))

        if len(langs) == 1:
            return langs.pop()
        return "|".join(sorted(langs))

    @staticmethod
    def is_python_node(node_path: str) -> bool:
        """Convenience: check if a node is Python."""
        return LanguageDetector.detect(node_path) == "Python"

    @staticmethod
    def is_rust_node(node_path: str) -> bool:
        """Convenience: check if a node is Rust."""
        return LanguageDetector.detect(node_path) == "Rust"
