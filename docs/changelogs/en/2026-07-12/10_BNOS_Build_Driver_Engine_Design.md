# 10 BNOS Build Driver Engine Design

## Overview

Redesigned the BNOS Build approach: from "copy files to new directory" (export mode) to "inject files into project root" (driver layer mode). The driver engine is fully isolated from source files, independently deletable and updatable.

---

## I. Concept Upgrade

| Before | After |
|------|------|
| `bnos build pipeline.json --output ./dist` | `bnos build` |
| Export entire project to new folder | Inject 5 driver files into project root |
| Engine = part of project | **Engine = pluggable driver layer** (like USB driver) |

---

## II. Isolation Principle

```
Project root/
├── nodes/              ← Source files (engine never touches)
│   ├── preprocess/
│   │   └── main.py
│   └── inference/
│       └── main.py
│
├── bnos_runtime/       ← Driver engine (pure injection)
│   ├── engine.py       ← Entry: type dispatch
│   ├── pipeline.json   ← Auto-generated
│   ├── standalone_runner.py
│   ├── composite_runner.py
│   └── venv_resolver.py
│
├── .gitignore          ← Recommend ignoring bnos_runtime/
└── pipeline.json       ← Canvas topology definition
```

**Remove engine = `bnos build --clean`** (whitelist delete, never touches `nodes/`).

---

## III. Commands

| Command | Purpose |
|------|------|
| `bnos build` | Inject driver engine (first time) |
| `bnos build --force` | Overwrite existing engine |
| `bnos build --clean` | Remove driver engine |
| `bnos build --update` | Rebuild `pipeline.json` + orchestrator after node changes |
| `bnos build --docker` | Also generate `Dockerfile` + `.dockerignore` |

---

## IV. Runtime

```bash
# No BNOS GUI needed — pure Python
python -m bnos_runtime.engine pipeline.json
```

Engine auto-dispatches by node type: standalone → `standalone_runner`, composite → pre-generated `orchestrator.py`.

---

## V. Mixed Node Type Support

| Node Type | Launch Method | Runtime |
|------|------|------|
| Standalone | `subprocess.Popen([venv/python, listener.py])` | Independent process |
| Composite (inprocess) | `subprocess.Popen([venv/python, orchestrator.py])` | Single process imports sub-nodes |
| Composite (process) | Launch sub-node processes separately | Multi-process |

Full design: `docs/design/BNOS_Build_独立应用打包方案.md`.
