# Photoshop-Style History Rollback

## Background

The original undo/redo had several problems:

1. **Dual-stack pattern**: Redo stack was lost after new operations, preventing backtracking to earlier states
2. **No visual history**: Users couldn't see what state undo would revert to, or how many steps had been performed
3. **Unreliable anchor restoration**: In multi-port scenarios, undo re-creation of edges would restore anchors to wrong ports

A Photoshop-like history panel was needed: clear list, clickable jump, no loss of redo capability.

---

## Design

**Flat command list + current_index pointer** replaces dual-stack:

```
         commands[]
         ↓
[0] [1] [2] [3] [4] [5] [6] [7] ...
                  ↑
            current_index = 4

undo → current_index = 3, execute commands[4].undo()
redo → current_index = 4, execute commands[5].execute()
jump_to(2) → undo [4], undo [3], execute [2]
```

- **jump_to(n)**: Batch undo/execute to target position, supports clicking any history panel entry
- **New operation overwrites tail**: `current_index=4` + new operation → discard [5,6,7], append new command at [5]
- **Redo never lost**: As long as no new operation is performed, redo is always available

---

## Architecture

```
ui/core/commands/
├── base.py              # Command base class (execute/undo/description)
├── history_manager.py   # HistoryManager singleton (commands[] + current_index)
├── node_commands.py     # CreateNodeCommand / DeleteNodeCommand / MoveNodeCommand
└── edge_commands.py     # CreateEdgeCommand / DeleteEdgeCommand
```

### Command Base Class

```python
class Command(ABC):
    @abstractmethod
    def execute(self): ...

    @abstractmethod
    def undo(self): ...

    @property
    def description(self) -> str: ...
```

### HistoryManager Singleton

```python
class HistoryManager(QObject):
    COMMANDS_LIMIT = 500
    history_changed = Signal()   # UI refresh signal
    index_changed = Signal(int)

    def execute_command(self, command): ...
    def record_only(self, command): ...
    def undo(self): ...
    def redo(self): ...
    def jump_to(self, index): ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
```

### HistoryPanel UI

- `HistoryPanelWidget`: Inner QWidget panel with QListWidget displaying operation list + clear button + info label
- Connects to `history_manager.history_changed` / `index_changed` signals for auto-refresh
- Click list item → `jump_to(index)` to navigate to corresponding state

---

## Bug Fix Journey

### Edge deletion ValueError: `list.remove(x): x not in list`

- **Root cause**: `_record_delete_edge` — `DeleteEdgeCommand.execute()` already removed the edge internally, outer `self.edges.remove(edge)` threw
- **Fix**: After recording, check `edge not in self.edges`, skip if already removed

### Reconnection shows "Already exists"

- **Root cause**: `_record_create_edge` used `execute_command()` which double-executed `create_edge`
- **Fix**: Changed to `record_only()` — record without re-executing

### Small anchor edge deletion → undo restores to large anchor

- **Layer 1**: `_record_delete_edge` didn't pass port name
- **Layer 2**: `_resolve_anchor` used `node.input_ports` (doesn't exist)
- **Layer 3**: `edge.target_port_name` attribute doesn't exist → EdgeItem stores as `_desired_target_port_name`
- **Fix**: `getattr(edge, '_desired_target_port_name', None)` correctly resolves target port name

---

## Key Files Changed

| File | Change |
|------|--------|
| `ui/core/commands/base.py` | Command abstract base class |
| `ui/core/commands/history_manager.py` | HistoryManager singleton (flat list + current_index + jump_to) |
| `ui/core/commands/edge_commands.py` | CreateEdgeCommand / DeleteEdgeCommand (with `_resolve_anchor`) |
| `ui/core/commands/node_commands.py` | CreateNodeCommand / DeleteNodeCommand / MoveNodeCommand |
| `ui/panels/history_panel.py` | HistoryPanelWidget + HistoryPanelDock |
| `ui/canvas/canvas_connections.py` | Edge creation/deletion auto-recording + `_desired_target_port_name` |
| `ui/canvas/canvas_view.py` | Replay guard mechanism |
| `ui/main_window/panel.py` | `show_history_panel()` method |
| `ui/menu/menu_manager.py` | Tools menu added 「History」 entry |

---

## Verification Results

- ✅ Undo/redo correctly restores node positions, edges, and anchor bindings
- ✅ HistoryPanel visual list updates in real-time
- ✅ Multi-port anchor restoration correct (no fallback to default anchor)
- ✅ Delete edge → undo restore edge → anchor port correct
- ✅ Menu bar 「Tools → History」 opens panel normally
