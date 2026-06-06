# 🚀 Splash Screen + Brand Rename BnosConsole + README Update

## 🚀 Splash Screen + Brand Rename BnosConsole + README Update (2026-05-23)

### Splash Screen

New `ui/core/splash_screen.py` (114 lines):
- **ASCII Art BNOS**: 6-line █ block characters, Consolas 13pt bold, monochrome
- **BNOS CONSOLE** subtitle + project tagline (i18n)
- **Bottom-left live log**: QTextEdit 80px, scrolled startup steps
- **Bottom progress bar**: 0→100%, gray chunk
- **Delayed close**: 2 seconds after main window appears

### Brand Rename: BnosGui → BnosConsole

| Old | New |
|-----|-----|
| `bnos_gui.py` | `bnos_console.py` |
| `start_bnos_gui.bat` | `start_bnos_console.bat` |
| `start_bnos_gui.sh` | `start_bnos_console.sh` |
| `requirements_gui.txt` | `requirements.txt` |
| `"BnosGui"` window title | `"BnosConsole"` |
| `logs/bnos_gui.log` | `logs/bnos_console.log` |
| `_k_app_name` | `"BNOS Console"` (cn/en unified) |

25+ files affected: `main_window.py`, `dark_title_bar.py`, `logger.py`, `build_bnos.spec`, README, UPDATE, tests, etc.

### Affected Files

`splash_screen.py`(new), `bnos_console.py`(rename + splash delay), `strings_cn/en.json`, `main_window.py`, `dark_title_bar.py`, `logger.py`, `build_bnos.spec`, startup scripts, README, UPDATE, tests

---