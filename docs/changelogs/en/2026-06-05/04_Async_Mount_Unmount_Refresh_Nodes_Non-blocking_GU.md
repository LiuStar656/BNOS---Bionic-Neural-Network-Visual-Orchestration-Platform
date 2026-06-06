# 🔧 Async Mount/Unmount/Refresh Nodes, Non-blocking GUI

## 🔧 Async Mount/Unmount/Refresh Nodes, Non-blocking GUI (2026-06-05)

### Problem Description

**GUI unresponsive when mounting/unmounting/refreshing nodes**
- **Problem**: When mounting external nodes, unmounting nodes, or refreshing node list, the operation is synchronous and blocking, causing the entire GUI to become unresponsive
- **Impact**: Users cannot perform other operations during the operation, resulting in poor experience

### Fix Solution

**Async for the following functions**

1. **External node mount**
   - Immediately show "Processing mount request..."
   - Async read config, register node
   - Update UI after completion

2. **External node unmount**
   - Immediately show "Unmounting node..."
   - Async unregister from registry, update groups
   - Update UI after completion

3. **Refresh node list**
   - Immediately show "Refreshing node list..."
   - Async scan directories, read configs, restore mounted nodes
   - Update UI after completion

### Modified Files

- `ui/core/external_node_manager.py` - Async mount/unmount
- `ui/core/project_manager.py` - Async refresh nodes

### Acceptance Criteria

✅ GUI does not block when mounting external nodes
✅ GUI does not block when unmounting external nodes
✅ GUI does not block when refreshing node list
✅ Display transition status prompts

---