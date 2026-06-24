"""
test_node_config_parser.py — NodeConfigParser 单元测试
覆盖: node_config_parser.py (ParameterDef, InputPortDef, OutputPortDef, NodeConfigParser)
"""
import pytest
from ui.core.node_config_parser import (
    NodeConfigParser, ParameterDef, InputPortDef, OutputPortDef
)


# ═══════════════════ ParameterDef ═══════════════════

class TestParameterDef:
    def test_basic_creation(self):
        p = ParameterDef(name="threshold", type="float", label="Threshold", default=0.5)
        assert p.name == "threshold"
        assert p.type == "float"
        assert p.label == "Threshold"
        assert p.default == 0.5
        assert p.required is False
        assert p.min is None
        assert p.max is None
        assert p.options == []

    def test_required_parameter(self):
        p = ParameterDef(name="api_key", type="string", label="API Key", required=True)
        assert p.required is True

    def test_numeric_constraints(self):
        p = ParameterDef(name="ratio", type="float", label="Ratio", min=0.0, max=1.0, step=0.1, decimals=3)
        assert p.min == 0.0
        assert p.max == 1.0
        assert p.step == 0.1
        assert p.decimals == 3

    def test_enum_options(self):
        p = ParameterDef(name="model", type="enum", label="Model", options=["gpt4", "gpt35"])
        assert p.options == ["gpt4", "gpt35"]

    def test_file_constraints(self):
        p = ParameterDef(name="data_file", type="file", label="Data File", file_filter="*.csv")
        assert p.file_filter == "*.csv"

    def test_dynamic_options(self):
        p = ParameterDef(
            name="node_list", type="enum", label="Node",
            dynamic_options={"source": "nodes_data", "key": "name"}
        )
        assert p.dynamic_options == {"source": "nodes_data", "key": "name"}

    def test_text_rows(self):
        p = ParameterDef(name="prompt", type="text", label="Prompt", rows=5)
        assert p.rows == 5
        assert p.type == "text"


# ═══════════════════ InputPortDef ═══════════════════

class TestInputPortDef:
    def test_basic_node_port(self):
        p = InputPortDef(name="input_data", source="node", required=True)
        assert p.name == "input_data"
        assert p.source == "node"
        assert p.required is True
        assert p.type == "default"

    def test_edit_port(self):
        p = InputPortDef(name="prompt", label="Prompt", source="edit", description="User prompt")
        assert p.source == "edit"
        assert p.label == "Prompt"
        assert p.description == "User prompt"

    def test_param_port_default_source_none(self):
        p = InputPortDef(name="config")
        assert p.source is None
        assert p.required is False


# ═══════════════════ OutputPortDef ═══════════════════

class TestOutputPortDef:
    def test_basic_output(self):
        p = OutputPortDef(name="result", label="Result", type="json")
        assert p.name == "result"
        assert p.label == "Result"
        assert p.type == "json"
        assert p.description == ""

    def test_default_type(self):
        p = OutputPortDef(name="data")
        assert p.type == "default"


# ═══════════════════ NodeConfigParser ═══════════════════

class TestNodeConfigParser:
    # ── parse ──
    def test_parse_empty_parameters(self):
        assert NodeConfigParser.parse({}) == []
        assert NodeConfigParser.parse({"parameters": []}) == []

    def test_parse_single_parameter(self):
        config = {"parameters": [{"name": "x", "type": "int", "label": "X"}]}
        result = NodeConfigParser.parse(config)
        assert len(result) == 1
        assert result[0].name == "x"
        assert result[0].type == "int"

    def test_parse_multiple_parameters(self):
        config = {"parameters": [
            {"name": "a", "type": "int", "label": "A"},
            {"name": "b", "type": "float", "label": "B", "default": 0.0},
        ]}
        result = NodeConfigParser.parse(config)
        assert len(result) == 2
        assert result[0].name == "a"
        assert result[1].name == "b"
        assert result[1].default == 0.0

    # ── extract_values ──
    def test_extract_values_empty(self):
        assert NodeConfigParser.extract_values({}) == {}
        assert NodeConfigParser.extract_values({"parameters": []}) == {}

    def test_extract_values_configured(self):
        config = {
            "parameters": [{"name": "model", "type": "enum", "label": "Model", "default": "gpt4"}],
            "model": "gpt35"
        }
        result = NodeConfigParser.extract_values(config)
        assert result["model"] == "gpt35"

    def test_extract_values_fallback_to_default(self):
        config = {
            "parameters": [{"name": "model", "type": "enum", "label": "Model", "default": "gpt4"}],
        }
        result = NodeConfigParser.extract_values(config)
        assert result["model"] == "gpt4"

    # ── has_parameters ──
    def test_has_parameters(self):
        assert NodeConfigParser.has_parameters({"parameters": [{"name": "x"}]}) is True
        assert NodeConfigParser.has_parameters({}) is False
        assert NodeConfigParser.has_parameters({"parameters": []}) is False

    # ── parse_input_ports ──
    def test_parse_input_ports_empty(self):
        assert NodeConfigParser.parse_input_ports({}) == []
        assert NodeConfigParser.parse_input_ports({"input_ports": []}) == []

    def test_parse_input_ports_with_data(self):
        config = {
            "input_ports": [
                {"name": "prompt", "source": "node", "required": True},
                {"name": "config", "source": "edit"},
            ]
        }
        result = NodeConfigParser.parse_input_ports(config)
        assert len(result) == 2
        assert result[0].name == "prompt"
        assert result[0].source == "node"
        assert result[1].name == "config"
        assert result[1].source == "edit"

    # ── has_input_ports ──
    def test_has_input_ports(self):
        assert NodeConfigParser.has_input_ports({"input_ports": [{"name": "x"}]}) is True
        assert NodeConfigParser.has_input_ports({}) is False

    # ── get_input_port_names ──
    def test_get_input_port_names(self):
        config = {
            "input_ports": [
                {"name": "a"}, {"name": "b"}, {"name": "c"}
            ]
        }
        assert NodeConfigParser.get_input_port_names(config) == ["a", "b", "c"]
        assert NodeConfigParser.get_input_port_names({}) == []

    # ── parse_output_ports ──
    def test_parse_output_ports_empty(self):
        assert NodeConfigParser.parse_output_ports({}) == []
        assert NodeConfigParser.parse_output_ports({"output_ports": []}) == []

    def test_parse_output_ports_with_data(self):
        config = {
            "output_ports": [
                {"name": "result", "label": "Result", "type": "json"},
            ]
        }
        result = NodeConfigParser.parse_output_ports(config)
        assert len(result) == 1
        assert result[0].name == "result"
        assert result[0].type == "json"

    # ── has_output_ports ──
    def test_has_output_ports(self):
        assert NodeConfigParser.has_output_ports({"output_ports": [{"name": "x"}]}) is True
        assert NodeConfigParser.has_output_ports({}) is False

    # ── get_output_port_names ──
    def test_get_output_port_names(self):
        config = {"output_ports": [{"name": "out1"}, {"name": "out2"}]}
        assert NodeConfigParser.get_output_port_names(config) == ["out1", "out2"]
        assert NodeConfigParser.get_output_port_names({}) == []
