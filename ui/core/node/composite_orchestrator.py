"""
ui/core/composite_orchestrator.py
复合节点编排器脚本生成器。

生成独立的 Python 脚本（orchestrator_{comp_id}.py），
在拓扑 DAG 顺序下串联执行子节点。
"""

from __future__ import annotations

import json as _json


def render_orchestrator_script(comp_id: str, node_modules: list, dag: list, external_ports: dict) -> str:
    """生成 orchestrator.py 源代码字符串。"""
    return f'''"""
自动生成的复合节点编排器 — {comp_id}
"""
import sys, os, json, importlib, traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

NODES = {_json.dumps(node_modules, ensure_ascii=False)}
DAG = {_json.dumps(dag, ensure_ascii=False)}

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
        self._run_id = uuid.uuid4().hex[:12]
        self._run_ts = time.strftime("%Y-%m-%d %H:%M:%S")
        ctx = {{}}
        for node_name in self._topo_sort():
            inp = self._build_input(node_name, ctx)
            if external_input and node_name == self._find_entry_node():
                inp["data"].update(external_input)
            try:
                out = self._modules[node_name].process(inp)
                ctx[node_name] = out
                self._write_output(node_name, out)
            except Exception as e:
                print(f"[{comp_id}] ERR {{node_name}}: {{e}}")
        return ctx

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

    def _build_input(self, node_name, ctx):
        inp = {{"data": {{}}}}
        for e in DAG:
            if e["to"] == node_name:
                upstream = ctx.get(e["from"], {{}})
                port = e.get("target_port") or ""
                if port: inp["data"][port] = upstream
                else: inp["data"].update(upstream)
        return inp

    def _find_entry_node(self):
        targets = set(e["to"] for e in DAG)
        for e in DAG:
            if e["from"] not in targets:
                return e["from"]
        return DAG[0]["from"] if DAG else ""

    def _write_output(self, node_name, output):
        for n in NODES:
            if n["name"] == node_name:
                path = PROJECT_ROOT / n["path"] / "output.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                if not isinstance(output, dict): output = {{"data": output}}
                if "code" not in output: output["code"] = 0
                output["run_id"] = self._run_id
                output["timestamp"] = self._run_ts
                path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
                break

if __name__ == "__main__":
    pid = os.getpid()
    pid_path = PROJECT_ROOT / ".pid"
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
                            # 提取 data 字段作为输入
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
