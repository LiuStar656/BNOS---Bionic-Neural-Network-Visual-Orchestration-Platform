# BNOS Build — 独立运行时驱动引擎方案

## 一、背景与目标

### 现状

BNOS 是优秀的可视化节点编排开发工具（Studio），但开发完成的工作流无法脱离 BNOS GUI 独立运行。用户用 BNOS 搭建好管线后，面临"如何上线"的问题。

### 目标

实现 `bnos build` 命令，在 BNOS 项目根目录中注入**独立的运行时驱动引擎**，使项目可在无 GUI 环境下按拓扑结构启动管线。

**核心哲学：引擎 = 外挂驱动层，不是项目的一部分**

- **引擎与源文件物理隔离**：所有引擎文件集中在 `bnos_runtime/` 目录下。删除该目录 + `pipeline.json` + `run.*` = 项目恢复为纯开发项目，节点代码不受任何影响。
- **引擎可独立更新**：修改 `nodes/` 结构或 DAG 后，`bnos build --update` 重新生成 `pipeline.json` + 编排器脚本，引擎核心代码不变。
- **源文件零改动**：引擎只**读取** `nodes/` 下的 `main.py`、`config.json`、`input.json`/`output.json`，从不写入或修改。
- **引擎 = 方便层**：它的唯一职责是"替代 GUI，按拓扑顺序启动节点"——不多做任何事。

类比：**USB 驱动程序之于硬盘**——拔掉驱动，硬盘里的数据完好无损。

---

## 二、核心思路

### 节点类型与启动方式差异

一个 BNOS 项目可能同时包含两种节点，**启动方式截然不同**：

| 维度 | 单进程独立节点 | 复合节点 (inprocess) | 复合节点 (process 模式) |
|------|:------------:|:-------------------:|:---------------------:|
| **进程数** | 1 个 | 1 个（含全部子节点） | N 个（每个子节点独立进程） |
| **入口** | `listener.py` / `main.py` | 自动生成的 `orchestrator.py` | N × 各自的 `main.py` |
| **子节点通信** | — | 进程内函数调用 + 内存 ctx | 文件管道（input.json/output.json） |
| **venv 来源** | 节点自身 `.venv/` | 合并的复合节点独立 venv | 各子节点自身 `.venv/` |
| **DAG 编排** | 无（单节点） | 编排器内拓扑排序 | 顶层引擎并行调度 |
| **资源限制** | 单进程 | 整个编排器进程 | 每个子进程独立限制 |

**结论**：`engine.py` 必须能识别节点类型，对复合节点走编排器路径，对独立节点走直接子进程路径。

### 分层分析

BNOS 完整安装约 300MB+，按运行时必要性分层：

| 层 | 组件 | 运行时需要？ | 占比 |
|-----|------|:---:|------|
| **GUI 框架** | PySide6、QGraphicsView、Canvas、Dock、Menu | ❌ | ~200MB |
| **编辑器功能** | Action 系统、参数面板、对话框、右键菜单 | ❌ | ~5MB |
| **开发辅助** | Toast、Splash、Changelog Viewer、Settings | ❌ | ~2MB |
| **调度引擎** | node_process、orchestrator、IPC、队列、轮询 | ✅ | ~200KB |
| **复合节点引擎** | composite_orchestrator、composite_env、composite_node | ✅ | ~150KB |
| **业务逻辑** | 用户编写的 main.py + 第三方依赖 | ✅ | 用户决定 |
| **基础运行时** | psutil、logger、config 解析、thread_pool | ✅ | ~3MB |

**砍掉 GUI 后，运行时核心模块约 350KB（纯 Python 源文件），部署时无需安装 PySide6 及其 Qt 依赖。**

### 原则

1. **节点代码零改动** — main.py 原样工作，不进不出
2. **依赖最小化** — 不引入 PySide6 及任何 Qt 组件
3. **平台无关** — 产出物可在 Windows/Linux/macOS 上运行
4. **可选的容器化** — 自动生成 Dockerfile，一键 docker build
5. **引擎与源文件隔离** — 引擎是独立于 `nodes/` 的外挂层，删除引擎不影响项目和节点
6. **引擎可更新** — 项目结构变化后，`bnos build --update` 重新生成引擎

---

## 三、`bnos build` 命令设计

```bash
# 在项目根目录执行
bnos build [--docker] [--no-venv] [--force] [--clean] [--update]
```

### 参数

| 参数 | 必填 | 说明 |
|------|:---:|------|
| `--docker` | ❌ | 同时生成 Dockerfile + docker-compose.yml 到项目根目录 |
| `--no-venv` | ❌ | 不生成 venv 修复信息，使用系统 Python |
| `--force` | ❌ | 覆盖已有的 `bnos_runtime/`、`pipeline.json` 等文件 |
| `--clean` | ❌ | **仅删除** `bnos_runtime/`、`pipeline.json`、`run.*`、`requirements.txt`、`Dockerfile`——不碰 `nodes/` |
| `--update` | ❌ | 更新 `pipeline.json` + 复合节点编排器（项目 DAG/节点变化时使用），引擎核心不动 |

### 初始化 vs 更新 vs 清理

```
bnos build           → 全新注入引擎（目录不存在时）
bnos build --force   → 覆盖已有引擎（目录存在时）
bnos build --update  → 重建 pipeline.json + orchestrator，不重写引擎核心
bnos build --clean   → 移除所有引擎文件，项目恢复纯净状态
```

**无 `--output` 参数** — 命令始终作用于当前目录（项目根目录）。执行前会检测当前目录是否包含 `nodes/` 文件夹和 `project_config.json`，不是 BNOS 项目则拒绝执行。

### 示例

```bash
cd my_bnos_project/

# 注入运行时引擎
bnos build

# 项目结构变化后更新
bnos build --update

# 注入 + Docker 支持
bnos build --docker

# 清理引擎
bnos build --clean
# 删除后项目恢复为纯开发状态
ls bnos_runtime/   # → 不存在
ls pipeline.json   # → 不存在
ls nodes/          # → 完好无损

# 项目根目录变为：
my_bnos_project/            # 引擎注入后的状态
├── bnos_runtime/           # ✅ 新生成 — 驱动引擎
├── pipeline.json           # ✅ 新生成 — 拓扑描述
├── run.sh                  # ✅ 新生成
├── run.bat                 # ✅ 新生成
├── requirements.txt        # ✅ 新生成（无 PySide6）
├── Dockerfile              # ✅ 可选
├── docker-compose.yml      # ✅ 可选
├── nodes/                  # 【已有，不动】源文件
│   ├── fetch_data/
│   ├── image_pipeline/
│   │   ├── orchestrator.py # ✅ 新生成（build 时）
│   │   └── ...
│   └── save_db/
├── venv/                   # 【已有，不动】
├── project_config.json     # 【已有，不动】
└── ...                     # 其他项目文件，不动
```

### 上线流程

```
开发（GUI）                 构建（CLI）                部署（服务器）
┌──────────┐              ┌──────────┐              ┌──────────┐
│ 画布拖拽  │   bnos build │ 注入引擎   │   git push  │  git pull │
│ 连线调试  │ ──────────→  │ 生成配置   │ ──────────→ │  运行管线  │
│ 配置参数  │              │ 项目自包含 │              │  无 GUI   │
└──────────┘              └──────────┘              └──────────┘

项目结构变化后：
┌──────────┐              ┌──────────┐
│ 新增节点  │  bnos build  │ pipeline.json 更新 │
│ 改 DAG   │ ── --update →│ orchestrator 重建   │
│ 改配置   │              │ bnos_runtime/ 不动  │
└──────────┘              └──────────┘
```

---

### pipeline.json 格式（含混合节点类型）

```json
{
    "name": "data_pipeline",
    "nodes": {
        "fetch_data": {
            "type": "standalone",
            "path": "nodes/fetch_data",
            "entry": "main.py",
            "timeout": 120,
            "resource_limit": {
                "memory_mb": 512,
                "cpu_percent": 100
            }
        },
        "image_pipeline": {
            "type": "composite",
            "path": "nodes/image_pipeline",
            "runtime": "inprocess",
            "entry": "orchestrator.py",
            "timeout": 600,
            "resource_limit": {
                "memory_mb": 4096,
                "cpu_percent": 200
            },
            "sub_nodes": {
                "preprocess": {
                    "path": "nodes/image_pipeline/sub_nodes/preprocess",
                    "entry": "main.py"
                },
                "inference": {
                    "path": "nodes/image_pipeline/sub_nodes/inference",
                    "entry": "main.py"
                },
                "postprocess": {
                    "path": "nodes/image_pipeline/sub_nodes/postprocess",
                    "entry": "main.py"
                }
            },
            "internal_edges": [
                {"from": "preprocess", "to": "inference"},
                {"from": "inference", "to": "postprocess"}
            ],
            "external_input": {
                "preprocess": ["input.json"]
            },
            "external_output": {
                "postprocess": ["output.json"]
            }
        },
        "save_db": {
            "type": "standalone",
            "path": "nodes/save_db",
            "entry": "main.py",
            "timeout": 60
        }
    },
    "edges": [
        {"from": "fetch_data", "to": "image_pipeline"},
        {"from": "image_pipeline", "to": "save_db"}
    ]
}
```

---

## 四、产出物结构

`bnos build` 在项目根目录注入以下文件。已有的 `nodes/`、`venv/` 等**原样保留不动**。

```
<项目根目录>/                     # 本身就是可部署产物
│
├── bnos_runtime/               # ✅ 新生成 — 精简运行时引擎（零 GUI）
│   ├── __init__.py
│   ├── engine.py               # 顶层执行引擎：类型分发 + DAG 调度
│   ├── standalone_runner.py    # 独立节点启动器
│   ├── composite_runner.py     # 复合节点启动器（编排器模式）
│   ├── orchestrator.py          # DAG 拓扑排序工具
│   ├── pipeline_loader.py       # pipeline.json 解析与校验
│   ├── venv_resolver.py         # 跨平台 Python 解释器定位
│   ├── logger.py                # 精简日志（stdout + 文件）
│   └── resource_limit.py        # 资源限制（可选）
│
├── pipeline.json                # ✅ 新生成 — 工作流定义（从画布状态生成）
│
├── run.sh                       # ✅ 新生成 — Linux/macOS 启动
├── run.bat                      # ✅ 新生成 — Windows 启动
├── requirements.txt             # ✅ 新生成 — 纯运行时依赖（无 PySide6）
│
├── Dockerfile                   # ✅ 可选 — 容器化构建
├── docker-compose.yml           # ✅ 可选 — 容器化编排
│
├── nodes/                       # 【已有，不动】用户节点
│   ├── fetch_data/              # [独立节点]
│   │   ├── main.py
│   │   ├── config.json
│   │   └── .venv/
│   ├── image_pipeline/          # [复合节点]
│   │   ├── orchestrator.py      # ✅ 新生成 — 复合节点编排器
│   │   ├── node_clusters.json   # 已有，不动
│   │   ├── sub_nodes/           # 已有，不动
│   │   │   ├── preprocess/
│   │   │   ├── inference/
│   │   │   └── postprocess/
│   │   └── .venv/               # 已有（合并 venv），不动
│   └── save_db/                 # [独立节点]
│       ├── main.py
│       ├── config.json
│       └── .venv/
│
├── venv/                        # 【已有，不动】项目级 venv
├── project_config.json          # 【已有，不动】
└── .gitignore                   # 【已有，不动】
```

### 关键设计

| 原则 | 说明 |
|------|------|
| **引擎 ⇄ 源文件隔离** | `bnos_runtime/`、`pipeline.json`、`run.*` 这三类是**引擎层**；`nodes/`、`venv/`、`project_config.json` 是**项目层**。两层互不写入。 |
| **单向注入** | `bnos build` 只生成引擎层文件，不修改项目层文件 |
| **可逆** | `bnos build --clean` 删除所有引擎层文件，项目恢复纯净 |
| **可更新** | `bnos build --update` 重建 `pipeline.json` + 编排器，引擎核心不动 |
| **Git 策略** | 推荐 `.gitignore` 包含 `bnos_runtime/`、`pipeline.json`、`run.*`、`requirements.txt`。服务器上 `git pull` 后执行 `bnos build` 即可。 |

---

## 五、运行时引擎设计

引擎分为三层：**顶层调度 → 类型分发 → 节点执行**

```
PipelineRunner
  │
  ├─ _topological_sort()       → DAG → 并行批次
  │
  ├─ 对于 standalone 节点:
  │   └─ StandaloneRunner.run()
  │       └─ subprocess.run([venv/python, main.py])
  │
  └─ 对于 composite 节点:
      ├─ inprocess 模式:
      │   └─ CompositeRunner.run_inprocess()
      │       └─ subprocess.run([venv/python, orchestrator.py])
      │
      └─ process 模式:
          └─ CompositeRunner.run_process()
              └─ 并行启动 N 个 subprocess.run()
```

### engine.py — 顶层执行引擎

```python
"""BNOS 运行时执行引擎 — 零 GUI 依赖，支持独立节点 + 复合节点混合"""

import json
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from bnos_runtime.pipeline_loader import load_pipeline, PipelineDef, NodeDef
from bnos_runtime.standalone_runner import StandaloneRunner
from bnos_runtime.composite_runner import CompositeRunner
from bnos_runtime.orchestrator import topological_sort


@dataclass
class NodeResult:
    node_id: str
    node_type: str          # "standalone" | "composite"
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    success: bool


class PipelineRunner:
    """管线执行器 — 混合节点类型"""

    def __init__(self, pipeline_path: Path):
        self.pipeline: PipelineDef = load_pipeline(pipeline_path)
        self.results: dict[str, NodeResult] = {}

    def run(self) -> dict[str, NodeResult]:
        batches = topological_sort(
            list(self.pipeline.nodes.keys()),
            self.pipeline.edges,
        )
        total = sum(len(b) for b in batches)

        print(f"[BNOS] Pipeline '{self.pipeline.name}'")
        print(f"[BNOS] {len(self.pipeline.nodes)} nodes ({self._node_type_summary()}) in {len(batches)} stages")
        print("-" * 50)

        for stage_idx, batch in enumerate(batches):
            print(f"\n[Stage {stage_idx + 1}/{len(batches)}] Running: {', '.join(batch)}")

            with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                futures = {pool.submit(self._run_node, nid): nid for nid in batch}
                for future in as_completed(futures):
                    result = future.result()
                    self.results[result.node_id] = result

                    status = "OK" if result.success else "FAIL"
                    type_tag = "C" if result.node_type == "composite" else "S"
                    print(f"  [{type_tag}] {result.node_id}: {status} ({result.duration_ms:.0f}ms)")

                    if not result.success:
                        print(f"\n[FATAL] Node '{result.node_id}' failed (exit={result.exit_code})")
                        print(f"[FATAL] stderr: {result.stderr[-500:]}")
                        sys.exit(1)

        print("\n" + "=" * 50)
        print(f"[BNOS] Pipeline complete. {sum(1 for r in self.results.values() if r.success)}/{len(self.results)} OK.")
        return self.results

    def _run_node(self, node_id: str) -> NodeResult:
        node_def = self.pipeline.nodes[node_id]
        if node_def.type == "composite":
            runner = CompositeRunner(node_id, node_def)
        else:
            runner = StandaloneRunner(node_id, node_def)
        return runner.run()

    def _node_type_summary(self) -> str:
        s = sum(1 for n in self.pipeline.nodes.values() if n.type == "standalone")
        c = sum(1 for n in self.pipeline.nodes.values() if n.type == "composite")
        return f"{s} standalone, {c} composite"
```

### standalone_runner.py — 独立节点执行器

```python
"""独立节点运行器 — 单进程子进程执行"""

import os
import subprocess
import sys
import time
from pathlib import Path

from bnos_runtime.pipeline_loader import NodeDef
from bnos_runtime.venv_resolver import resolve_python
from bnos_runtime.resource_limit import create_resource_limit, ResourceLimit


class StandaloneRunner:
    def __init__(self, node_id: str, node_def: NodeDef):
        self.node_id = node_id
        self.defn = node_def

    def run(self) -> "NodeResult":
        from bnos_runtime.engine import NodeResult  # 避免循环导入

        node_path = Path(self.defn.path)
        python_exe = resolve_python(node_path)
        entry = self.defn.entry or "main.py"

        # 资源限制
        limit = None
        if self.defn.resource_limit:
            limit = create_resource_limit(None, self.defn.resource_limit)

        t0 = time.perf_counter()
        try:
            proc = subprocess.Popen(
                [str(python_exe), entry],
                cwd=str(node_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # 应用资源限制到子进程
            if limit:
                limit.assign_to_pid(proc.pid)

            stdout, stderr = proc.communicate(timeout=self.defn.timeout)
            duration_ms = (time.perf_counter() - t0) * 1000
            return NodeResult(
                node_id=self.node_id,
                node_type="standalone",
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                success=proc.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            duration_ms = (time.perf_counter() - t0) * 1000
            return NodeResult(
                node_id=self.node_id,
                node_type="standalone",
                exit_code=-1,
                stdout=stdout or "",
                stderr=f"Timeout after {self.defn.timeout}s\n{stderr or ''}",
                duration_ms=duration_ms,
                success=False,
            )
```

### composite_runner.py — 复合节点执行器

```python
"""复合节点运行器 — 支持 inprocess（编排器）和 process 两种模式"""

import subprocess
import sys
import time
from pathlib import Path

from bnos_runtime.pipeline_loader import NodeDef
from bnos_runtime.venv_resolver import resolve_python
from bnos_runtime.resource_limit import create_resource_limit


class CompositeRunner:
    def __init__(self, node_id: str, node_def: NodeDef):
        self.node_id = node_id
        self.defn = node_def

    def run(self) -> "NodeResult":
        from bnos_runtime.engine import NodeResult

        mode = self.defn.runtime or "inprocess"
        if mode == "process":
            return self._run_process()
        return self._run_inprocess()

    def _run_inprocess(self) -> "NodeResult":
        """编排器模式：运行预生成的 orchestrator.py，所有子节点在同一进程"""
        from bnos_runtime.engine import NodeResult

        node_path = Path(self.defn.path)
        python_exe = resolve_python(node_path)
        orchestrator = node_path / (self.defn.entry or "orchestrator.py")

        if not orchestrator.exists():
            return NodeResult(
                self.node_id, "composite", -2, "", "orchestrator.py not found", 0, False,
            )

        limit = None
        if self.defn.resource_limit:
            limit = create_resource_limit(None, self.defn.resource_limit)

        t0 = time.perf_counter()
        try:
            proc = subprocess.Popen(
                [str(python_exe), str(orchestrator)],
                cwd=str(node_path.parent.parent),  # 项目根目录，确保 sys.path 可 import 子节点
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if limit:
                limit.assign_to_pid(proc.pid)

            stdout, stderr = proc.communicate(timeout=self.defn.timeout)
            duration_ms = (time.perf_counter() - t0) * 1000
            return NodeResult(
                self.node_id, "composite", proc.returncode, stdout, stderr, duration_ms,
                proc.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            duration_ms = (time.perf_counter() - t0) * 1000
            return NodeResult(
                self.node_id, "composite", -1, stdout or "",
                f"Timeout after {self.defn.timeout}s\n{stderr or ''}", duration_ms, False,
            )

    def _run_process(self) -> "NodeResult":
        """独立进程模式：并行启动每个子节点为独立进程"""
        from bnos_runtime.engine import NodeResult
        from concurrent.futures import ThreadPoolExecutor, as_completed

        t0 = time.perf_counter()
        sub_results: list[NodeResult] = []

        with ThreadPoolExecutor(max_workers=len(self.defn.sub_nodes)) as pool:
            futures = {}
            for name, sn in self.defn.sub_nodes.items():
                # 每个子节点作为独立进程
                node_path = Path(sn["path"])
                python_exe = resolve_python(node_path)
                entry = sn.get("entry", "main.py")

                limit = None
                if sn.get("resource_limit"):
                    limit = create_resource_limit(None, sn["resource_limit"])

                def _do_run(py=python_exe, e=entry, np=node_path, l=limit, to=self.defn.timeout):
                    p = subprocess.Popen(
                        [str(py), e], cwd=str(np),
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    )
                    if l:
                        l.assign_to_pid(p.pid)
                    out, err = p.communicate(timeout=to)
                    return NodeResult(name, "standalone", p.returncode, out, err, 0, p.returncode == 0)

                futures[pool.submit(_do_run)] = name

            for future in as_completed(futures):
                result = future.result()
                sub_results.append(result)
                if not result.success:
                    break  # 快速失败

        duration_ms = (time.perf_counter() - t0) * 1000
        all_ok = all(r.success for r in sub_results)
        combined_stderr = "\n".join(f"[{r.node_id}] {r.stderr}" for r in sub_results if r.stderr)
        combined_stdout = "\n".join(f"[{r.node_id}] {r.stdout}" for r in sub_results if r.stdout)

        return NodeResult(
            self.node_id, "composite",
            0 if all_ok else 1,
            combined_stdout, combined_stderr, duration_ms, all_ok,
        )
```

### orchestrator.py — 预生成的复合节点编排器

构建时由 `bnos build` 自动生成到每个复合节点目录。运行时引擎不参与生成——只负责执行。

```python
"""Auto-generated by bnos build — do not edit manually"""
#
# 复合节点: image_pipeline
# 子节点:   preprocess → inference → postprocess
# 生成时间: 2025-01-01T00:00:00
# 模式:     inprocess
#
import importlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent  # 项目根目录
COMP_DIR     = Path(__file__).parent         # nodes/image_pipeline/
SUB_NODES    = COMP_DIR / "sub_nodes"

# ─── 子节点模块导入 ───
MODULES = {
    "preprocess":  "nodes.image_pipeline.sub_nodes.preprocess.main",
    "inference":   "nodes.image_pipeline.sub_nodes.inference.main",
    "postprocess": "nodes.image_pipeline.sub_nodes.postprocess.main",
}

# ─── 内部 DAG 边 ───
INTERNAL_EDGES = [
    ("preprocess", "inference"),
    ("inference", "postprocess"),
]

# ─── 外部端口路由 ───
EXTERNAL_INPUT: dict[str, list[str]] = {"preprocess": ["input.json"]}
EXTERNAL_OUTPUT: dict[str, list[str]] = {"postprocess": ["output.json"]}


def _topo_sort() -> list[str]:
    """Kahn 拓扑排序"""
    in_degree = {n: 0 for n in MODULES}
    children: dict[str, list[str]] = {n: [] for n in MODULES}
    for src, tgt in INTERNAL_EDGES:
        in_degree[tgt] += 1
        children[src].append(tgt)

    order = []
    queue = [n for n, d in in_degree.items() if d == 0]
    while queue:
        n = queue.pop(0)
        order.append(n)
        for child in children[n]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    return order


def _load_external_input() -> dict[str, Any]:
    """从复合节点目录读取上层传入的外部输入"""
    inp = {}
    for target_node, files in EXTERNAL_INPUT.items():
        for fname in files:
            fpath = COMP_DIR / fname
            if fpath.exists():
                with open(fpath) as f:
                    data = json.load(f)
                if target_node not in inp:
                    inp[target_node] = data
                else:
                    inp[target_node].update(data)
    return inp


def _build_input(name: str, ctx: dict[str, Any], ext: dict[str, Any]) -> dict[str, Any]:
    """构建节点的输入数据：外部输入 + 上游节点输出"""
    result: dict[str, Any] = {}
    # 外部输入
    if name in ext:
        result.update(ext[name])
    # 上游 DAG 输出
    for src, tgt in INTERNAL_EDGES:
        if tgt == name and src in ctx:
            result.update(ctx[src])
    return result


def main():
    ext_input = _load_external_input()
    modules = {}
    failed = set()

    for name, mod_path in MODULES.items():
        try:
            modules[name] = importlib.import_module(mod_path)
        except Exception as e:
            print(f"[ORCH] Failed to import {name}: {e}", file=sys.stderr)
            failed.add(name)

    if failed:
        print(f"[ORCH] Aborting: import failed for {failed}", file=sys.stderr)
        sys.exit(1)

    order = _topo_sort()
    ctx: dict[str, Any] = {}

    for name in order:
        inp = _build_input(name, ctx, ext_input)
        print(f"[ORCH] Running {name}...")
        try:
            out = modules[name].process(inp)
        except Exception as e:
            print(f"[ORCH] {name} failed: {e}", file=sys.stderr)
            sys.exit(1)

        ctx[name] = out
        out_path = SUB_NODES / name / "output.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump({"result": out}, f, ensure_ascii=False, indent=2)
        print(f"[ORCH] {name} OK → {out_path}")

    # 写复合节点级输出（给下游独立节点消费）
    for src_node, files in EXTERNAL_OUTPUT.items():
        if src_node in ctx:
            for fname in files:
                fpath = COMP_DIR / fname
                with open(fpath, "w") as f:
                    json.dump(ctx[src_node], f, ensure_ascii=False, indent=2)

    print("[ORCH] Composite node complete.")


if __name__ == "__main__":
    main()
```

### pipeline_loader.py — pipeline.json 解析

```python
"""pipeline.json 解析器"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class NodeDef:
    type: str                       # "standalone" | "composite"
    path: str
    entry: str = "main.py"
    timeout: int = 300
    resource_limit: dict[str, Any] | None = None
    # 复合节点专用
    runtime: str | None = None      # "inprocess" | "process"
    sub_nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    internal_edges: list[dict[str, str]] = field(default_factory=list)
    external_input: dict[str, list[str]] = field(default_factory=dict)
    external_output: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class PipelineDef:
    name: str
    nodes: dict[str, NodeDef]
    edges: list[dict[str, str]]


def load_pipeline(path: Path) -> PipelineDef:
    with open(path) as f:
        data = json.load(f)

    nodes = {}
    for nid, nd in data["nodes"].items():
        nodes[nid] = NodeDef(
            type=nd.get("type", "standalone"),
            path=nd["path"],
            entry=nd.get("entry", "main.py"),
            timeout=nd.get("timeout", 300),
            resource_limit=nd.get("resource_limit"),
            runtime=nd.get("runtime"),
            sub_nodes=nd.get("sub_nodes", {}),
            internal_edges=nd.get("internal_edges", []),
            external_input=nd.get("external_input", {}),
            external_output=nd.get("external_output", {}),
        )

    return PipelineDef(
        name=data.get("name", "unnamed"),
        nodes=nodes,
        edges=data.get("edges", []),
    )
```

### venv_resolver.py — 跨平台 Python 解释器定位

```python
"""跨平台 Python 解释器定位"""

import sys
import platform
from pathlib import Path


def resolve_python(node_path: Path) -> Path:
    """按优先级定位节点的 Python 解释器"""
    is_win = platform.system() == "Windows"

    # 1) 节点自身的 .venv
    if is_win:
        candidate = node_path / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = node_path / ".venv" / "bin" / "python3"

    if candidate.exists():
        return candidate

    # 2) 项目级 venv（复合节点的合并 venv 在此）
    project_venv = node_path.parent.parent / "venv"
    if is_win:
        candidate = project_venv / "Scripts" / "python.exe"
    else:
        candidate = project_venv / "bin" / "python3"
    if candidate.exists():
        return candidate

    # 3) 系统 Python
    return Path(sys.executable)
```

---

## 六、构建流程

### build 命令执行步骤

```
Step 1: 验证项目 → 检查 nodes/ + project_config.json 存在
Step 2: 扫描节点 → 遍历 nodes/，识别每个节点的 type（standalone | composite）
Step 3: 导入运行时模块 → 从 BNOS 安装目录提取必要 .py 文件到 bnos_runtime/
Step 4: 生成 pipeline.json → 从 project_config.json + 画布状态生成工作流定义
Step 5: 处理复合节点 → 为每个 composite 节点生成 orchestrator.py 到其目录
Step 6: 生成 requirements.txt → 扫描所有节点依赖，输出不含 PySide6 的依赖清单
Step 7: 生成 run.sh / run.bat → 一键启动脚本
Step 8: [可选] 生成 Dockerfile + docker-compose.yml
Step 9: 输出构建报告 + 节点类型统计
```

### 新旧对比

| 维度 | 旧方案（导出模式） | 新方案（注入模式） |
|------|:-----------:|:-----------:|
| 节点文件 | **复制**到 dist/ | **原样保留**，不动 |
| venv 目录 | **复制**到 dist/ | **原样保留**，不动 |
| 文件重复 | 两份（源 + dist） | 一份 |
| `git push` 后 | dist/ 需要单独上传 | 整个项目就是产物 |
| 修改节点后 | 需要重新 build + copy | 直接 git push，无需 rebuild |
| 构建速度 | 取决于节点数量与大小 | 固定 < 1s（无文件复制） |

### 节点类型自动检测

构建器自动扫描项目目录，基于 `node_clusters.json` 的存在性判断：

```python
def detect_node_type(node_path: Path) -> str:
    """检测节点类型"""
    if (node_path / "node_clusters.json").exists():
        return "composite"
    return "standalone"
```

若用户在画布中手动标记了类型（通过 `config.json` 的 `_composite` 字段），优先使用标记值。

### orchestrator.py 生成规则

构建器根据 `node_clusters.json` 中的子节点列表和内部 DAG 边生成编排器脚本：

| 输入 | 来源 |
|------|------|
| 子节点模块路径 | `nodes.{comp_name}.sub_nodes.{name}.main` |
| 内部 DAG 边 | `node_clusters.json` → `_internal_edges` |
| 外部输入路由 | `node_clusters.json` → `_port_routing.input` |
| 外部输出路由 | `node_clusters.json` → `_port_routing.output` |

生成的 `orchestrator.py` 是一个自包含的 Python 脚本，不依赖任何 BNOS GUI 模块——只依赖 `importlib`、`json`、`pathlib`（全部标准库）。

### 模块提取白名单

以下模块从 BNOS 安装目录提取到 `bnos_runtime/`。**不复制** — 注入的模块是独立副本，与原 BNOS 安装无关。

```python
RUNTIME_MODULES = [
    "ui/core/logger.py",                   # 精简日志
    "ui/core/system/thread_pool.py",       # 线程池
    "ui/core/system/resource_limit.py",    # 全平台资源限制
    "ui/core/i18n/i18n.py",               # 国际化（t() 函数）
    "ui/core/i18n/translation_keys.py",    # 翻译键常量
]
```

提取时自动去除对 PySide6 / ui.canvas / ui.panels 的 import 引用。复合节点的编排逻辑由构建时生成的 `orchestrator.py` 自包含，不需要从 BNOS 源码中提取 `composite_node.py` 或 `composite_orchestrator.py`。

---

## 七、Docker 化（可选）

### 自动生成的 Dockerfile

生成在项目根目录，COPY 整个项目（已通过 `.dockerignore` 排除 GUI 和无用文件）。

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "bnos_runtime.engine", "pipeline.json"]
```

### 自动生成的 .dockerignore

排除 GUI 源码和开发文件，减小镜像体积：

```
ui/canvas/
ui/panels/
ui/dialogs/
ui/main_window/
ui/creators/
ui/icons/
.dockerignore
Dockerfile
*.md
.git/
__pycache__/
*.pyc
```

### docker-compose.yml

```yaml
version: "3.8"
services:
  data-pipeline:
    build: .
    restart: on-failure
    environment:
      - BNOS_LOG_LEVEL=INFO
    volumes:
      - ./output:/app/output
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2"
```

---

## 八、实施计划

| 阶段 | 内容 | 工作量 | 依赖 |
|------|------|:---:|------|
| **P0** | 运行时引擎开发（engine + standalone_runner + composite_runner + pipeline_loader + venv_resolver） | 2 天 | 无 |
| **P1** | orchestrator 模板 — 从 node_clusters.json 渲染自包含脚本 | 1 天 | P0 |
| **P2** | `bnos build` 命令实现（项目验证 + 模块注入 + pipeline.json 生成 + 构建报告） | 2 天 | P0, P1 |
| **P3** | Docker 化支持（Dockerfile + .dockerignore + docker-compose 生成） | 0.5 天 | P2 |
| **P4** | 画布导出功能（GUI 内一键调用 build，导出当前画布状态） | 1 天 | 无 |
| **总计** | | **~6.5 天** | |

### 优先级说明

- **P0** 纯 Python 引擎——不依赖项目代码，可独立开发和测试
- **P1** 编排器模板——将 GUI 中的 `node_clusters.json` 转换为自包含 `orchestrator.py`
- **P2** CLI 入口——`bnos build` 命令，项目验证 + 文件注入
- **P4** GUI 导出——画布菜单增加 "Build Runtime" 按钮

### build 命令实现伪代码

```python
def cmd_build(docker: bool = False):
    """bnos build — 注入运行时到当前项目"""
    project_root = Path.cwd()

    # 1. 验证是 BNOS 项目
    if not (project_root / "nodes").exists():
        sys.exit("Error: not a BNOS project (no nodes/ directory)")

    # 2. 扫描节点类型
    nodes = scan_nodes(project_root / "nodes")
    # → [{"id": "fetch_data", "type": "standalone", ...}, ...]

    # 3. 注入 bnos_runtime/（从 BNOS 安装目录提取）
    inject_runtime(project_root / "bnos_runtime", RUNTIME_MODULES)

    # 4. 生成 pipeline.json
    generate_pipeline(project_root / "pipeline.json", nodes)

    # 5. 生成复合节点 orchestrator
    for node in nodes:
        if node.type == "composite":
            generate_orchestrator(node.path / "orchestrator.py", node)

    # 6. 生成 requirements.txt
    generate_requirements(project_root / "requirements.txt", nodes)

    # 7. 生成启动脚本
    generate_launcher(project_root / "run.sh", project_root / "run.bat")

    # 8. 可选：Docker
    if docker:
        generate_docker(project_root)

    # 9. 报告
    print_build_report(nodes)
```

### 测试策略

| 测试类型 | P0 覆盖 |
|------|------|
| 独立节点启动 | `main.py` 返回 0 / 返回非零 / 超时 |
| 复合节点 (inprocess) | orchestrator.py 正常结束 / 子节点异常 / 导入失败 |
| 复合节点 (process) | 全部成功 / 部分失败 / 全部超时 |
| 混合管线 | standalone + composite + standalone 三节点线性执行 |
| DAG 分批 | 2 独立节点 → 1 复合节点 → 2 独立节点（验证并行批次） |
| 资源限制 | 独立节点内存限制 / 复合节点 CPU 限制 |

---

## 九、验收标准

| 检查项 | 标准 |
|--------|------|
| 产物形态 | 项目根目录增加 `bnos_runtime/` + `pipeline.json` + `run.*`，无新子目录创建 |
| 已有文件 | `nodes/`、`venv/`、`project_config.json` 等零改动 |
| 构建产物大小 | < 350KB（bnos_runtime 模块 + pipeline.json + run.*） |
| 运行时依赖 | 不含 PySide6 / Qt 任何组件，仅需 Python 3.12 + psutil |
| 节点代码兼容性 | 现有所有节点 main.py 零改动可运行 |
| 管线执行 | 3 节点线性管线，`python -m bnos_runtime.engine pipeline.json` 一次性成功 |
| 复合节点 | orchestrator.py 自包含，`python orchestrator.py` 独立运行子节点 DAG |
| 错误处理 | 任一节点失败立即终止，退出码非零 |
| Docker 构建 | `docker build && docker compose up` 一次性通过 |
| 跨平台 | Windows / Linux 均可执行（macOS 尽力支持） |
| Git 友好 | commit 新生成文件后，另一台机器 `git pull && python -m bnos_runtime.engine pipeline.json` 可直接运行 |
| **引擎隔离** | `bnos build --clean` 后 `nodes/` 目录完好，项目可正常在 GUI 中打开 |
| **引擎更新** | 新增节点后 `bnos build --update` 仅更新 `pipeline.json` + 编排器，`bnos_runtime/` 不变 |
| **源文件保护** | `bnos build --clean` 不删除或修改 `nodes/` 下任何文件 |

---

## 十、引擎生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                        项目层（不碰）                            │
│  nodes/  │  venv/  │  project_config.json  │  .gitignore         │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 只读
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                        引擎层（可重建）                          │
│                                                                 │
│  bnos_runtime/engine.py        ← 顶层调度                        │
│  bnos_runtime/standalone_runner.py                               │
│  bnos_runtime/composite_runner.py                                │
│  bnos_runtime/pipeline_loader.py                                 │
│  bnos_runtime/orchestrator.py                                    │
│  bnos_runtime/venv_resolver.py                                   │
│  bnos_runtime/resource_limit.py                                  │
│  pipeline.json                 ← DAG 拓扑（可重新生成）          │
│  run.sh / run.bat              ← 启动脚本                        │
│  requirements.txt              ← 运行时依赖                      │
│                                                                 │
│  操作:                                                          │
│    bnos build          → 从头生成                                │
│    bnos build --update → 更新 pipeline.json + 编排器             │
│    bnos build --clean  → 全部删除                                │
└─────────────────────────────────────────────────────────────────┘
```

**关键性质**：
- 引擎层 100% 可重建 — 删除后执行 `bnos build` 即可恢复
- 项目层 0% 受影响 — 引擎不写入 `nodes/` 下任何文件
- `.gitignore` 推荐忽略引擎层文件，服务器端 `git pull && bnos build` 生成

---

## 十、风险与限制

| 风险 | 应对 |
|------|------|
| 节点内硬编码了 BNOS GUI API | 运行时设置 `BNOS_RUNTIME=1` 环境变量，节点检查后走纯 CLI 分支 |
| venv 跨机器兼容性 | 复用现有 `_repair_portable_venv` 逻辑 |
| 节点依赖 PySide6 | 依赖分析阶段告警，提供 `--no-venv` 跳过 |
| macOS 资源限制 | 仅支持优先级调节，文档注明 |
| 复合节点 orchestrator.py 的 import 路径与运行时目录结构不匹配 | 构建时验证所有 `nodes.{path}.main` 模块路径可解析，生成测试导入脚本 |
| 复合节点 process 模式的子节点 DAG 依赖未在 pipeline.json 中表达 | 构建器检查 `internal_edges` 并在 process 模式下按拓扑顺序串行启动子节点 |
| 合并 venv 缺少原始节点的第三方依赖 | 构建器扫描所有子节点的 `requirements.txt`，合并去重后重新 pip install |
| **多人协作时引擎版本不一致** | 推荐 `.gitignore` 忽略引擎文件，各开发者/服务器独立 `bnos build` |
| **`--clean` 误删用户文件** | `--clean` 仅删除白名单文件名（`bnos_runtime/`、`pipeline.json`、`run.*`、`requirements.txt`、`Dockerfile`），不遍历目录 |
| `bnos build` 后用户仍运行 BNOS Studio，`nodes/` 可能被修改 | 每次 `git push` 前重新 `bnos build` 确保 pipeline.json 与当前画布一致 |

### .gitignore 建议

由于引擎是**可重建的外挂层**，推荐忽略所有引擎文件：

```gitignore
# BNOS Build 驱动引擎（可重建 — 服务器上 git pull 后 bnos build 即可生成）
bnos_runtime/
pipeline.json
run.sh
run.bat
requirements.txt
Dockerfile
docker-compose.yml
```

**推荐策略**：`nodes/` 进版本管理；引擎文件不进。服务器 `git pull && bnos build` 即部署。

---

**最后更新**：2026-07-12
**状态**：方案设计，待实施
