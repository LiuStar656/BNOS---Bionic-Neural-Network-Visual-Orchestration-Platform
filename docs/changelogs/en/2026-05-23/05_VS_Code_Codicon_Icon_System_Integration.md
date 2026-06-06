# 🎨 VS Code Codicon Icon System Integration

## 🎨 VS Code Codicon Icon System Integration (2026-05-23)

### Icon Resource Management

**New icon source directory**: `codicon-source/` (formerly `vscode-codicons-main`)

- Full VS Code Codicon icon library (MIT License)
- Font file: `codicon.ttf`
- Icon definitions: `codiconsLibrary.ts`

### Icon Manager

**Updated**: `ui/icons/codicon.py`

- Icon mappings expanded from 527 to **597 icons**
- New icon categories: AI, Debug, Git, Terminal, Layout
- Convenient `get_icon()` and `get_icon_font()` interfaces

### New Icon Categories

| Category | New Icons |
|----------|-----------|
| AI Assistant | `copilot`, `thinking`, `sparkle`, `openai`, `claude` |
| Debug | `debug-all`, `debug-step-in`, `debug-step-out`, `debug-coverage` |
| Git | `git-compare`, `repo-clone`, `repo-pull`, `repo-push` |
| Terminal | `terminal-bash`, `terminal-cmd`, `terminal-powershell` |
| Layout | `layout`, `layout-panel`, `layout-sidebar-left/right` |
| Run | `run-all`, `run-coverage`, `run-with-deps` |

### UI Icon Replacement

**Modified files**:
- `ui/menu/menu_manager.py` - Menu icons
- `ui/canvas/draw_toolbar.py` - Drawing toolbar icons

### Usage Example

```python
from ui.icons import get_icon, get_icon_font

icon_char = get_icon('copilot')    # AI assistant icon
icon_char = get_icon('run-all')    # Run icon
```

---