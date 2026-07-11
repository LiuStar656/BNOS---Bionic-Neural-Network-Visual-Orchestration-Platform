# BNOS Build — 独立运行时源码打包方案

## 一、背景与目标

### 现状

BNOS 是优秀的可视化节点编排开发工具（Studio），但开发完成的工作流无法脱离 BNOS GUI 独立运行。用户用 BNOS 搭建好管线后，面临"如何上线"的问题。

### 目标

实现 `bnos build` 命令，将 BNOS 画布上的工作流连同必要的运行时源码打包为一个**独立可部署的源码目录**，砍掉所有 GUI 代码和依赖，只保留执行引擎。

**打包产物是源码（.py 文件），不是编译后的二进制**。用户拿到的是去掉 GUI 的纯净项目目录，通过 `python -m bnos_runtime.engine pipeline.json` 即可在任何有 Python 3.12 的机器上运行。

类比：**Unity Editor → Export Project**（导出工程文件，而非 Standalone Build），或 **Node-RED 的运行时模式**。

---

## 二、核心思路

### 分层分析

BNOS 完整安装约 300MB+，按运行时必要性分层：

| 层 | 组件 | 运行时需要？ | 占比 |
|-----|------|:---:|------|
| **GUI 框架** | PySide6、QGraphicsView、Canvas、Dock、Menu | ❌ | ~200MB |
| **编辑器功能** | Action 系统、参数面板、对话框、右键菜单 | ❌ | ~5MB |
| **开发辅助** | Toast、Splash、Changelog Viewer、Settings | ❌ | ~2MB |
| **调度引擎** | node_process、orchestrator、IPC、队列、轮询 | ✅ | ~200KB |
| **业务逻辑** | 用户编写的 main.py + 第三方依赖 | ✅ | 用户决定 |
| **基础运行时** | psutil、logger、config 解析、thread_pool | ✅ | ~3MB |

**砍掉 GUI 后，运行时核心模块仅 ~200KB（纯 Python 源文件），部署时无需安装 PySide6 及其 Qt 依赖。**

### 原则

1. **节点代码零改动** — main.py 原样工作，不进不出
2. **依赖最小化** — 不引入 PySide6 及任何 Qt 组件
3. **平台无关** — 产出物可在 Windows/Linux/macOS 上运行
4. **可选的容器化** — 自动生成 Dockerfile，一键 docker build

---

## 三、`bnos build` 命令设计

```bash
bnos build <pipeline.json> --output ./dist [--docker] [--name my-app]
```

### 参数

| 参数 | 必填 | 说明 |
|------|:---:|------|
| `pipeline.json` | ✅ | 从画布导出的工作流定义文件 |
| `--output` | ❌ | 输出目录，默认 `./dist` |
| `--docker` | ❌ | 同时生成 Dockerfile + docker-compose.yml |
| `--name` | ❌ | 应用名称，默认取管线名称 |
| `--no-venv` | ❌ | 不复制 venv，使用系统 Python |

### 示例

```bash
# 基本打包
bnos build my_pipeline.json

# 带 Docker 支持
bnos build my_pipeline.json --docker --name data-service

# 产出物
dist/my_pipeline/
├── bnos_runtime/           # 精简运行时
├── nodes/                  # 用户节点
├── pipeline.json
├── requirements.txt        # 无 PySide6
├── Dockerfile
├── docker-compose.yml
├── run.sh
└── run.bat
```

---

## 四、产出物结构

```
dist/<app_name>/
├── bnos_runtime/               # BNOS 精简运行时（独立模块）
│   ├── __init__.py
│   ├── engine.py               # 执行引擎入口
│   ├── node_runner.py           # 单节点进程管理
│   ├── orchestrator.py          # DAG 拓扑排序 + 并行调度
│   ├── pipeline_loader.py       # pipeline.json 解析
│   ├── logger.py                # 精简日志（stdout + 文件）
│   └── resource_limit.py        # 资源限制（可选）
│
├── nodes/                       # 用户节点（含 venv）
│   ├── fetch_data/
│   │   ├── main.py
│   │   ├── config.json
│   │   └── .venv/               # 可迁移虚拟环境
│   ├── process/
│   │   ├── main.py
│   │   ├── config.json
│   │   └── .venv/
│   └── save_db/
│       ├── main.py
│       ├── config.json
│       └── .venv/
│
├── pipeline.json                # 工作流定义
├── requirements.txt             # 仅运行时依赖（无 PySide6）
├── Dockerfile                   # 可选
├── docker-compose.yml           # 可选
├── run.sh                       # Linux/macOS 启动
└── run.bat                      # Windows 启动
```

---

## 五、运行时引擎设计

### engine.py — 核心执行引擎

```python
"""BNOS 运行时执行引擎 — 零 GUI 依赖"""

import json
import subprocess
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any


@dataclass
class NodeResult:
    node_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    success: bool


class PipelineRunner:
    """管线执行器"""

    def __init__(self, pipeline_path: Path):
        with open(pipeline_path) as f:
            self.pipeline = json.load(f)
        self.nodes = self.pipeline["nodes"]
        self.edges = self.pipeline.get("edges", [])
        self.results: dict[str, NodeResult] = {}

    def run(self) -> dict[str, NodeResult]:
        """执行完整管线，返回所有节点结果"""
        batches = self._topological_sort()
        total = sum(len(b) for b in batches)
        completed = 0

        print(f"[BNOS Runtime] Pipeline '{self.pipeline.get('name', 'unnamed')}'")
        print(f"[BNOS Runtime] {len(self.nodes)} nodes in {len(batches)} stages")
        print("-" * 50)

        for stage_idx, batch in enumerate(batches):
            print(f"\n[Stage {stage_idx + 1}/{len(batches)}] Running: {', '.join(batch)}")

            with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                futures = {pool.submit(self._run_node, nid): nid for nid in batch}
                for future in as_completed(futures):
                    result = future.result()
                    self.results[result.node_id] = result
                    completed += 1

                    status = "OK" if result.success else "FAIL"
                    print(f"  [{completed}/{total}] {result.node_id}: {status} "
                          f"({result.duration_ms:.0f}ms)")

                    if not result.success:
                        print(f"\n[ERROR] Node '{result.node_id}' failed with exit code {result.exit_code}")
                        print(f"[ERROR] stderr: {result.stderr[-500:]}")
                        print(f"\n[BNOS Runtime] Pipeline aborted at stage {stage_idx + 1}")
                        sys.exit(1)

        print("\n" + "=" * 50)
        print(f"[BNOS Runtime] Pipeline completed. {completed}/{total} nodes OK.")
        return self.results

    def _run_node(self, node_id: str) -> NodeResult:
        """启动单个节点进程并等待完成"""
        node = self.nodes[node_id]
        node_path = Path(node["path"])
        python_exe = node_path / ".venv" / "Scripts" / "python.exe"  # Windows
        if not python_exe.exists():
            python_exe = node_path / ".venv" / "bin" / "python3"  # Linux/macOS
        if not python_exe.exists():
            python_exe = sys.executable  # 回退到系统 Python

        entry = node.get("entry", "main.py")

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(python_exe), entry],
                cwd=str(node_path),
                capture_output=True,
                text=True,
                timeout=node.get("timeout", 300),
                env={**__import__("os").environ, "BNOS_RUNTIME": "1"},
            )
            duration_ms = (time.perf_counter() - t0) * 1000
            return NodeResult(
                node_id=node_id,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=duration_ms,
                success=proc.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - t0) * 1000
            return NodeResult(
                node_id=node_id,
                exit_code=-1,
                stdout="",
                stderr=f"Timeout after {node.get('timeout', 300)}s",
                duration_ms=duration_ms,
                success=False,
            )

    def _topological_sort(self) -> list[list[str]]:
        """DAG 拓扑排序，返回并行执行的批次"""
        # 构建邻接表和入度
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        children: dict[str, list[str]] = {nid: [] for nid in self.nodes}

        for edge in self.edges:
            src, tgt = edge["from"], edge["to"]
            in_degree[tgt] = in_degree.get(tgt, 0) + 1
            children.setdefault(src, []).append(tgt)

        # Kahn 算法
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        batches = []

        while queue:
            batches.append(list(queue))
            next_queue = []
            for node_id in queue:
                for child in children.get(node_id, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_queue.append(child)
            queue = next_queue

        return batches
```

---

## 六、构建流程

### build 命令执行步骤

```
Step 1: 解析 pipeline.json → 提取节点列表和连线关系
Step 2: 生成 bnos_runtime/ → 从源码提取必要模块（无 GUI 依赖）
Step 3: 复制节点目录 → 每个节点文件夹 + .venv 完整复制
Step 4: 生成 pipeline.json → 规范化工作流定义
Step 5: 生成 requirements.txt → 仅运行时依赖
Step 6: 生成 run.sh / run.bat → 一键启动脚本
Step 7: [可选] 生成 Dockerfile + docker-compose.yml
Step 8: 输出构建报告
```

### 模块提取白名单

以下模块从 BNOS 源码中提取到 `bnos_runtime/`：

```python
RUNTIME_MODULES = [
    "ui/core/logger.py",
    "ui/core/node/node_process.py",
    "ui/core/node/composite_orchestrator.py",
    "ui/core/node/composite_env.py",
    "ui/core/config/validators.py",
    "ui/core/system/thread_pool.py",
    "ui/core/system/polling_manager.py",
    "ui/core/system/ipc.py",
    "ui/core/i18n/i18n.py",
    "ui/core/i18n/translation_keys.py",
]
```

提取时自动去除对 PySide6 / ui.canvas / ui.panels 的 import 引用。

---

## 七、Docker 化（可选）

### 自动生成的 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bnos_runtime/ ./bnos_runtime/
COPY nodes/ ./nodes/
COPY pipeline.json .

CMD ["python", "-m", "bnos_runtime.engine", "pipeline.json"]
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
| **P0** | 运行时引擎开发（engine.py + 拓扑排序） | 2 天 | 无 |
| **P1** | `bnos build` 命令实现（文件复制 + 模块提取 + 依赖分析） | 3 天 | P0 |
| **P2** | 资源限制集成（Linux cgroups / Windows Job Objects） | 1 天 | P1 |
| **P3** | Docker 化支持（自动生成 Dockerfile + docker-compose） | 1 天 | P1 |
| **P4** | 画布导出功能（GUI 内一键导出 pipeline.json） | 1 天 | 无 |
| **总计** | | **~8 天** | |

---

## 九、验收标准

| 检查项 | 标准 |
|--------|------|
| 产物形态 | 纯 Python 源码目录，无 .exe / .dll / 二进制文件 |
| 构建产物大小 | < 200KB（bnos_runtime 模块，不含 venv 和用户节点） |
| 运行时依赖 | 不含 PySide6 / Qt 任何组件，仅需 Python 3.12 + psutil |
| 节点代码兼容性 | 现有所有节点 main.py 零改动可运行 |
| 管线执行 | 3 节点线性管线，`python -m bnos_runtime.engine pipeline.json` 一次性成功 |
| 并行执行 | 同层节点正确并发 |
| 错误处理 | 任一节点失败立即终止，退出码非零 |
| Docker 构建 | `docker build && docker compose up` 一次性通过 |
| 跨平台 | Windows / Linux 均可执行（macOS 尽力支持） |

---

## 十、风险与限制

| 风险 | 应对 |
|------|------|
| 节点内硬编码了 BNOS GUI API | 运行时设置 `BNOS_RUNTIME=1` 环境变量，节点检查后走纯 CLI 分支 |
| venv 跨机器兼容性 | 复用现有 `_repair_portable_venv` 逻辑 |
| 节点依赖 PySide6 | 依赖分析阶段告警，提供 `--ignore-missing` 跳过 |
| macOS 资源限制 | 仅支持优先级调节，文档注明 |

---

**最后更新**：2026-07-12
**状态**：方案设计，待实施
