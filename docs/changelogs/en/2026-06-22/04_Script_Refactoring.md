# 04 Script Directory Refactoring

**Date**: 2026-06-22

## Background

The project root contained both entry scripts (`bnos_console.py`, `launcher.py`, `run_tests.py`) and helper scripts (`restart_helper.py`), making the boundary between public entry points and internal helpers unclear. `restart_helper.py` is only called indirectly from `bnos_console.py` during the restart flow, so it should live in a dedicated helper directory.

## Changes

### New `scripts/` directory and moved `restart_helper.py`

- New directory: `scripts/`
- Old location: `restart_helper.py` → New location: `scripts/restart_helper.py`
- File content and behavior are unchanged

### `bnos_console.py`: updated call path

Inside `bnos_console.py`, the way the helper script is resolved changed from:

```python
restart_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_helper.py")
```

to:

```python
restart_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "restart_helper.py")
```

The restart flow itself is unchanged: when `app.exec()` returns `42`, the main program launches `scripts/restart_helper.py` as an intermediate process that waits for the old parent to exit before starting a new instance.

## Tech docs updated

The following docs were updated to keep their path references in sync with the code:

- `docs/BNOS_文件结构图.md`: new `scripts/` node in the Mermaid graph; `restart_helper.py` re-parented under it
- `docs/BNOS_架构图.md`: flowchart labels now show `scripts/restart_helper.py`
- `docs/BNOS_技术分析报告.md`: LOC table uses the new file path
- `docs/BNOS_项目优化分析报告.md`: root tree and section 7.4 references updated

## Verification

1. `bnos_console.py` still parses/imports cleanly
2. `os.path.join(<script_dir>, "scripts", "restart_helper.py")` resolves to an existing file
3. Manual end-to-end check: run `python bnos_console.py` → click menu "Restart" → exit code 42 → new BNOS process starts successfully
