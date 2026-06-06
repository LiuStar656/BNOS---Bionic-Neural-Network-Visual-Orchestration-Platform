# 🔧 Force Delete Node Folder

## 🔧 Force Delete Node Folder (2026-06-05)

### Problem Description

**Node folder deletion fails due to file being accessed**
- **Problem**: When deleting a node, the folder may be occupied by unknown programs (File Explorer, antivirus, Python processes, etc.), causing deletion to fail
- **Impact**: Users cannot delete nodes normally, affecting user experience

### Fix Solution

**Three-layer Force Delete Mechanism**

1. **Layer 1: Try Renaming**
   - Rename folder to temporary name to bypass certain occupation scenarios

2. **Layer 2: Windows rmdir Command**
   - Use `rmdir /s /q` command to force delete
   - Windows-specific, can handle file occupation scenarios

3. **Layer 3: Scan and Terminate Occupying Processes**
   - Use psutil to scan all processes
   - Check if process working directory and open files contain node path
   - Force terminate these processes then retry deletion

### Technical Implementation

```python
def _force_stop_node_processes(self, node_path):
    """Force stop processes that may occupy node folder"""
    import psutil
    
    for proc in psutil.process_iter(['pid', 'name', 'open_files', 'cwd']):
        try:
            # Check working directory
            cwd = proc.cwd()
            if node_path_lower in cwd.lower():
                proc.kill()
            
            # Check open files
            for f in proc.open_files():
                if node_path_lower in f.path.lower():
                    proc.kill()
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

def _force_delete_directory(self, node_path):
    """Force delete directory"""
    import shutil
    import time
    
    # Method 1: Rename and delete
    try:
        os.rename(node_path, temp_name)
        node_path = temp_name
    except OSError:
        pass
    
    # Method 2: shutil.rmtree
    try:
        shutil.rmtree(node_path)
        return True, "Success"
    except:
        pass
    
    # Method 3: Windows rmdir
    if os.name == 'nt':
        subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', node_path])
    
    # Method 4: Terminate processes and retry
    self._force_stop_node_processes(node_path)
    time.sleep(0.5)
    shutil.rmtree(node_path)
```

### Modified Files

- `ui/panels/node_list_panel.py` - Added force delete functions
- `ui/panels/node_list_dock.py` - Added force delete functions

### Acceptance Criteria

✅ Normal node deletion functionality unaffected
✅ Auto-trigger force delete mechanism when files are occupied
✅ Log terminated processes after successful force deletion
✅ Batch node deletion also uses force delete mechanism

---