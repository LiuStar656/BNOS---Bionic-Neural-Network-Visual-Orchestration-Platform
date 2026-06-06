# 🔄 Node State Sync and Project Persistence Improvement

## 🔄 Node State Sync and Project Persistence Improvement (2026-06-07)

### Fixed Issues

**1. Node state information not updating properly**
- **Problem**: Canvas node CPU and memory info not updating, inconsistent with resource monitor panel
- **Root Cause**: Conflicting node state fetching methods, 
ode_monitor module and resource monitor had different data sources
- **Fix**:
  - Deprecated ui/core/node_monitor.py module
  - Resource monitor added 
ode_state_updated signal to forward node CPU and memory data
  - Canvas nodes receive data from resource monitor via signals, ensuring consistent data source
- **Modified Files**:
  - ui/panels/resource_monitor.py - Added signal and data forwarding
  - ui/panels/resource_monitor_dock.py - Added signal and data forwarding
  - ui/canvas/items/node_item.py - Removed 
ode_monitor dependency, switched to signal-based data reception

**2. Data loading delay caused by async calls**
- **Problem**: Nodes couldn't receive data signals from resource monitor after creation
- **Root Cause**: Signal connection timing issue, resource monitor created later than nodes
- **Fix**: Main window added _connect_existing_nodes_to_resource_monitor() method to actively connect signals of existing nodes after panel creation
- **Modified Files**: ui/main_window.py

**3. Node running time not updating**
- **Problem**: Node running time showing 0s
- **Root Cause**: Node start time not recorded
- **Fix**:
  - Added _start_time attribute to nodes
  - Record start time when node status becomes 'running' or 'idle'
  - Real-time calculation and display of running duration
- **Modified Files**: ui/canvas/items/node_item.py

**4. Node UI layout adjustment**
- **Problem**: Node internal element layout不合理, node name, status indicator, language tag positions not meeting requirements
- **Fix**:
  - Adjusted node height to 120px
  - Node name centered at top
  - Status indicator parallel with node name
  - CPU, memory, running time left-aligned and vertically stacked
  - Language tag (Python) top edge tangent to node bottom edge
  - Running time centered
- **Modified Files**: ui/canvas/items/node_item.py

**5. Project persistence improvement**
- **Problem**: Need to manually open project after restarting GUI
- **Fix**:
  - Record to pp_config.json when opening project
  - Record again when closing GUI
  - Auto-open last opened project on next GUI startup
- **Modified Files**:
  - ui/main_window.py - Auto-open project logic
  - ui/core/project_manager.py - Record project path

**6. Removed deprecated module**
- **Deleted File**: ui/core/node_monitor.py

### Technical Implementation

**Signal Forwarding Mechanism**
`python
# resource_monitor.py - Resource monitor sends signal
node_state_updated = pyqtSignal(str, float, float)  # node_name, cpu_percent, memory_mb

def _update_single_node_stats(self, node_name, node_info):
    # Calculate CPU, memory
    cpu_percent = ...
    memory_mb = ...
    self.node_state_updated.emit(node_name, cpu_percent, memory_mb)
`

**Node Data Reception**
`python
# node_item.py - Node receives signal and updates display
def _on_status_updated(self, node_name, cpu_percent, mem_mb):
    if node_name != self.node_name:
        return
    duration_seconds = 0
    if self._start_time:
        duration_seconds = (datetime.now() - self._start_time).total_seconds()
    self._status_widget.update_status(cpu_percent, mem_mb, duration_seconds)
`

**Start Time Recording**
`python
def _try_initialize_start_time(self):
    if self.node_name in self.canvas.parent_window.nodes_data:
        node_info = self.canvas.parent_window.nodes_data[self.node_name]
        if node_info.get('status') in ('running', 'idle'):
            self._start_time = datetime.now()
`

**Project Persistence**
`python
def auto_open_last_project(self):
    last_project = self.app_config.get('last_project')
    if last_project and os.path.exists(last_project):
        QTimer.singleShot(200, lambda: self._auto_open_project(last_project))
`

### Acceptance Criteria

✅ Canvas node CPU and memory info consistent with resource monitor panel
✅ Node state updates in real-time, no delay
✅ Node running time displays correctly and updates in real-time
✅ Node UI layout meets requirements: name at top, language tag at bottom edge, running time centered
✅ Auto-open last project after GUI restart
✅ All functions work properly, no errors
✅ 
ode_monitor.py deleted
✅ Clear code structure, easy to maintain

---

---