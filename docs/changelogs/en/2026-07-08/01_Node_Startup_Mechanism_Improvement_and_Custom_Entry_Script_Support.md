# Node Startup Mechanism Improvement and Custom Entry Script Support

## Overview

This update improves the node startup mechanism, supporting custom startup program configuration in `start.json`, and synchronizes updates to node development tools.

## Key Changes

### 1. New entry field in start.json

Added `entry` field in `start.json`, allowing users to specify custom startup script paths:

```json
{
  "entry": "main.py",
  "venv_path": "venv"
}
```

- `entry` field is optional, defaults to `main.py`
- Supports relative and absolute paths
- Backward compatible: uses default value when not set

### 2. Node Startup Process Optimization

Modified startup logic in `ui/core/node_process.py`:

- Priority reads `entry` field from `start.json`
- Falls back to default `main.py` when not present
- Supports launching other programs (scripts, executables, etc.)

### 3. Node Development Tool Updates

Updated `tools/python_create_node.py`:

- Prompts user for custom entry file when creating nodes
- Default value is `main.py` for backward compatibility
- Updated node development documentation to explain `start.json` configuration

### 4. Development Documentation Updates

Updated `tools/节点开发规范.md` and `tools/config_json_开发规范.md`:

- Added complete `start.json` configuration documentation
- Explained usage and default values for `entry` field
- Provided configuration examples for custom startup programs

## File Changes

| File | Change Type | Description |
|------|------------|-------------|
| `ui/core/node_process.py` | Modified | Supports reading entry field from start.json |
| `tools/python_create_node.py` | Modified | Supports custom entry file input |
| `tools/节点开发规范.md` | Modified | Added start.json configuration documentation |
| `tools/config_json_开发规范.md` | Modified | Added entry field documentation |