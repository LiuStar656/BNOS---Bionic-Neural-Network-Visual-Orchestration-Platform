"""
ui/core/composite_orchestrator.py
复合节点编排器脚本生成器。

生成独立的 Python 脚本（orchestrator.py），
从 pipeline.json 读取 DAG 拓扑，在拓扑顺序下串联执行子节点。
"""

from __future__ import annotations


def render_orchestrator_script(comp_id: str) -> str:
    """生成 orchestrator.py 源代码字符串。\n\n    DAG 不再硬编码，运行时从同目录的 pipeline.json 读取。\n    output 缓存写入 composite_nodes/<comp_id>/output/。\n"""
    return f'''"""
自动生成的复合节点编排器 — {comp_id}
"""
import sys, os, json, importlib, traceback
from pathlib import Path

COMP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = COMP_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 从 pipeline.json 读取 DAG（不再硬编码）
PIPELINE = json.loads((COMP_DIR / "pipeline.json").read_text(encoding="utf-8"))
NODES = PIPELINE["nodes"]
DAG = PIPELINE["edges"]

# output 缓存目录（隔离在 composite_nodes 下）
OUTPUT_DIR = COMP_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class DagRunner:
    def __init__(self):
        self._modules = {{}}
        self._failed = set()
        for n in NODES:
            try:
                self._modules[n["name"]] = importlib.import_module(n["module"])
            except Exception as e:
                print(f"[{comp_id}] FAIL_IMPORT {{n['name']}}: {{e}}")
                self._failed.add(n["name"])
                self._modules[n["name"]] = None

    def run(self, external_input=None):
        # S09: 任 main.py 导入失败则中止，避免下游拿空数据连锁失败
        if self._failed:
            failed_list = ", ".join(sorted(self._failed))
            print(f"[{comp_id}] 以下节点导入失败，中止执行: {{failed_list}}")
            return {{"code": -1, "error": f"import failed: {{failed_list}}"}}
        import time, uuid
        from concurrent.futures import ThreadPoolExecutor, as_completed
        self._run_id = uuid.uuid4().hex[:12]
        self._run_ts = time.strftime("%Y-%m-%d %H:%M:%S")
        ctx = {{}}

        for level in self._topo_sort_levels():
            if len(level) == 1:
                # 单节点层级：串行（无并行开销）
                node_name = level[0]
                self._process_node(node_name, ctx, external_input)
            else:
                # 多节点层级：并行执行
                print(f"[{comp_id}] 并行执行 {{len(level)}} 节点: {{', '.join(level)}}")
                with ThreadPoolExecutor(max_workers=len(level)) as executor:
                    futures = {{
                        executor.submit(self._process_node, n, ctx, external_input): n
                        for n in level
                    }}
                    for future in as_completed(futures):
                        n = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            print(f"[{comp_id}] ERR {{n}} (parallel): {{e}}")
        return ctx

    def _process_node(self, node_name, ctx, external_input):
        """处理单个节点的完整流程（供串行或并行调用）。"""
        inp = self._build_input(node_name, ctx)
        if external_input and node_name == self._find_entry_node():
            inp["data"].update(external_input)
        cached = self._try_read_cache(node_name)
        if cached is not None:
            print(f"[{comp_id}] SKIP {{node_name}} (cached)")
            ctx[node_name] = cached
            return
        out = self._modules[node_name].process(inp)
        ctx[node_name] = out
        self._write_output(node_name, out)

    def _topo_sort(self):
        nodes = set()
        for e in DAG: nodes.add(e["from"]); nodes.add(e["to"])
        degree = {{n: 0 for n in nodes}}
        adj = {{n: [] for n in nodes}}
        for e in DAG: adj[e["from"]].append(e["to"]); degree[e["to"]] += 1
        q = [n for n in nodes if degree[n] == 0]
        result = []
        while q:
            n = q.pop(0); result.append(n)
            for nb in adj[n]:
                degree[nb] -= 1
                if degree[nb] == 0: q.append(nb)
        return result

    def _topo_sort_levels(self):
        """拓扑排序按层级分组：[[A], [B, C], [D]]。
        同层级节点共享相同的前驱集，可安全并行。"""
        nodes = set()
        for e in DAG: nodes.add(e["from"]); nodes.add(e["to"])
        in_deg = {{n: 0 for n in nodes}}
        adj = {{n: [] for n in nodes}}
        for e in DAG: adj[e["from"]].append(e["to"]); in_deg[e["to"]] += 1
        q = [n for n in nodes if in_deg[n] == 0]
        levels = []
        while q:
            level = list(q)
            levels.append(level)
            q = []
            for n in level:
                for nb in adj[n]:
                    in_deg[nb] -= 1
                    if in_deg[nb] == 0:
                        q.append(nb)
        return levels

    def _build_input(self, node_name, ctx):
        inp = {{"data": {{}}}}
        for e in DAG:
            if e["to"] == node_name:
                upstream = ctx.get(e["from"], {{}})
                port = e.get("target_port") or ""
                if port: inp["data"][port] = upstream
                else: inp["data"].update(upstream)
        return inp

    def _try_read_cache(self, node_name):
        path = OUTPUT_DIR / f"{{node_name}}.output.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "run_id" in data:
                    return {{k: v for k, v in data.items() if k != "run_id"}}
            except (ValueError, OSError):
                pass
        return None

    def _find_entry_node(self):
        targets = set(e["to"] for e in DAG)
        for e in DAG:
            if e["from"] not in targets:
                return e["from"]
        return DAG[0]["from"] if DAG else ""

    def _write_output(self, node_name, output):
        path = OUTPUT_DIR / f"{{node_name}}.output.json"
        if not isinstance(output, dict): output = {{"data": output}}
        if "code" not in output: output["code"] = 0
        output["run_id"] = self._run_id
        output["timestamp"] = self._run_ts
        try:
            path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            print(f"[{comp_id}] WARN 写入 output.json 失败: {{e}}", file=sys.stderr)

if __name__ == "__main__":
    pid = os.getpid()
    pid_path = COMP_DIR / ".pid"
    pid_path.write_text(str(pid))
    print(f"[{comp_id}] PID={{pid}} 就绪")

    # ── 从 _port_routing 读取外部输入 ──
    external_input = None
    clusters_path = PROJECT_ROOT / "node_clusters.json"
    if clusters_path.exists():
        try:
            clusters = json.loads(clusters_path.read_text(encoding="utf-8"))
            comp_data = clusters.get("composites", {{}}).get("{comp_id}", {{}})
            routing = comp_data.get("_port_routing", {{}})
            input_routes = routing.get("input", {{}})
            if input_routes:
                external_input = {{}}
                for port_name, route in input_routes.items():
                    src_path = route.get("source_output_path", "")
                    if src_path and Path(src_path).exists():
                        try:
                            src_data = json.loads(Path(src_path).read_text(encoding="utf-8"))
                            src_payload = src_data.get("data", src_data)
                            external_input[port_name] = src_payload
                            print(f"[{comp_id}] 读取外部输入 {{port_name}} ← {{src_path}}")
                        except Exception as e:
                            print(f"[{comp_id}] 读取外部输入失败 {{port_name}}({{src_path}}): {{e}}")
        except Exception as e:
            print(f"[{comp_id}] 读取 node_clusters.json 失败: {{e}}")

    runner = DagRunner()
    result = runner.run(external_input=external_input)
    print(f"[{comp_id}] 完成")
    try: pid_path.unlink()
    except OSError: pass
'''
