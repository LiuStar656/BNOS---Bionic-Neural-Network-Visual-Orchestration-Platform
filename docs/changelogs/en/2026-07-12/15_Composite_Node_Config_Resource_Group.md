# 15 Composite Node Config & Resource Group

## Overview

Establishes a formal configuration file system and directory resource group for composite nodes. At its core is the `composite.json` Schema definition, replacing the previous ad-hoc path concatenation scattered across the codebase. It also introduces configuration self-healing — auto-rebuilding from `node_clusters.json` when corrupted — along with a `.archive` mechanism for historical log retention.

---

## Changes

| File | Change | Lines |
|------|--------|:---:|
| `ui/core/node/composite_node.py` | New `CompositeConfig` method group + directory creation / config read-write / registry / decompress cleanup / archive pruning / legacy migration / structure fingerprint / config rebuild | +280 |
| `ui/panels/node_list_ops.py` | `_get_log_files` path fix, adapted to `composite_nodes/<id>/logs/` | ~5 |
| `ui/core/i18n/translation_keys.py` | No new keys (reuses existing) | — |
| `ui/core/i18n/strings_cn.json` | No new entries | — |
| `ui/core/i18n/strings_en.json` | No new entries | — |

### New Methods

> All in `composite_node.py`

| Method | Responsibility |
|--------|----------------|
| `_create_comp_config_dir(comp_id)` | Create `composite_nodes/<id>/` and `logs/` subdirectory |
| `_write_composite_config(comp_id, data)` | Write `composite.json` (with atomic write protection) |
| `_load_composite_config(comp_id)` | Read `composite.json`; auto-rebuild if corrupted |
| `_write_node_registry(comp_id, data)` | Write `node_registry.json` |
| `_load_node_registry(comp_id)` | Read `node_registry.json` |
| `_decompress_cleanup(comp_id)` | Archive logs on decompress → delete everything under `composite_nodes/<id>/` |
| `_prune_archives()` | Prune `.archive`, keep at most 10 versions |
| `_migrate_existing_composites()` | Auto-create config files for legacy composites on startup |
| `_compute_structure_fingerprint(data)` | Compute DAG + port structural fingerprint (used for archive directory naming) |
| `_rebuild_composite_config(comp_id)` | Rebuild corrupted `composite.json` from `node_clusters.json` |

---

## Key Design

### composite.json Schema

```json
{
  "composite_id": "comp_abc123",
  "display_name": "Image Processing Pipeline",
  "dag": {
    "nodes": { "<node_id>": { "type": "...", "config": {...} } },
    "edges": [ { "from": "<node_id>.<port>", "to": "<node_id>.<port>" } ]
  },
  "ports": {
    "inputs":  [ { "key": "image",   "label": "Input Image", "type": "image" } ],
    "outputs": [ { "key": "result",  "label": "Result", "type": "image" } ]
  },
  "resource_budget": {
    "cpu_cores": 4,
    "memory_mb":  2048
  },
  "structure_fingerprint": "a1b2c3d4e5f6",
  "created_at": "2026-07-12T10:30:00",
  "updated_at": "2026-07-12T11:00:00"
}
```

The Schema carries the composite node's **full identity** (id + display_name), **DAG topology** (nodes + edges), **exposed ports** (inputs/outputs), and **resource budget**, making `composite.json` the single source of truth for a composite node.

### node_registry.json Design

```json
{
  "composite_id": "comp_abc123",
  "children": {
    "node_1": { "status": "running", "pid": 12345, "output_path": "..." },
    "node_2": { "status": "running", "pid": 12346, "output_path": "..." },
    "node_3": { "status": "done",    "pid": null,  "output_path": "..." }
  }
}
```

The registry records each child node's **runtime state**, kept separate from the static DAG description in `composite.json`. Runtime information (PID, status, output path) is hot data and should not be mixed into cold configuration.

### Config Corruption Self-Healing

```
_load_composite_config()
    │
    ├── Parse success → return
    │
    └── Parse failure (JSONDecodeError / KeyError)
            │
            ├── Log warning "composite.json corrupted, rebuilding..."
            │
            └── _rebuild_composite_config()
                    │
                    ├── Extract child node list for this composite from node_clusters.json
                    ├── Generate minimal viable composite.json (with DAG and ports)
                    ├── Fingerprint marked as "rebuilt"
                    └── Return recovered config
```

The recovery path guarantees a composite node won't become completely unusable due to a single corrupted config file. The minimal viable version may lose some metadata (e.g., custom resource_budget values), but all core functionality (DAG execution, port mapping) is recoverable.

### Archiving Policy

```
Archive naming convention:
  composite_nodes/.archive/<comp_id>_<structure_fingerprint>_<timestamp>/

Pruning policy (_prune_archives):
  - Keep at most 10 archive versions per comp_id
  - Excess entries are deleted in ascending chronological order (retain the latest 10)
  - Triggered after each _decompress_cleanup
```

The structure fingerprint ensures different DAG/port structure versions are distinguishable; the timestamp provides version traceability; the limit of 10 prevents unbounded disk growth.

---

## File Tree

### Composite Node Runtime Directory

```
composite_nodes/<comp_id>/
├── composite.json              # Identity + DAG + ports + resource budget (Schema defined above)
├── node_registry.json          # Child node runtime state registry
├── logs/                       # Composite node logs
│   ├── composite_output.log    # Orchestrator stdout
│   └── composite_error.log     # Orchestrator stderr
├── orchestrator.py             # Orchestrator script
└── venv/                       # Merged virtual environment
```

### Archive Directory

```
composite_nodes/.archive/
├── comp_abc123_a1b2c3d4e5f6_20260712T103000/
│   ├── composite.json          # Structural snapshot
│   ├── composite_output.log    # Historical logs
│   └── composite_error.log
├── comp_abc123_d4e5f6a1b2c3_20260712T110000/
│   └── ...
└── comp_xyz789_.../
    └── ...
```

---

## Behavioral Changes

### 4.1 Compress (Collapse into Composite Node)

```
Old behavior: Only writes child node data to node_clusters.json, no standalone config file

New behavior:
  1. _create_comp_config_dir(comp_id)     → Create composite_nodes/<id>/ and logs/
  2. _write_composite_config(comp_id)      → Write composite.json
  3. _write_node_registry(comp_id)         → Write node_registry.json
  4. Log output redirected to composite_nodes/<id>/logs/
```

### 4.2 Auto-Migration on Startup

```
_startup_check → _migrate_existing_composites()
    │
    └── Iterate over all composite nodes in node_clusters.json
            │
            └── If composite_nodes/<id>/composite.json does not exist
                    │
                    └── Extract data from node_clusters.json → create config files
```

**Background**: Composite nodes created before this change have no config files. On startup, they are automatically scanned and backfilled, ensuring seamless upgrade for existing projects.

### 4.3 Decompress (Restore to Normal Nodes)

```
Old behavior: Directly restores child nodes; old logs remain in venv/logs (messy)

New behavior:
  1. _decompress_cleanup(comp_id)
       ├── Create .archive/<comp_id>_<fingerprint>_<timestamp>/
       ├── Copy composite.json → archive (structural snapshot)
       ├── Move logs/*.log → archive (historical logs)
       └── Delete everything under composite_nodes/<comp_id>/
  2. _prune_archives() → Prune to 10 archive versions
  3. Restore child nodes to canvas
```

### 4.4 Log Path Migration

```
Old path: venv/logs/composite_output.log  (depends on display_name, unstable)

New path: composite_nodes/<comp_id>/logs/composite_output.log
                                              /composite_error.log
```

Paths are now decoupled from `display_name` and depend only on the immutable `comp_id`. `_get_log_files` in `node_list_ops.py` has been updated accordingly.

### 4.5 Config Corruption Recovery

```
Trigger: composite.json content is corrupted (JSON parse failure or missing required keys)

Recovery flow:
  1. Log warning + corruption reason
  2. Call _rebuild_composite_config(comp_id)
  3. Extract child node topology for this composite from node_clusters.json
  4. Generate minimal viable composite.json and overwrite
  5. structure_fingerprint marked as "rebuilt"
  6. User continues transparently (custom resource_budget may be lost)
```
