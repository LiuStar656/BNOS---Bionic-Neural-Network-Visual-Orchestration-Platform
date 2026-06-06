# 🆕 Node Registry + External Node Mount

## 🆕 Node Registry + External Node Mount (2026-05-22)

### Node Registry Component 📋

**New**: `ui/core/node_registry.py`

- **Persistent file**: `<project>/node_registry.json`
- **Scan-first principle**: `refresh_nodes()` scans nodes/ dir as primary source, registry as auxiliary
- **Auto-sync**: Scanned nodes → active, unscanned local nodes → missing
- **Mount support**: `mount_root` field for external sources

### External Node Mounting 🔗

**New feature**: Edit menu → "Mount External Node" (Ctrl+Shift+O)

- **Select external folder** → read `config.json` → mount to project (no file copy)
- **Auto-create locked group**: Named after mount root absolute path, shows 🔒
- **Lock rules**:
  - ❌ No move out of mount group
  - ❌ No move into mount group
  - ❌ Mount group cannot be renamed/deleted
  - ✅ Same mount group nodes can freely create sub-groups
- **Restart recovery**: `refresh_nodes()` auto-restores mounted nodes from registry
- **Unmount**: Right-click node → "Unmount External Node" (keeps source files)

### NodeGroupManager Locked Groups

**Modified**: `ui/panels/node_group_manager.py`

- New `_locked_groups` set + `lock_group()`/`unlock_group()`/`is_group_locked()`
- Persisted to `node_groups.json` `locked_groups` field
- Empty locked groups are not auto-cleaned

---