# 🎨 UI Simplification & Optimization

## 🎨 UI Simplification & Optimization (2026-05-21)

### **Emoji Removal + Name Simplification** 🧹

- All Emoji patterns removed from UI buttons, menus, dialog titles
- Button names simplified to 2-4 characters (e.g., "Clear All Edges" → "Clear Edges")
- 6 files affected: canvas_view.py, property_panel.py, node_list_panel.py, main_window.py, menu_manager.py, bnos_gui.py

### **Button Colors Unified to Black/White/Gray** ⚫

- All colorful button backgrounds replaced with monochrome (`#333`/`#555`/`#666`)
- 14 locations in `property_panel.py`

### **Canvas Right-Click Menu Enhanced** 📋

- Canvas blank area right-click adds "New Node" submenu (7 languages)
- Canvas blank area right-click adds "Node Monitor"

### **Box Selection Logic Fixed** 🎯

- Clicking node sub-items (status indicator, text, expand button) no longer triggers box selection
- Uses `parentItem()` chain lookup instead of flat `isinstance` check

### **Bug Fixes** 🔧

- Fixed single-node right-click start/stop crash (missing `start_single_node`/`stop_single_node` methods)
- `.gitignore` adds `logs/` to exclude log directory

---