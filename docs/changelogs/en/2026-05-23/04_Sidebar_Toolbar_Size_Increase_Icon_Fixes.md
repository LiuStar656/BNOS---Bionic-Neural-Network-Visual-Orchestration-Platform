# 🖼️ Sidebar Toolbar Size Increase & Icon Fixes

## 🖼️ Sidebar Toolbar Size Increase & Icon Fixes (2026-05-23)

### Dimension Adjustments

**Modified file**: `ui/canvas/draw_toolbar.py`

| Item | Before | After |
|------|--------|-------|
| Toolbar width | 40px | **56px** |
| Button height | 34px | **44px** |
| Icon font size | 14px | **18px** |

### Icon Fixes

Fixed several invalid icons that displayed as exclamation mark `!`:

| Function | Old Icon | New Icon | Description |
|----------|----------|----------|-------------|
| Rectangle tool | `layout-panel` | ✅ `layout-panel` | Panel icon |
| Round rectangle | `circle` | ✅ `circle` | Circle icon |
| Polygon | `triangle-up` | ✅ `triangle-up` | Triangle icon |
| Arrow tool | `arrow-right` | ✅ `arrow-right` | Arrow icon |
| Text tool | `file-text` | ✅ `file-text` | Text file icon |
| Stroke color | `pencil` | ✅ `pencil` | Pencil icon |
| Fill color | `paintcan` | ✅ `paintcan` | Paint bucket icon |
| Lock | `lock` | ✅ `lock` | Lock icon |
| Show/Hide | `eye` | ✅ `eye` | Eye icon |
| Undo | `arrow-left` → **`chevron-left`** | ✅ `chevron-left` | Left chevron |
| Redo | `arrow-right` → **`chevron-right`** | ✅ `chevron-right` | Right chevron |
| Delete selected | `trash` | ✅ `trash` | Trash icon |
| Clear all | `clear-all` → **`close`** | ✅ `close` | Close icon |

---