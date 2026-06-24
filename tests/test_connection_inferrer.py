"""
test_connection_inferrer.py — ConnectionInferrer 单元测试
覆盖: connection_inferrer.py (_extract_node_name_from_path, infer_all_edges, compare_with_existing, get_node_upstream/downstreams, diagnose)
"""
import pytest
from ui.core.connection_inferrer import ConnectionInferrer


# ═══════════════════ 测试数据构造 ═══════════════════

def _make_nodes_data(*entries):
    """构造 nodes_data 字典"""
    result = {}
    for name, config in entries:
        result[name] = {"config": config, "path": f"nodes/{name}", "process": None, "status": "stopped"}
    return result


# ═══════════════════ _extract_node_name_from_path ═══════════════════

class TestExtractNodeName:
    def test_standard_path(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("node_A", {}), ("node_B", {})
        ))
        # nodes/node_A/output.json → node_A
        assert inferrer._extract_node_name_from_path("/project/nodes/node_A/output.json") == "node_A"

    def test_relative_path(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("node_B", {})
        ))
        assert inferrer._extract_node_name_from_path("../node_B/output.json") == "node_B"

    def test_windows_path(self):
        inferrer = ConnectionInferrer("C:/project", _make_nodes_data(
            ("node_C", {})
        ))
        assert inferrer._extract_node_name_from_path("C:/project/nodes/node_C/output.json") == "node_C"

    def test_non_nodes_path_with_known_name(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("my_special_node", {})
        ))
        assert inferrer._extract_node_name_from_path("/data/my_special_node/output.json") == "my_special_node"

    def test_unknown_node_returns_none(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("known_node", {})
        ))
        assert inferrer._extract_node_name_from_path("/some/unknown/path/output.json") is None

    def test_empty_data_returns_none(self):
        inferrer = ConnectionInferrer("/project", {})
        assert inferrer._extract_node_name_from_path("/nodes/anything/output.json") is None


# ═══════════════════ infer_all_edges ═══════════════════

class TestInferAllEdges:
    def test_single_connection(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("node_A", {}),
            ("node_B", {"listen_upper_file": "../node_A/output.json"}),
        ))
        edges = inferrer.infer_all_edges()
        assert len(edges) == 1
        assert edges[0]["source"] == "node_A"
        assert edges[0]["target"] == "node_B"
        assert edges[0]["target_port"] is None

    def test_chain_connection(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {"listen_upper_file": "../A/output.json"}),
            ("C", {"listen_upper_file": "../B/output.json"}),
        ))
        edges = inferrer.infer_all_edges()
        assert len(edges) == 2
        sources = {e["source"] for e in edges}
        assert sources == {"A", "B"}

    def test_no_upstream_orphan(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("orphan", {"listen_upper_file": ""}),
            ("root", {}),
        ))
        edges = inferrer.infer_all_edges()
        assert edges == []  # orphan 无有效 listen_upper_file，不产生边

    def test_multiple_upstreams_via_port_mappings(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {}),
            ("C", {
                "listen_upper_file": "../A/output.json",
                "port_mappings": {
                    "prompt": "../B/output.json",
                }
            }),
        ))
        edges = inferrer.infer_all_edges()
        assert len(edges) == 2
        ports = {(e["source"], e["target_port"]) for e in edges}
        assert ("A", None) in ports
        assert ("B", "prompt") in ports

    def test_ignore_non_string_port_mapping(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("C", {
                "port_mappings": {"invalid": None}
            }),
        ))
        edges = inferrer.infer_all_edges()
        assert edges == []  # None 值被跳过

    def test_empty_nodes_data(self):
        inferrer = ConnectionInferrer("/project", {})
        assert inferrer.infer_all_edges() == []


# ═══════════════════ compare_with_existing ═══════════════════

class TestCompareWithExisting:
    def test_new_edges_detected(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {"listen_upper_file": "../A/output.json"}),
        ))
        result = inferrer.compare_with_existing([])
        assert result["stats"]["new_count"] == 1
        assert len(result["new"]) == 1
        assert result["new"][0]["source"] == "A"

    def test_no_diff_when_identical(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {"listen_upper_file": "../A/output.json"}),
        ))
        result = inferrer.compare_with_existing([{"source": "A", "target": "B"}])
        assert result["stats"]["new_count"] == 0
        assert result["stats"]["missing_count"] == 0
        assert result["stats"]["conflict_count"] == 0

    def test_missing_edges_detected(self):
        """config 中无对应 listen_upper_file 但 canvas 中有连线"""
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {}),
        ))
        result = inferrer.compare_with_existing([{"source": "A", "target": "B"}])
        assert result["stats"]["missing_count"] == 1
        assert result["missing"][0]["source"] == "A"

    def test_conflicts_detected(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("C", {}),
            ("B", {"listen_upper_file": "../C/output.json"}),
        ))
        existing = [{"source": "A", "target": "B"}]
        result = inferrer.compare_with_existing(existing)
        assert result["stats"]["conflict_count"] == 1
        assert result["conflicts"][0]["inferred_source"] == "C"
        assert result["conflicts"][0]["existing_source"] == "A"

    def test_orphans_detected(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("orphan", {"listen_upper_file": ""}),
            ("B", {"listen_upper_file": "../A/output.json"}),
        ))
        result = inferrer.compare_with_existing([])
        assert result["stats"]["orphan_count"] == 2
        assert "orphan" in result["orphans"]
        assert "A" in result["orphans"]

    def test_stats_accurate(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {"listen_upper_file": "../A/output.json"}),
            ("C", {"listen_upper_file": "../B/output.json"}),
        ))
        result = inferrer.compare_with_existing([])
        assert result["stats"]["total_inferred"] == 2
        assert result["stats"]["total_existing"] == 0
        assert result["stats"]["new_count"] == 2

    def test_all_keys_present_in_return(self):
        inferrer = ConnectionInferrer("/project", {})
        result = inferrer.compare_with_existing([])
        for key in ("inferred", "existing", "new", "missing", "conflicts", "orphans", "stats"):
            assert key in result, f"Missing key: {key}"


# ═══════════════════ get_node_upstream / get_node_downstreams ═══════════════════

class TestUpstreamDownstream:
    def test_get_upstream_found(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {"listen_upper_file": "../A/output.json"}),
        ))
        assert inferrer.get_node_upstream("B") == "A"

    def test_get_upstream_not_found(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
        ))
        assert inferrer.get_node_upstream("A") is None  # A 没有 listen_upper_file

    def test_get_upstream_nonexistent_node(self):
        inferrer = ConnectionInferrer("/project", {})
        assert inferrer.get_node_upstream("nonexistent") is None

    def test_get_downstreams(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("source", {}),
            ("A", {"listen_upper_file": "../source/output.json"}),
            ("B", {"listen_upper_file": "../source/output.json"}),
            ("C", {"listen_upper_file": "../A/output.json"}),
        ))
        downstreams = inferrer.get_node_downstreams("source")
        assert set(downstreams) == {"A", "B"}

    def test_get_downstreams_none(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("source", {}),
        ))
        assert inferrer.get_node_downstreams("source") == []


# ═══════════════════ diagnose ═══════════════════

class TestDiagnose:
    def test_diagnose_output_contains_node_names(self):
        inferrer = ConnectionInferrer("/project", _make_nodes_data(
            ("A", {}),
            ("B", {"listen_upper_file": "../A/output.json"}),
        ))
        report = inferrer.diagnose()
        assert "A" in report
        assert "B" in report
        assert "连线反推诊断报告" in report
        assert "推断连线数:" in report
