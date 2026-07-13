"""
ui/core/composite_orchestrator.py
复合节点编排器脚本生成器。

生成独立的 Python 脚本（orchestrator.py），采用 listener.py 相同的轮询+防重模式：
- while True 轮询 _port_routing.input 上游文件
- 通过 input_filter_rules 做数据类型过滤（等同入口节点 node_config.json 规则）
- _processed_{comp_id} 防重标记写入上游文件
- 从 pipeline.json 读取 DAG 拓扑，拓扑顺序下串联执行子节点
"""

from __future__ import annotations


def render_orchestrator_script(comp_id: str) -> str:
    """生成 orchestrator.py 源代码字符串。

    orchestrator.py 是复合节点的常驻编排进程，采用与 listener.py 相同的业务逻辑：
    轮询上游 output.json → 过滤匹配 → 执行 DAG → 产出 output → 写防重标记。
    """
    return f'''"""
自动生成的复合节点编排器 — {comp_id}
常驻轮询模式（与 listener.py 业务逻辑一致）
"""
import sys, os, json, subprocess, traceback, time, signal, atexit
from pathlib import Path
from datetime import datetime

COMP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = COMP_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ==================== 配置加载 ====================

PIPELINE_PATH = COMP_DIR / "pipeline.json"

def _load_pipeline():
    return json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))

PIPELINE = _load_pipeline()
NODES = PIPELINE["nodes"]
DAG = PIPELINE["edges"]

INPUT_FILTER_RULES = PIPELINE.get("input_filter_rules", {{}})
MY_FILTER = INPUT_FILTER_RULES.get("filter", {{}})

OUTPUT_DIR = COMP_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = COMP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log(msg, level="INFO"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{{now}}] [{{level}}] [{comp_id}] {{msg}}"
    print(line)
    try:
        with (LOG_DIR / "composite_orchestrator.log").open("a", encoding="utf-8") as f:
            f.write(line + "\\n")
    except OSError:
        pass

# ==================== PID / 优雅退出 ====================

RUNNING = True

PID_PATH = COMP_DIR / ".pid"

def _write_pid():
    PID_PATH.write_text(str(os.getpid()))

def _cleanup_pid():
    try:
        if PID_PATH.exists():
            PID_PATH.unlink()
    except OSError:
        pass

def signal_handler(signum, frame):
    global RUNNING
    log("收到退出信号，准备退出...", "WARNING")
    RUNNING = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(_cleanup_pid)

# ==================== 数据类型过滤 ====================

_PROCESSED_FLAG = "_processed_{comp_id}"

def _is_my_data(data):
    """检查数据是否匹配 input_filter_rules.filter。

    等同入口节点 listener.py 的 is_my_data() 逻辑：
    如果 filter 为空则不限制；否则所有 key-value 必须完全匹配。
    """
    if not MY_FILTER:
        return True
    for k, v in MY_FILTER.items():
        if data.get(k) != v:
            return False
    return True

# ==================== DAG 执行引擎 ====================

class DagRunner:
    """DAG 拓扑执行器 — 每次轮询命中时运行一次完整的 DAG。

    通过 subprocess 调用每个子节点的 main.py（与 listener.py 完全一致），
    数据格式对齐：传入上游 output.json 的完整字典，接收 main.py stdout 输出的 JSON。
    """

    def __init__(self):
        self._node_paths = {{}}
        for n in NODES:
            path = n["path"]
            p = Path(path)
            if p.is_absolute():
                self._node_paths[n["name"]] = p
            else:
                self._node_paths[n["name"]] = PROJECT_ROOT / path

    @staticmethod
    def _get_venv_python(node_dir):
        """获取节点 venv 中的 Python 解释器路径。"""
        candidates = [
            node_dir / "venv" / "Scripts" / "python.exe",
            node_dir / "venv" / "bin" / "python",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return sys.executable

    def run(self, external_input=None):
        import uuid
        self._run_id = uuid.uuid4().hex[:12]
        self._run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ctx = {{}}

        for level in self._topo_sort_levels():
            if len(level) == 1:
                node_name = level[0]
                ok, out = self._process_node(node_name, ctx, external_input)
                if not ok:
                    return {{"code": -1, "error": f"node {{node_name}} failed"}}
                ctx[node_name] = out
            else:
                log(f"并行执行 {{len(level)}} 节点: {{', '.join(level)}}")
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=len(level)) as executor:
                    futures = {{}}
                    for n in level:
                        # 每个节点使用独立的 ctx 快照（只读）
                        futures[executor.submit(
                            self._process_node, n, dict(ctx), external_input
                        )] = n
                    for future in as_completed(futures):
                        n = futures[future]
                        try:
                            ok, result = future.result()
                            if ok:
                                ctx[n] = result
                            else:
                                log(f"ERR {{n}} (parallel) failed", "ERROR")
                        except Exception as e:
                            log(f"ERR {{n}} (parallel): {{e}}", "ERROR")
        return ctx

    def _process_node(self, node_name, ctx, external_input):
        """通过 subprocess 调用 main.py，与 listener.py 完全一致。"""
        node_dir = self._node_paths.get(node_name)
        if not node_dir:
            log(f"FAIL_FIND {{node_name}}: path not found", "ERROR")
            return False, None

        py_path = self._get_venv_python(node_dir)
        main_py = node_dir / "main.py"
        if not main_py.exists():
            log(f"FAIL_FIND {{node_name}}: main.py not found", "ERROR")
            return False, None

        # ── 构造输入（对齐 listener.py 的 json.dumps(data) 格式）──
        inp = self._build_input(node_name, ctx)
        if external_input and node_name == self._find_entry_node():
            inp.update(external_input)

        try:
            input_json = json.dumps(inp, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            log(f"FAIL_INPUT {{node_name}}: {{e}}", "ERROR")
            return False, None

        # ── 调用子进程 ──
        try:
            res = subprocess.run(
                [py_path, str(main_py), input_json],
                capture_output=True, text=True, encoding="utf-8", timeout=60
            )
        except subprocess.TimeoutExpired:
            log(f"FAIL_TIMEOUT {{node_name}} (60s)", "ERROR")
            return False, None
        except FileNotFoundError:
            log(f"FAIL_VENV {{node_name}}: python not found at {{py_path}}", "ERROR")
            return False, None
        except Exception as e:
            log(f"FAIL_SUBPROCESS {{node_name}}: {{e}}", "ERROR")
            return False, None

        if res.returncode != 0:
            stderr = res.stderr.strip() if res.stderr else "no stderr"
            log(f"FAIL_RUN {{node_name}} (rc={{res.returncode}}): {{stderr}}", "ERROR")
            return False, None

        output_text = res.stdout.strip()
        if not output_text:
            log(f"WARN_EMPTY {{node_name}}: stdout 为空", "WARNING")
            return False, None

        try:
            out = json.loads(output_text)
        except json.JSONDecodeError:
            log(f"FAIL_JSON {{node_name}}: {{output_text[:200]}}", "ERROR")
            return False, None

        # ── 写入 output ──
        self._write_output(node_name, out)
        return True, out

    def _topo_sort_levels(self):
        nodes = set()
        for e in DAG:
            nodes.add(e["from"])
            nodes.add(e["to"])
        in_deg = {{n: 0 for n in nodes}}
        adj = {{n: [] for n in nodes}}
        for e in DAG:
            adj[e["from"]].append(e["to"])
            in_deg[e["to"]] += 1
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
        """从 ctx 中提取上游节点的输出，直接作为当前节点的输入。

        与 listener.py 一致：上游 output.json 的完整字典直接传给 main.py。
        """
        inp = {{}}
        for e in DAG:
            if e["to"] == node_name:
                upstream = ctx.get(e["from"], {{}})
                port = e.get("target_port") or ""
                if port:
                    inp[port] = upstream
                else:
                    inp.update(upstream)
        return inp

    def _find_entry_node(self):
        targets = set(e["to"] for e in DAG)
        for e in DAG:
            if e["from"] not in targets:
                return e["from"]
        return DAG[0]["from"] if DAG else ""

    def _find_leaf_nodes(self):
        """找出 DAG 中没有出边的叶子节点。"""
        sources = set(e["from"] for e in DAG)
        targets = set(e["to"] for e in DAG)
        return [n for n in targets if n not in sources] or [DAG[-1]["to"]] if DAG else []

    def _write_output(self, node_name, output):
        if not isinstance(output, dict):
            output = {{"data": output}}
        if "code" not in output:
            output["code"] = 0
        output["run_id"] = self._run_id
        output["timestamp"] = self._run_ts

        payload = json.dumps(output, ensure_ascii=False, indent=2)

        # 1. 写到复合节点存档目录
        archive_path = OUTPUT_DIR / f"{{node_name}}.output.json"
        try:
            archive_path.write_text(payload, encoding="utf-8")
        except OSError as e:
            log(f"WARN 写入存档 output.json 失败: {{e}}", "WARNING")

        # 2. 同时写到子节点自己的目录（下游节点直接监听）
        node_dir = self._node_paths.get(node_name)
        if node_dir:
            node_output = node_dir / "output.json"
            try:
                node_output.write_text(payload, encoding="utf-8")
                log(f"同步子节点 output: {{node_name}}")
            except OSError as e:
                log(f"WARN 写入子节点 output.json 失败: {{e}}", "WARNING")

# ==================== 外部输入读取 ====================

def _read_external_input():
    """从 node_clusters.json 的 _port_routing.input 读取外部节点数据。

    返回: (external_input dict 或 None, 所有上游文件均已就绪的 bool)
    """
    clusters_path = PROJECT_ROOT / "node_clusters.json"
    if not clusters_path.exists():
        return None, False

    try:
        clusters = json.loads(clusters_path.read_text(encoding="utf-8"))
        comp_data = clusters.get("composites", {{}}).get("{comp_id}", {{}})
        routing = comp_data.get("_port_routing", {{}})
        input_routes = routing.get("input", {{}})
    except Exception as e:
        log(f"读取 node_clusters.json 失败: {{e}}", "ERROR")
        return None, False

    if not input_routes:
        return None, True  # 无外部输入端口，视为就绪

    external_input = {{}}
    all_ready = True

    for port_name, route in input_routes.items():
        src_path = route.get("source_output_path", "")
        if not src_path:
            all_ready = False
            continue

        src_file = Path(src_path)
        if not src_file.exists():
            all_ready = False
            continue

        try:
            src_data = json.loads(src_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            all_ready = False
            continue

        # ── 防重：检查是否已被本复合节点处理过 ──
        if src_data.get(_PROCESSED_FLAG):
            # 已被消费过，跳过本次（等待上游产出新数据）
            all_ready = False
            continue

        # ── 数据类型过滤 ──
        if not _is_my_data(src_data):
            # 数据类型不匹配，等待匹配的数据
            all_ready = False
            continue

        src_payload = src_data.get("data", src_data)
        external_input[port_name] = src_payload

    return external_input, all_ready

def _write_processed_flags():
    """在所有上游文件中写入 _processed 防重标记。"""
    clusters_path = PROJECT_ROOT / "node_clusters.json"
    if not clusters_path.exists():
        return

    try:
        clusters = json.loads(clusters_path.read_text(encoding="utf-8"))
        comp_data = clusters.get("composites", {{}}).get("{comp_id}", {{}})
        routing = comp_data.get("_port_routing", {{}})
        input_routes = routing.get("input", {{}})
    except Exception:
        return

    for port_name, route in input_routes.items():
        src_path = route.get("source_output_path", "")
        if not src_path:
            continue
        src_file = Path(src_path)
        if not src_file.exists():
            continue
        try:
            data = json.loads(src_file.read_text(encoding="utf-8"))
            data[_PROCESSED_FLAG] = True
            src_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"已写防重标记: {{src_path}} <- {{_PROCESSED_FLAG}}")
        except Exception as e:
            log(f"写防重标记失败 {{src_path}}: {{e}}", "ERROR")

# ==================== pipe.json 信号文件检查 ====================

def _should_reload_pipeline():
    """检查 COMP_DIR / .pipe 信号文件，若存在则重新加载 pipeline.json。

    .pipe 文件由 BNOS 在用户修改 DAG（展开后重连再折叠）时写入。
    """
    pipe_path = COMP_DIR / ".pipe"
    if pipe_path.exists():
        try:
            pipe_path.unlink()
            return True
        except OSError:
            pass
    return False

def _reload_pipeline():
    global PIPELINE, NODES, DAG, INPUT_FILTER_RULES, MY_FILTER
    PIPELINE = _load_pipeline()
    NODES = PIPELINE["nodes"]
    DAG = PIPELINE["edges"]
    INPUT_FILTER_RULES = PIPELINE.get("input_filter_rules", {{}})
    MY_FILTER = INPUT_FILTER_RULES.get("filter", {{}})
    log("pipeline.json 已重新加载")

# ==================== 主循环 ====================

def _has_outputs():
    """检查是否有 output 目录且包含 output.json 文件。"""
    if not OUTPUT_DIR.exists():
        return False
    return any(f.suffix == ".json" for f in OUTPUT_DIR.iterdir())

def main():
    _write_pid()
    log("=" * 50)
    log(f"复合节点编排器启动")
    log(f"监听类型: _port_routing.input")
    log(f"过滤规则: {{MY_FILTER}}")
    log(f"防重标记: {{_PROCESSED_FLAG}}")
    log("=" * 50)

    global RUNNING

    while RUNNING:
        try:
            # ── 检测 pipeline 更新信号 ──
            pipeline_reloaded = _should_reload_pipeline()
            if pipeline_reloaded:
                _reload_pipeline()

            # ── 读取外部输入 ──
            external_input, all_ready = _read_external_input()

            if not all_ready:
                time.sleep(0.2)
                continue

            # ── 无外部输入端口时：仅执行一次，之后等待信号 ──
            clusters_path = PROJECT_ROOT / "node_clusters.json"
            has_input_routes = False
            if clusters_path.exists():
                try:
                    clusters = json.loads(clusters_path.read_text(encoding="utf-8"))
                    comp_data = clusters.get("composites", {{}}).get("{comp_id}", {{}})
                    routing = comp_data.get("_port_routing", {{}})
                    has_input_routes = bool(routing.get("input", {{}}))
                except Exception:
                    pass

            if not has_input_routes and _has_outputs() and not pipeline_reloaded:
                # 无外部输入且已有输出 → 仅在 .pipe 信号触发时重跑
                time.sleep(0.5)
                continue

            # ── 所有上游数据就绪 → 执行 DAG ──
            log("上游数据就绪，开始执行 DAG")
            runner = DagRunner()
            result = runner.run(external_input=external_input)
            log("DAG 执行完成")

            # ── 仅在 DAG 成功执行后写防重标记 ──
            if isinstance(result, dict) and result.get("code") != -1:
                _write_processed_flags()

                # ── 写复合节点最终结果 ──
                for leaf in runner._find_leaf_nodes():
                    leaf_output = result.get(leaf)
                    if leaf_output:
                        final = dict(leaf_output)
                        final.pop("run_id", None)
                        final.pop("timestamp", None)
                        final_path = COMP_DIR / "output.json"
                        try:
                            final_path.write_text(
                                json.dumps(final, ensure_ascii=False, indent=2),
                                encoding="utf-8"
                            )
                            log(f"已写复合节点最终结果: {{final_path}}")
                        except OSError as e:
                            log(f"WARN 写入最终结果失败: {{e}}", "WARNING")
            else:
                log("DAG 执行异常，未写防重标记，等待重试", "WARNING")

        except json.JSONDecodeError:
            log("数据包格式错误", "ERROR")
            time.sleep(0.2)
        except Exception as e:
            log(f"异常: {{e}}", "ERROR")
            traceback.print_exc()
            time.sleep(0.2)

        time.sleep(0.2)

    log("编排器已退出")

if __name__ == "__main__":
    main()
'''
