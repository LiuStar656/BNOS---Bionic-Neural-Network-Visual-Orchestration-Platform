# 🔄 Unified Polling Manager + Global State Monitoring Refactor

## 🔄 Unified Polling Manager + Global State Monitoring Refactor (2026-05-23)

### Unified Polling Manager

**New**: `ui/core/polling_manager.py` (Singleton Pattern)

Centralized management for all periodic polling tasks:

| Polling Task | Interval | Description |
|--------------|----------|-------------|
| Node Health Check | 3s | Detect node process status |
| Global Log Monitoring | 2s | Detect global log file changes |
| Global Config Monitoring | 5s | Detect global config file changes |
| Node Log Monitoring | 2s | Detect individual node log changes |
| Node Config Monitoring | 5s | Detect individual node config changes |
| Node Output JSON | 1s | Detect output.json changes |
| Application State | 1s | Monitor overall application status |

**Core Features**:
- Singleton pattern for global unique instance
- Support task registration/cancellation/pause/resume
- Precise timing based on QTimer
- PyQt signal mechanism for panel notifications

### Module Consolidation

**Deleted Redundant Files**:
- `ui/core/system_monitor.py` → merged into polling_manager
- `ui/core/global_detector.py` → merged into polling_manager

### Panel Adaptations

| Panel | Changes |
|-------|---------|
| `ui/main_window.py` | Replaced SystemMonitor/GlobalDetector with polling_manager |
| `ui/panels/node_monitor.py` | Subscribed to polling_manager log signals |
| `ui/panels/node_expand_panel.py` | Subscribed to config/output signals |
| `ui/dialogs/node_config_dialog.py` | Subscribed to config change signals |

### Affected Files

`polling_manager.py`(new), `main_window.py`, `node_monitor.py`, `node_expand_panel.py`, `node_config_dialog.py`, `system_monitor.py`(deleted), `global_detector.py`(deleted)

---