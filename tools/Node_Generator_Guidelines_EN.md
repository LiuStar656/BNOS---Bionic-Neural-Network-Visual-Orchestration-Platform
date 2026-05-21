# Standard Node Generator Development Guidelines

> For developing new language node generators (Go / Java / C++ / Shell, etc.)

---

## 1. Node Directory Structure

Each node under `project/nodes/` must have the following structure:

```
nodes/
└── node_{lang}_{name}/
    ├── config.json          # Node configuration (required)
    ├── start.bat             # Windows launcher (required)
    ├── start.sh              # Linux/macOS launcher (required)
    ├── listener.{ext}        # Listener entry point (required, runs continuously)
    ├── main.{ext}            # Main processor entry (optional, single-shot logic)
    ├── requirements.txt      # Dependency declarations (if any)
    ├── .gitignore            # Exclude build artifacts and logs
    └── logs/                 # Runtime logs (auto-created)
        └── listener.log
```

---

## 2. config.json Specification

```json
{
  "node_name": "Node Name",
  "language": "Language key (python/rust/go/java/cpp/shell)",
  "output_type": "Output type (json/text)",
  "listen_upper_file": "",
  "input_type": "json",
  "description": "Node description"
}
```

The `language` key must match the key registered in `ui/creators/node_creator_manager.py`.

---

## 3. start.bat Mandatory Specification (Windows)

### Required Arguments

| Argument | Behavior |
|----------|----------|
| `--no-pause` | Silent mode: no UI output, no `pause`, used by GUI |
| None | Interactive mode: full output, `pause` at end |

### Required Features

1. **Self-healing**: Detect missing runtime/compiler dependencies, auto-repair
2. **Background launch**: Use `start /b` to run listener without blocking script
3. **PID recording**: Write `.pid` file after launch for GUI health detection

### Template

```bat
@echo off
setlocal enabledelayedexpansion
if not "%1"=="--no-pause" (
    cls
    chcp 65001 >nul
    echo ======================================
    echo        BNOS {Lang} Node Starter
    echo ======================================
    echo.
)
cd /d "%~dp0"

REM === Self-healing ===
REM Detect {runtime/compiler/venv}, auto-build/repair if missing
REM ...

REM === Background Launch ===
if not "%1"=="--no-pause" (
    echo 🔧 Launching listener in background...
    start /b "" {launch_command}
) else (
    start /b "" {launch_command} >nul 2>&1
)

REM === Write PID ===
REM Wait for process to start
timeout /t 1 /nobreak >nul
REM Get PID via tasklist (replace {exe_name} with actual process name)
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq {exe_name}" /nh 2^>nul') do echo %%i > .pid

if not "%1"=="--no-pause" (
    echo ✅ Listener running in background (PID written to .pid)
    pause
)
```

### Critical Implementation Details

- **`start /b ""`**: The `""` is required to prevent Windows from treating the first argument as a window title
- **`timeout /t 1`**: Wait 1 second for process to start before querying with `tasklist`
- **`2^>nul`**: Must use `2^>nul` inside bat files (not `2>nul`)
- **PID file format**: Single integer on one line, e.g. `echo 1234 > .pid`

---

## 4. start.sh Mandatory Specification (Linux/macOS)

### Template

```bash
#!/bin/bash
cd "$(dirname "$0")"
NO_PAUSE=false
[ "$1" = "--no-pause" ] && NO_PAUSE=true

# === Self-healing ===
# ...

# === Background Launch + PID ===
nohup {launch_command} > /dev/null 2>&1 &
echo $! > .pid
[ "$NO_PAUSE" = false ] && echo "✅ Listener running in background (PID: $(cat .pid))" && read -p "Press Enter to exit..."
```

### Critical Implementation Details

- **`nohup ... &`**: Run in background immune to terminal closure
- **`echo $! > .pid`**: `$!` is the PID of the most recent background process
- **`[ "$NO_PAUSE" = false ]`**: Conditional UI output, silent in no-pause mode

---

## 5. Listener Program Specification

The listener is the core of each node and must run continuously (should not exit on its own).

### Minimum Requirements

1. Read `config.json` to get `listen_upper_file` path
2. Monitor upstream node's `output.json` file for changes
3. Invoke processing logic upon receiving new data
4. Write results to this node's `output.json`
5. Log to `logs/listener.log`

### Self-healing

- Verify runtime environment on startup, auto-repair if incomplete
- Auto-create missing output directories
- Never crash on errors — log and continue listening

---

## 6. Integration with NodeCreatorManager

### Register New Language

In `ui/creators/node_creator_manager.py`, inside `_register_default_creators`:

```python
self._register("{lang_key}", {
    "display_name": "{Display Name}",
    "creator_func": lambda name: create_{lang}_node(name),
})
```

### Creator Function

The creator function should:

1. Import the corresponding tools script (e.g. `from tools.{lang}_create_node import generate`)
2. Call the generate function to create node directory and all files
3. Return `True` / `False`

---

## 7. Test Checklist

All tests must pass before a new language generator is considered complete:

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Create Node | GUI → New Node → Select language | Full directory created, config.json correct |
| Build/Compile | First launch of node | Self-healing triggers, build succeeds |
| Foreground Launch | Double-click `start.bat` | Full UI displayed, `pause` at end |
| Background Launch | GUI starts node | Process runs in background, UI shows ● Running |
| PID Recording | Check `.pid` after launch | File exists, contains valid PID |
| Process Detection | Restart GUI, check status | Auto-restored to ● Running |
| Process Exit | Kill process manually, wait 3s | UI auto-changes to ○ Stopped |
| Stop Node | GUI stops node | `.pid` deleted, process terminated |
| Log Output | Check `logs/listener.log` | Normal log entries recorded |

---

## 8. Forbidden Practices

| Forbidden | Why |
|-----------|-----|
| Foreground blocking `{program}` | No background execution, GUI can't detect |
| No `.pid` file | Can't restore state across sessions |
| `pause` without `--no-pause` check | GUI call hangs indefinitely |
| `stdout=subprocess.PIPE` without reading | Buffer fills up, process freezes |
| Build artifacts in version control | Use `.gitignore` to exclude `target/`, `venv/`, `.exe`, etc. |
