# README Rewrite and Archive

## Background

The v1 README had the following issues:
- **Too long**: ~1100 lines with significant content duplication
- **Unclear architecture**: Module list dump without high-level abstraction or hierarchy diagram
- **Composite node system missing**: The most critical and complex feature (`composite_node.py` ~2800 lines) was barely mentioned
- **Stale references**: Multiple references to non-existent files (`bnos_gui.py`, `requirements_gui.txt`, `start_bnos_gui.bat`)
- **Scattered core design**: Key concepts (code-first, process isolation, file communication) were scattered across feature descriptions

## Changes

### README Rewrite (Bilingual CN/EN)

Compressed `README.md` and `README_CN.md` from ~1100 lines to ~220 lines, reorganized into 9 sections:

| Section | Content |
|---------|---------|
| 1. Introduction | One-sentence definition + positioning |
| 2. Core Design | Four principles: (1) Code-first + visual orchestration (2) Per-node process isolation + venv (3) File-based JSON communication + attention filtering (4) **Composite node DAG compression** |
| 3. Architecture | Hierarchy diagram: Launcher → BNOS Console → ApplicationContext → {EventBus, DI, Polling} → {Canvas, Panels, NodeSystem} → {Nodes(venv), Composite(orchestrator)} |
| 4. Quick Start | Correct startup commands (`python launcher.py` or `python bnos_console.py`) |
| 5. Key Features | Condensed to 6: Visual canvas, Composite node system, Multi-language nodes, Process health detection, Node registry, Startup queue + History rollback + Toast |
| 6. Project Structure | Condensed directory tree |
| 7. Extending | Adding new languages / node styles / parameter widgets |
| 8. Known Limitations | 4 core limitations |
| 9. License + Contribution | Unchanged |

### Key Changes

- **New "Composite Node" feature section**: Standalone section covering compression/expansion/orchestrator/DAG execution/port routing/dual runtime modes
- **Fixed stale references**: `bnos_gui.py` → `launcher.py` / `bnos_console.py`
- **Architecture diagram redrawn**: Shows two-tier launch → ApplicationContext → core services → node system hierarchy
- **Massively simplified**: Removed detailed user guide (node creation, canvas operations, etc.), kept only 5-step quick start
- **Removed "BNOS vs Low-Code" long table**: Condensed to a single positioning sentence
- **Archive links**: Both new READMEs include links to archived versions

### Old Version Archive

Old READMEs archived to `docs/archived/` with archive notices at top:

| File | Archive Location |
|------|-----------------|
| `README.md` (v1) | `docs/archived/README_v1_archived.md` |
| `README_CN.md` (v1) | `docs/archived/README_CN_v1_archived.md` |

## Comparison

| Aspect | Old (v1) | New (v2) |
|--------|----------|----------|
| Length | ~1100 lines | ~220 lines |
| Composite nodes | Not mentioned | Flagship feature, standalone section |
| Architecture | Module list dump | High-level hierarchy diagram |
| Startup command | `bnos_gui.py` (non-existent) | `launcher.py` / `bnos_console.py` |
| BNOS vs Low-Code | Verbose comparison table | Single positioning sentence |
| User guide | Extensive detailed steps | 5-step quick start |
| Archive links | None | Link in footer + archive notice |

## Modified Files

| File | Change |
|------|--------|
| `README.md` | Rewrite: ~1100 lines → ~220 lines, 9-section structure |
| `README_CN.md` | Rewrite: ~1100 lines → ~220 lines, 9-section structure |
| `docs/archived/README_v1_archived.md` | New: Archived v1 English README (with archive notice) |
| `docs/archived/README_CN_v1_archived.md` | New: Archived v1 Chinese README (with archive notice) |
| `docs/changelogs/cn/2026-07-13/14_README重写与归档.md` | New: This changelog (CN) |
| `docs/changelogs/en/2026-07-13/14_README_Rewrite_and_Archive.md` | New: This changelog (EN) |
| `docs/changelogs/cn/2026-07-13/README.md` | Update: Date index adds entry 14 |
| `docs/changelogs/en/2026-07-13/README.md` | Update: Date index adds entry 14 |
| `docs/changelogs/cn/README.md` | Update: Summary index details fold adds entry |
| `docs/changelogs/en/README.md` | Update: Summary index details fold adds entry |
| `docs/changelogs/cn/INDEX.md` | Update: Date index adds entry |
| `docs/changelogs/en/INDEX.md` | Update: Date index adds entry |
