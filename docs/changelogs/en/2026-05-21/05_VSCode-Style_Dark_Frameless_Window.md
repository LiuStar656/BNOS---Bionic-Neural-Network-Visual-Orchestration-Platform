# 🎨 VSCode-Style Dark Frameless Window

## 🎨 VSCode-Style Dark Frameless Window (2026-05-21)

**New component**: `ui/core/dark_title_bar.py`

- Main window switched to frameless design with custom 40px dark title bar (`#1e1e1e`)
- Menu bar embedded in same row as title bar: `[BnosGui] [File] [Edit] [Tools] [Help] ←→ [─] [□] [✕]`
- Global dark QSS theme: menus, scrollbars, inputs, buttons, tables, dialogs all dark-styled
- Edge-drag resize support for frameless window (6px sensitive margin)
- Custom minimize/maximize/close buttons, close button turns red (`#e81123`) on hover
- Double-click title bar to toggle maximize/restore, drag title bar to move window

---