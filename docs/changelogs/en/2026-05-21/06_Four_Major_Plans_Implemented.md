# 🆕 Four Major Plans Implemented

## 🆕 Four Major Plans Implemented (2026-05-21)

### **Plan 1: Node Expand Panel** 📤

**New component**: `ui/panels/node_expand_panel.py`

- `>>` expand button on canvas node top-right corner, opens floating panel centered on node
- Left: output.json editor (dark theme/editable/auto-refresh)
- Right: Start/Stop, Config, Delete three action buttons
- Right-click menu adds "Expand Node" entry
- Panel center aligns with node center coordinates

### **Plan 2: Node Monitor Panel** 📊

**New component**: `ui/panels/node_monitor.py`

- Global real-time log viewer, parent window + collapsible sub-panel architecture
- Syncs canvas nodes every 3s, auto-refreshes logs on mtime change every 2s
- Menu bar adds "Tools(&T)" → "Node Monitor" (Ctrl+Shift+M)
- Canvas right-click menu adds "Node Monitor"
- Window type matches NodeListPanel, follows main window

### **Plan 3: print → logging Migration** 📝

**New module**: `ui/core/logger.py`

- Console INFO + File DEBUG dual-channel output
- All 211 `print()` calls across 9 files migrated to `logger`
- Log file: `logs/bnos_gui.log` (excluded by .gitignore)

### **Plan 4: Floating Panel Base Class** 🪟

**New base class**: `ui/core/floating_panel.py`

- Unifies frameless, translucent, draggable, titled window behavior
- `NodeListPanel` → extends `FloatingPanel`
- `NodeConfigDialog` → extends `FloatingPanel` (removed QDialogButtonBox)
- `NodeMonitor` → extends `FloatingPanel`
- `NodeExpandPanel` → extends `FloatingPanel`
- Unified visual style: `rgba(30,30,30,220)` translucent dark container

---