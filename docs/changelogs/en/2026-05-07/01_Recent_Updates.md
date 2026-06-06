# 🆕 Recent Updates

## 🆕 Recent Updates (2026-05-07)

### ✨ New Features and Optimizations

#### 1. **Connection Anchor Position Fix** 🔧
- **Problem**: Connections showed correctly during drag, but after connecting, anchor position shifted to status indicator
- **Fix**: Changed to use `sceneBoundingRect().center()` directly to get anchor geometric center, ensuring connections always link to anchor center
- **Affected Files**: `ui/canvas_widget.py` - `EdgeItem.update_path()` method
- **Technical Improvement**: Avoided manual offset calculation, improved coordinate calculation accuracy and reliability

#### 2. **Window Topmost Behavior Optimization** 🪟
- **Problem**: Node list, Toast notifications, and progress windows stayed globally topmost after switching apps, covering other software windows
- **Fix**: Removed all unnecessary `WindowStaysOnTopHint` flags, kept `Qt.WindowType.Tool` flag
- **Affected Files**:
  - `ui/node_list_panel.py` - Node list panel
  - `ui/main_window.py` - ToastNotification and ProgressFloatingWindow
- **Effect**: Tool windows only maintain hierarchy within the app, won't interfere with other applications

#### 3. **Best Practices Documentation** 📚
- Created knowledge base documenting QGraphicsItem anchor position calculation best practices
- Documented Qt tool window topmost problem solutions
- Provided technical reference and guidelines for future development

### 🎯 Technical Highlights

- **More Accurate Coordinate Calculation**: Used `sceneBoundingRect().center()` instead of `scenePos() + offset`
- **Better User Experience**: Tool windows follow standard Windows behavior, don't cover other apps
- **Code Quality Improvement**: Precipitated best practices through memory system, avoid repeated issues
