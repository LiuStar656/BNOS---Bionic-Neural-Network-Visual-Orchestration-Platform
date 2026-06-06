# 🎨 VS Code Codicon 图标系统集成

## 🎨 VS Code Codicon 图标系统集成 (2026-05-23)

### 图标资源管理

**新增图标源目录**: `codicon-source/`（原 `vscode-codicons-main`）

- 包含完整的 VS Code Codicon 图标库（MIT 许可证）
- 字体文件: `codicon.ttf`
- 图标定义: `codiconsLibrary.ts`

### 图标管理器

**更新**: `ui/icons/codicon.py`

- 图标映射从 527 个扩展至 **597 个**
- 新增 AI/调试/Git/终端/布局等类别图标
- 提供 `get_icon()` 和 `get_icon_font()` 便捷接口

### 新增图标类别

| 类别 | 新增图标 |
|------|---------|
| AI 助手 | `copilot`, `thinking`, `sparkle`, `openai`, `claude` |
| 调试 | `debug-all`, `debug-step-in`, `debug-step-out`, `debug-coverage` |
| Git | `git-compare`, `repo-clone`, `repo-pull`, `repo-push` |
| 终端 | `terminal-bash`, `terminal-cmd`, `terminal-powershell` |
| 布局 | `layout`, `layout-panel`, `layout-sidebar-left/right` |
| 运行 | `run-all`, `run-coverage`, `run-with-deps` |

### UI 图标替换

**修改文件**:
- `ui/menu/menu_manager.py` - 菜单图标
- `ui/canvas/draw_toolbar.py` - 绘图工具栏图标

### 使用示例

```python
from ui.icons import get_icon, get_icon_font

icon_char = get_icon('copilot')    # AI 助手图标
icon_char = get_icon('run-all')    # 运行图标
```

---