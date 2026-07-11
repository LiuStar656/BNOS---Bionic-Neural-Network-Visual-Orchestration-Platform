"""
Node Language Detector

Detects the programming language of a node by inspecting its file system structure.
Used by composite node factory to route creation to the correct builder.
"""
import os
import json
from typing import List


class LanguageDetector:
    """
    Detects the programming language of a BNOS node.

    Detection priority (high to low):
      1. start.json 'entry' field extension
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
        if not node_path or not os.path.isdir(node_path):
            return "Unknown"

        # 1. Check start.json entry field
        start_json = os.path.join(node_path, "start.json")
        if os.path.isfile(start_json):
            try:
                with open(start_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                nodes_list = data.get("nodes", [])
                if isinstance(nodes_list, list) and nodes_list:
                    entry = nodes_list[0].get("entry", "")
                    if entry:
                        _, ext = os.path.splitext(entry)
                        lang = LanguageDetector.ENTRY_EXT_MAP.get(ext.lower())
                        if lang:
                            return lang
            except (json.JSONDecodeError, OSError):
                pass

        # 2. Check signature files
        for filename, lang in LanguageDetector.SIGNATURE_FILES.items():
            if os.path.isfile(os.path.join(node_path, filename)):
                return lang

        # 3. Check main files
        for path_rel, lang in LanguageDetector.MAIN_FILE_CHECKS:
            if os.path.isfile(os.path.join(node_path, path_rel)):
                return lang

        return "Unknown"

    @staticmethod
    def detect_multi(node_paths: List[str]) -> str:
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
