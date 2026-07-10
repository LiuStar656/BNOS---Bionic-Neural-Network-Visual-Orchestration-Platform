# Global Defensive Mechanisms

## Overview

Conducted three rounds of comprehensive defensive scanning and fixes across the BNOS client, covering 8 dimensions: process management, file persistence, signal lifecycle, resource cleanup, path security, thread safety, config validation, and concurrency control — totaling **40 defensive mechanisms**.

## Round 1: Composite Node Defenses (11 items)

Defenses for the composite node lifecycle (compress -> run -> decompress -> persist):

| ID | Mechanism | File |
|------|------|------|
| S01 | DAG cycle detection | `composite_node.py` |
| S02 | Prevent compression while nodes running | `composite_node.py` |
| S03 | Restore composites on canvas load | `canvas_view.py` |
| S04 | Prevent mode switch while running | `composite_node.py` |
| S05 | Decompress confirmation dialog | `canvas_menus.py` |
| S06 | Nested composite prevention | `composite_node.py` |
| S07 | Minimum node count check | `composite_node.py` |
| S08 | 0.3s health check after Popen | `composite_node.py` |
| S09 | Abort remaining nodes on import failure | `composite_node.py` |
| S10 | Orphan node warning | `composite_node.py` |
| S14 | Real-time position persistence | `composite_node_item.py` |

## Round 2: Global Client Defenses (13 items)

| ID | Mechanism | File |
|------|------|------|
| F01 | Auto-stop process when deleting running node | `canvas_node_manager.py` |
| F02 | List running nodes in batch delete, auto-stop | `canvas_batch_ops.py` |
| F03 | Running status warning in delete confirm dialog | `node_list_ops.py` |
| F04 | Atomic write for canvas_layout.json | `canvas_layout.py` |
| F05 | Atomic write for node_groups.json | `node_group_manager.py` |
| F06 | Atomic write for node_clusters.json | `composite_node.py` |
| F07 | 6 type validations in config.json parsing | `node_config_parser.py` |
| F08 | Bare except -> except Exception | `terminal_process.py` |
| F09 | ValueError separation in _read_pid | `node_process.py` |
| F10 | Shortcut conflict detection in set() | `shortcut_manager.py` |
| F11 | nodes_data KeyError protection | `canvas_connections.py` |
| F12 | Reset _is_closing on user cancel close | `lifecycle.py` |
| F13 | .bak backup on layout corruption | `canvas_layout.py` |

## Round 3: Global Defenses (9 items)

| ID | Mechanism | File |
|------|------|------|
| R01 | start_script UnboundLocalError fix | `property_panel.py` |
| R02 | Restart Popen try/except protection | `bnos_console.py` |
| R03 | _notify() thread-safe lock | `app_state.py` |
| R04 | file_operation_manager race condition fix | `file_operation_manager.py` |
| R05 | float() deserialization try/except | `edge_item.py` |
| R06 | data['name'] -> .get() protection | `node_list_ops.py` |
| R07 | data['name'] -> .get() protection | `node_list_context.py` |
| R08 | data['name'] -> .get() protection | `node_list_drag.py` |
| R09 | start_path None check | `property_panel.py` |

## Round 4: Signal & Resource Safety (18 items)

| ID | Priority | Mechanism | File |
|------|----------|------|------|
| S01 | P0 | destroyed signal cleanup for polling_manager | `node_list_dock.py` |
| S02 | P0 | _on_close() disconnect cleanup | `node_list_panel.py` |
| S03 | P0 | Kill child process on exception after Popen | `composite_node.py` |
| S04 | P0 | Path traversal protection in changelog_viewer | `changelog_viewer.py` |
| S05 | P1 | _on_close() disconnect | `resource_monitor.py` |
| S06 | P1 | unsubscribe_monitor disconnect | `node_monitor.py` |
| S07 | P1 | dispose() disconnect | `performance_panel.py` |
| S08 | P1 | temp_dir try/finally cleanup | `import_export_manager.py` |
| S09 | P1 | rmtree failure rollback after rename | `node_list_ops.py` |
| S10 | P1 | Thread callback main-thread execution confirmed | `thread_pool.py` |
| S11 | P1 | list() snapshot anti-iteration-conflict | `performance_panel.py` |
| S12 | P1 | json.loads return type validation | `json_node_starter.py` |
| S13 | P1 | Project file lock to prevent multi-open | `project_manager.py` |
| S14 | P2 | cleanup_polling_signals() virtual hook | `floating_panel.py` |
| S15 | P2 | navigate_to same path boundary | `changelog_viewer.py` |
| S16 | P2 | load() type consistency validation | `app_config.py` |
| S18 | P2 | source_info.get protection | `canvas_connections.py` |
| S20 | P1 | remove_project_lock | `canvas_host.py` |

## Impact Scope

```
Round 1: 13 mechanisms  12 files
Round 2:  9 mechanisms   8 files
Round 3: 18 mechanisms  17 files (includes 11 composite node defenses)
────────────────────────────────────
Total:   40 mechanisms  37 files
```

The codebase has been comprehensively hardened across 8 dimensions: process management, file persistence, signal lifecycle, resource cleanup, path security, thread safety, config validation, and concurrency control.
