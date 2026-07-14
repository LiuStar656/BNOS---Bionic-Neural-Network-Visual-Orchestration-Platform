from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ui.core.config.config_merger import get_config_path

if TYPE_CHECKING:
    from ui.core.node.composite_node import CompositeNode

ROUTING_STANDALONE = "STANDALONE"
ROUTING_COMPOSITE_OUTPUT = "COMPOSITE_OUTPUT"
ROUTING_COMPOSITE_INPUT = "COMPOSITE_INPUT"
ROUTING_COMPOSITE_INTERNAL = "COMPOSITE_INTERNAL"
ROUTING_STANDALONE_PORT_MAP = "STANDALONE_PORT_MAP"

VALID_ROUTING_TYPES = frozenset(
    {
        ROUTING_STANDALONE,
        ROUTING_COMPOSITE_OUTPUT,
        ROUTING_COMPOSITE_INPUT,
        ROUTING_COMPOSITE_INTERNAL,
        ROUTING_STANDALONE_PORT_MAP,
    }
)

EdgeKey = tuple[str, str, str, str, str]


def make_edge_key(
    routing_type: str,
    upstream_node_name: str,
    downstream_node_name: str,
    upstream_port: str = "default",
    downstream_port: str = "default",
) -> EdgeKey:
    if routing_type not in VALID_ROUTING_TYPES:
        raise ValueError(f"invalid routing_type: {routing_type}")
    if not upstream_port:
        upstream_port = "default"
    if not downstream_port:
        downstream_port = "default"
    return (
        routing_type,
        upstream_node_name,
        downstream_node_name,
        upstream_port,
        downstream_port,
    )


def parse_edge_key(key: EdgeKey) -> dict[str, str]:
    return {
        "routing_type": key[0],
        "up": key[1],
        "down": key[2],
        "up_port": key[3],
        "down_port": key[4],
    }


def _resolve_node_path(node_name: str, nodes_data: dict) -> str:
    info = nodes_data.get(node_name, {}) if nodes_data else {}
    return str(info.get("path", "") or "")


def _resolve_node_output_path(node_name: str, nodes_data: dict) -> str:
    node_path = _resolve_node_path(node_name, nodes_data)
    if not node_path:
        return ""
    return str((Path(node_path) / "output.json").resolve())


def _resolve_composite_output_node(comp_id: str, out_port: str, composite_manager: CompositeNode | None) -> str:
    if composite_manager is None:
        return ""
    internal_name = ""
    if hasattr(composite_manager, "_find_internal_by_port"):
        try:
            internal_name = composite_manager._find_internal_by_port(comp_id, out_port, "output")
        except Exception:
            internal_name = ""
    if not internal_name and out_port == "default" and hasattr(composite_manager, "_find_exit_node"):
        try:
            internal_name = composite_manager._find_exit_node(comp_id)
        except Exception:
            internal_name = ""
    return internal_name or ""


def _resolve_composite_input_node(
    comp_id: str, in_port: str, composite_manager: CompositeNode | None
) -> tuple[str, str]:
    if composite_manager is None:
        return "", in_port
    internal_name = ""
    actual_port = in_port
    if hasattr(composite_manager, "_find_internal_by_port"):
        try:
            internal_name = composite_manager._find_internal_by_port(comp_id, in_port, "input")
        except Exception:
            internal_name = ""
    if not internal_name and in_port == "default" and hasattr(composite_manager, "_find_entry_node"):
        try:
            internal_name = composite_manager._find_entry_node(comp_id)
            actual_port = "data"
        except Exception:
            internal_name = ""
            actual_port = in_port
    return (internal_name or "", actual_port)


def edge_upstream_output_path(key: EdgeKey, nodes_data: dict, composite_manager: CompositeNode | None = None) -> str:
    routing_type, up, _down, up_port, _dn_port = key
    if routing_type in (
        ROUTING_STANDALONE,
        ROUTING_COMPOSITE_INPUT,
        ROUTING_STANDALONE_PORT_MAP,
        ROUTING_COMPOSITE_INTERNAL,
    ):
        return _resolve_node_output_path(up, nodes_data)
    if routing_type == ROUTING_COMPOSITE_OUTPUT:
        internal_node = _resolve_composite_output_node(up, up_port, composite_manager)
        if not internal_node:
            return ""
        return _resolve_node_output_path(internal_node, nodes_data)
    return ""


def _resolve_composite_config_path(comp_id: str, nodes_data: dict) -> str:
    node_path = _resolve_node_path(comp_id, nodes_data)
    if not node_path:
        return ""
    return str((Path(node_path) / "composite.json").resolve())


def edge_downstream_targets(
    key: EdgeKey, nodes_data: dict, composite_manager: CompositeNode | None = None
) -> list[dict[str, Any]]:
    """
    把「这条边需要修改的所有配置字段」列成 plan，供 EdgeConfigWriter 写入 RouteCache。
    返回 list[dict]，每条 dict 的字段：
      - kind: "listen_upper_file" / "port_mapping" / "composite_input_routing" / "composite_output_routing"
      - cfg_path: 要改的配置文件绝对路径（node_config.json 或 composite.json）
      - value: 写入该字段的值（删除时 plan_remove_edge 会忽略 value，直接按 kind/port 清）
      - port: kind=="port_mapping"/composite routing 时的端口名
      - comp_id: kind==composite_* 时的复合节点 id
      - route: kind==composite_*_routing 时的 routing dict（供 RouteCache.set_composite_input_routing 用）
    """
    routing_type, up, down, _up_port, dn_port = key
    src_output_path = edge_upstream_output_path(key, nodes_data, composite_manager)
    results: list[dict[str, Any]] = []

    if routing_type in (ROUTING_STANDALONE, ROUTING_STANDALONE_PORT_MAP):
        node_path = _resolve_node_path(down, nodes_data)
        if not node_path:
            return results
        cfg_path = get_config_path(node_path)
        if routing_type == ROUTING_STANDALONE_PORT_MAP or (dn_port and dn_port != "default"):
            results.append(
                {
                    "kind": "port_mapping",
                    "cfg_path": str(cfg_path),
                    "port": dn_port,
                    "value": src_output_path,
                }
            )
        else:
            results.append(
                {
                    "kind": "listen_upper_file",
                    "cfg_path": str(cfg_path),
                    "value": src_output_path,
                }
            )
        up_path = _resolve_node_path(up, nodes_data)
        if up_path:
            up_cfg_path = get_config_path(up_path)
            results.append(
                {
                    "kind": "out_connection",
                    "cfg_path": str(up_cfg_path),
                    "port": _up_port,
                    "value": f"{down}|{dn_port}",
                }
            )
        return results

    if routing_type == ROUTING_COMPOSITE_OUTPUT:
        node_path = _resolve_node_path(down, nodes_data)
        if node_path:
            cfg_path = get_config_path(node_path)
            if dn_port and dn_port != "default":
                results.append(
                    {
                        "kind": "port_mapping",
                        "cfg_path": str(cfg_path),
                        "port": dn_port,
                        "value": src_output_path,
                    }
                )
            else:
                results.append(
                    {
                        "kind": "listen_upper_file",
                        "cfg_path": str(cfg_path),
                        "value": src_output_path,
                    }
                )
        comp_cfg_path = _resolve_composite_config_path(up, nodes_data)
        if comp_cfg_path:
            results.append(
                {
                    "kind": "composite_output_routing",
                    "cfg_path": str(comp_cfg_path),
                    "comp_id": up,
                    "port": _up_port,
                    "route": {
                        "target_node": down,
                        "target_port": dn_port or "default",
                    },
                }
            )
        return results

    if routing_type == ROUTING_COMPOSITE_INPUT:
        up_path = _resolve_node_path(up, nodes_data)
        internal_name, actual_in_port = _resolve_composite_input_node(down, dn_port, composite_manager)
        if up_path and internal_name:
            up_cfg_path = get_config_path(up_path)
            results.append(
                {
                    "kind": "out_connection",
                    "cfg_path": str(up_cfg_path),
                    "port": _up_port,
                    "value": f"{internal_name}|{actual_in_port}",
                }
            )
        comp_cfg_path = _resolve_composite_config_path(down, nodes_data)
        if comp_cfg_path:
            results.append(
                {
                    "kind": "composite_input_routing",
                    "cfg_path": str(comp_cfg_path),
                    "comp_id": down,
                    "port": dn_port,
                    "route": {
                        "source_output_path": src_output_path,
                        "target_node": internal_name or "",
                        "target_port": actual_in_port or "default",
                    },
                }
            )
        return results

    if routing_type == ROUTING_COMPOSITE_INTERNAL:
        parent_comp_id = ""
        if composite_manager and hasattr(composite_manager, "_composites"):
            for cid, comp in (composite_manager._composites or {}).items():
                children = comp.get("children") or comp.get("nodes") or []
                if up in children and down in children:
                    parent_comp_id = cid
                    break
        dn_path = _resolve_node_path(down, nodes_data)
        if dn_path:
            dn_cfg_path = get_config_path(dn_path)
            if dn_port and dn_port != "default":
                results.append(
                    {
                        "kind": "port_mapping",
                        "cfg_path": str(dn_cfg_path),
                        "port": dn_port,
                        "value": src_output_path,
                    }
                )
            else:
                results.append(
                    {
                        "kind": "listen_upper_file",
                        "cfg_path": str(dn_cfg_path),
                        "value": src_output_path,
                    }
                )
        up_path = _resolve_node_path(up, nodes_data)
        if up_path:
            up_cfg_path = get_config_path(up_path)
            results.append(
                {
                    "kind": "out_connection",
                    "cfg_path": str(up_cfg_path),
                    "port": _up_port,
                    "value": f"{down}|{dn_port}",
                }
            )
        if parent_comp_id:
            comp_cfg_path = _resolve_composite_config_path(parent_comp_id, nodes_data)
            if comp_cfg_path:
                results.append(
                    {
                        "kind": "composite_internal_edge_ref",
                        "cfg_path": str(comp_cfg_path),
                        "comp_id": parent_comp_id,
                        "value": f"{up}->{down}",
                    }
                )
        return results
    return results


def edge_key_is_valid(key: EdgeKey, nodes_data: dict, composite_manager: CompositeNode | None = None) -> bool:
    if len(key) != 5:
        return False
    routing_type = key[0]
    if routing_type not in VALID_ROUTING_TYPES:
        return False
    if not key[1] or not key[2]:
        return False
    src = edge_upstream_output_path(key, nodes_data, composite_manager)
    if not src:
        return False
    return True
