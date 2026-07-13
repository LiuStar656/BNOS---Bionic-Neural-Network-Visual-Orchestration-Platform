# 08 Anchor Manager Multi-Output Port Support

## Problem Description

Anchor manager only supported a single output anchor, unable to render multiple custom output ports configured in `node_config.json`.

## Fix Solution

### 8.1 Rewrite Output Anchor Generation

**File**: `ui/canvas/items/anchor_manager.py`

Prioritize `output_ports` configured multiple output ports, fallback to single default output anchor.

**Code Change**:
```python
config_output_ports = {}
for p in NodeConfigParser.parse_output_ports(config):
    config_output_ports[p.name] = p

if config_output_ports:
    port_list = list(config_output_ports.values())
    for port in port_list:
        if port.name in positions:
            # Use configured position
        else:
            # Auto-calculate position
            header_h = 26
            divider = 4
            top = header_h + divider
            available_h = nh - top - 16
            n = len(port_list)
            idx = port_list.index(port)
            if n == 1:
                out_center_y = top + available_h / 2
            else:
                out_center_y = top + (available_h * idx) / (n - 1)
            out_center_x = nw
            out_size = ANCHOR_SIZE_SMALL
        # Create anchor
else:
    # Fallback to single output anchor mode
```

## Modified Files

| File | Change |
|------|--------|
| `ui/canvas/items/anchor_manager.py` | Rewrote output anchor generation for multi-output support |

## Verification

After fix:
- ✅ Supports multiple custom output ports from `node_config.json`
- ✅ Output ports vertically distributed on node right side
- ✅ Prioritizes `row_positions` configured positions
- ✅ Falls back to single default output anchor when no multi-output config

---

**Last Updated**: 2026-07-13
