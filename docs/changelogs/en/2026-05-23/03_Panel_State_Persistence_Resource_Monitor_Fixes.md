# 🛠️ Panel State Persistence & Resource Monitor Fixes

## 🛠️ Panel State Persistence & Resource Monitor Fixes (2026-05-23)

### Fixed Issues

**1. Panel Auto-start Conflict**
- Fixed issue where floating panel auto-start causes Dock panel to disappear
- Fixed issue where floating panel fails to auto-start when Dock panel is auto-started
- Modified file: `ui/main_window.py`

**2. Null Pointer Error Fix**
- Fixed `AttributeError: 'NoneType' object has no attribute 'update_node_status'`
- Added null checks before accessing panels
- Modified file: `ui/main_window.py`

**3. Resource Monitor Dock Panel Node Data Loading**
- Fixed issue where node resource usage was not displayed
- Added `parent_window` reference for automatic node data retrieval
- Modified file: `ui/panels/resource_monitor_dock.py`

**4. Dock Panel Close Handling**
- Fixed issue where accessing deleted objects after closing Dock panel
- Connected `panel_closed` signal to clear references on close
- Modified file: `ui/main_window.py`

**5. Node Monitor Panel Status Sync**
- Fixed PID file path issue (prioritize `.pid` file)
- Sync status display during resource monitoring
- Modified file: `ui/panels/node_monitor_dock.py`

### Feature Improvements

**Panel State Persistence**
- Support independent visibility state saving for Dock and floating panels
- Support panel position persistence
- Auto-restore panel state and position after restart

**Resource Monitor Layout Optimization**
- CPU, RAM, Disk displayed horizontally and centered
- Node resource list displayed vertically
- Consistent layout between Dock and floating versions

### Modified Files
- `ui/main_window.py` - Panel state restoration, null checks, Dock close handling
- `ui/panels/resource_monitor_dock.py` - Node data loading, status sync
- `ui/panels/node_monitor_dock.py` - PID file path fix, status sync
- `ui/core/app_config.py` - Singleton pattern
- `ui/core/dock_manager.py` - Duplicate creation prevention

---