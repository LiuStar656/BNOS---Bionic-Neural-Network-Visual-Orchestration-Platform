# Dock吸附堆叠尺寸持久化方案

## 一、问题分析

### 1.1 当前问题
1. **尺寸恢复失败**：调整 Dock 窗口尺寸后，重启应用无法正确恢复
2. **只找到部分 Dock**：恢复时只找到 1 个 Dock，而保存时有 4 个
3. **直接 resize 无效**：对停靠的 Dock 使用 `dock.resize()` 不起作用
4. **堆叠状态丢失**：多个 Dock 堆叠成标签页的状态无法持久化

### 1.2 Qt Dock 机制
- Qt 使用 `QMainWindow::saveState()` 和 `restoreState()` 保存布局
- 多个 Dock 堆叠时，Qt 使用 `tabifyDockWidget()` 形成标签页
- 停靠的 Dock 尺寸由 `QMainWindow` 统一管理，不能直接 `resize()`
- 应该使用 `QMainWindow::resizeDocks()` 来调整尺寸

### 1.3 Photoshop 参考特性
1. **吸附停靠**：面板拖动到边缘自动吸附
2. **标签堆叠**：多个面板可堆叠成标签页
3. **尺寸记忆**：每个面板的尺寸和布局可持久化
4. **灵活调整**：拖动分隔线调整尺寸，比例自动保存

---

## 二、解决方案架构

### 2.1 核心思路
1. **增强版状态管理**：结合 Qt 的 `saveState/restoreState` 和自定义尺寸保存
2. **区域尺寸管理**：按停靠区域（左、右、底）分别管理尺寸
3. **比例保存**：保存 Dock 之间的尺寸比例，而非绝对尺寸
4. **分阶段恢复**：先创建 Dock，再恢复布局，最后调整尺寸

### 2.2 数据结构设计

```python
# app_config.json 中保存的结构
{
  "dock_layout": {
    "version": "1.0",
    "areas": {
      "left": {
        "total_width": 300,
        "docks": [
          {"title": "节点列表(Dock)", "height": 400, "visible": true},
          {"title": "资源监测(Dock)", "height": 300, "visible": false}
        ],
        "tab_groups": [
          ["节点列表(Dock)", "另一个面板"]  // 堆叠在一起的标签组
        ]
      },
      "right": {
        "total_width": 350,
        "docks": [...]
      },
      "bottom": {
        "total_height": 200,
        "docks": [...]
      }
    },
    "floating_docks": [
      {
        "title": "某个面板",
        "geometry": {"x": 100, "y": 100, "width": 300, "height": 400},
        "visible": true
      }
    ],
    "qt_state": "base64_encoded_qt_state"  // Qt 原生状态
  }
}
```

---

## 三、实现方案

### 3.1 增强版 WindowStateManager

**文件**：`ui/core/window_state_manager.py`

**主要改进**：
1. 保存 Qt 原生状态（`saveState()`）
2. 保存每个 Dock 的详细信息（尺寸、可见性、位置）
3. 保存 Dock 堆叠关系（标签组）
4. 分阶段恢复：先恢复 Qt 状态，再调整尺寸

### 3.2 DockManager 增强

**文件**：`ui/core/dock_manager.py`

**主要改进**：
1. 跟踪所有 Dock 的信息
2. 记录标签堆叠关系
3. 提供按标题查找 Dock 的方法
4. 支持保存和恢复标签组

### 3.3 尺寸调整策略

1. **左右停靠区域**：调整宽度
2. **上下停靠区域**：调整高度
3. **堆叠的 Dock**：保存每个 Dock 的尺寸比例
4. **使用 `resizeDocks()`**：Qt 推荐的方法

---

## 四、具体实现步骤

### 步骤 1：增强 Dock 信息跟踪

修改 `DockManager`，添加 Dock 信息跟踪：

```python
class DockManager(QObject):
    def __init__(self, main_window):
        super().__init__()
        self._main_window = main_window
        self._docks = {}  # edge -> list of docks
        self._dock_info_map = {}  # title -> {'dock': dock, 'edge': edge, 'original_size': QSize}
    
    def add_panel_to_dock(self, widget, title, edge='left'):
        # ... 现有代码 ...
        # 记录 Dock 信息
        self._dock_info_map[title] = {
            'dock': dock,
            'edge': edge,
            'widget': widget
        }
        return dock
    
    def get_dock_by_title(self, title):
        """按标题获取 Dock"""
        info = self._dock_info_map.get(title)
        return info['dock'] if info else None
    
    def get_all_dock_titles(self):
        """获取所有 Dock 标题"""
        return list(self._dock_info_map.keys())
```

### 步骤 2：增强 WindowStateManager

重写 `window_state_manager.py`：

```python
"""
增强版窗口状态持久化管理
结合 Qt 原生 saveState/restoreState 和自定义尺寸管理
"""
from PySide6.QtWidgets import QApplication, QDockWidget
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from ui.core.logger import logger
import base64


def save_state(main_window):
    """保存窗口状态 - 完整版本"""
    try:
        logger.info("💾 ===== 开始保存窗口状态（增强版）=====")
        
        # 1. 保存窗口几何信息
        geometry = {
            "x": main_window.geometry().x(),
            "y": main_window.geometry().y(),
            "width": main_window.geometry().width(),
            "height": main_window.geometry().height(),
            "maximized": main_window.isMaximized()
        }
        main_window.app_config.set("window_geometry", geometry)
        
        # 2. 保存 Qt 原生状态
        qt_state = main_window.saveState()
        qt_state_base64 = base64.b64encode(qt_state).decode('utf-8')
        
        # 3. 收集所有 Dock 信息
        dock_info = _collect_dock_info(main_window)
        
        # 4. 收集 CanvasHost 中的终端 Dock
        terminal_info = _collect_terminal_dock_info(main_window)
        
        # 5. 组合保存数据
        full_state = {
            "version": "1.0",
            "qt_state": qt_state_base64,
            "docks": dock_info,
            "terminal_dock": terminal_info
        }
        
        main_window.app_config.set("dock_layout", full_state)
        logger.info("💾 Dock 布局已保存: %d 个 Dock", len(dock_info))
        
        # 6. 保存画布视图状态（保持原逻辑）
        if main_window.current_project_path:
            main_window.app_config.set("last_project", main_window.current_project_path)
            
            if hasattr(main_window, 'canvas') and main_window.canvas:
                view_state = {
                    "scale": main_window.canvas.transform().m11(),
                    "scroll_x": main_window.canvas.horizontalScrollBar().value(),
                    "scroll_y": main_window.canvas.verticalScrollBar().value()
                }
                main_window.app_config.set("canvas_view_state", view_state)
                main_window.canvas.save_layout(main_window.current_project_path)
        
        main_window.app_config.save()
        logger.info("💾 ===== 窗口状态保存完成 =====")
        
    except Exception as e:
        logger.error("❌ 保存窗口状态失败: %s", e, exc_info=True)


def _collect_dock_info(main_window):
    """收集所有 Dock 的信息"""
    docks_info = []
    all_docks = main_window.findChildren(QDockWidget)
    
    for dock in all_docks:
        title = dock.windowTitle()
        if not title:
            continue
        
        area = main_window.dockWidgetArea(dock)
        area_name = _dock_area_to_name(area)
        
        dock_data = {
            "title": title,
            "floating": dock.isFloating(),
            "visible": dock.isVisible(),
            "area": area_name
        }
        
        if dock.isFloating():
            geo = dock.geometry()
            dock_data["geometry"] = {
                "x": geo.x(), "y": geo.y(),
                "width": geo.width(), "height": geo.height()
            }
        else:
            dock_data["size"] = {
                "width": dock.width(),
                "height": dock.height()
            }
        
        docks_info.append(dock_data)
        logger.debug("💾 收集 Dock: %s (floating=%s, area=%s)", title, dock.isFloating(), area_name)
    
    return docks_info


def _collect_terminal_dock_info(main_window):
    """收集终端 Dock 的信息"""
    if not hasattr(main_window, '_canvas_host') or not main_window._canvas_host:
        return None
    
    canvas_host = main_window._canvas_host
    if not hasattr(canvas_host, '_terminal_dock') or not canvas_host._terminal_dock:
        return None
    
    term_dock = canvas_host._terminal_dock
    
    info = {
        "visible": term_dock.isVisible(),
        "floating": term_dock.isFloating()
    }
    
    if term_dock.isFloating():
        geo = term_dock.geometry()
        info["geometry"] = {
            "x": geo.x(), "y": geo.y(),
            "width": geo.width(), "height": geo.height()
        }
    else:
        info["size"] = {
            "width": term_dock.width(),
            "height": term_dock.height()
        }
    
    return info


def _dock_area_to_name(area):
    """将 Dock 区域枚举转换为名称"""
    area_map = {
        Qt.DockWidgetArea.LeftDockWidgetArea: "left",
        Qt.DockWidgetArea.RightDockWidgetArea: "right",
        Qt.DockWidgetArea.TopDockWidgetArea: "top",
        Qt.DockWidgetArea.BottomDockWidgetArea: "bottom",
        Qt.DockWidgetArea.NoDockWidgetArea: "none"
    }
    return area_map.get(area, "unknown")


def _name_to_dock_area(name):
    """将名称转换为 Dock 区域枚举"""
    area_map = {
        "left": Qt.DockWidgetArea.LeftDockWidgetArea,
        "right": Qt.DockWidgetArea.RightDockWidgetArea,
        "top": Qt.DockWidgetArea.TopDockWidgetArea,
        "bottom": Qt.DockWidgetArea.BottomDockWidgetArea
    }
    return area_map.get(name, Qt.DockWidgetArea.NoDockWidgetArea)


def restore_state(main_window):
    """恢复窗口状态 - 完整版本"""
    try:
        logger.info("📐 ===== 开始恢复窗口状态（增强版）=====")
        
        # 1. 恢复窗口几何信息
        geom = main_window.app_config.get("window_geometry")
        if geom:
            if geom.get("maximized", False):
                main_window.showMaximized()
            else:
                width = geom.get("width", 1400)
                height = geom.get("height", 900)
                _center_window(main_window, width, height)
        else:
            _center_window(main_window, 1400, 900)
        
        # 2. 获取保存的布局信息
        dock_layout = main_window.app_config.get("dock_layout")
        
        if dock_layout and dock_layout.get("version") == "1.0":
            # 分阶段恢复
            from PySide6.QtCore import QTimer
            
            # 阶段 1：先延迟一下，确保 UI 初始化完成
            QTimer.singleShot(100, lambda: _restore_phase1(main_window, dock_layout))
        else:
            logger.info("📐 未找到增强版布局数据，使用简单恢复")
            # 回退到简单恢复（保持向后兼容）
            _restore_simple(main_window)
        
        logger.info("📐 ===== 窗口状态恢复启动 =====")
        
    except Exception as e:
        logger.error("❌ 恢复窗口状态失败: %s", e, exc_info=True)


def _restore_phase1(main_window, dock_layout):
    """恢复阶段 1：恢复 Qt 原生状态"""
    logger.info("📐 [阶段 1] 恢复 Qt 原生状态")
    
    try:
        qt_state_base64 = dock_layout.get("qt_state")
        if qt_state_base64:
            qt_state = base64.b64decode(qt_state_base64.encode('utf-8'))
            main_window.restoreState(qt_state)
            logger.info("📐 Qt 原生状态已恢复")
    except Exception as e:
        logger.warning("📐 恢复 Qt 原生状态失败: %s", e)
    
    # 阶段 2：延迟恢复 Dock 尺寸
    from PySide6.QtCore import QTimer
    QTimer.singleShot(200, lambda: _restore_phase2(main_window, dock_layout))


def _restore_phase2(main_window, dock_layout):
    """恢复阶段 2：调整 Dock 尺寸"""
    logger.info("📐 [阶段 2] 调整 Dock 尺寸")
    
    docks_info = dock_layout.get("docks", [])
    
    # 按区域分组 Dock
    docks_by_area = {}
    for info in docks_info:
        area = info.get("area", "unknown")
        if area not in docks_by_area:
            docks_by_area[area] = []
        docks_by_area[area].append(info)
    
    # 对每个区域的 Dock 进行尺寸调整
    for area_name, area_docks in docks_by_area.items():
        _restore_area_docks(main_window, area_name, area_docks)
    
    # 阶段 3：恢复终端 Dock
    from PySide6.QtCore import QTimer
    QTimer.singleShot(100, lambda: _restore_phase3(main_window, dock_layout))


def _restore_area_docks(main_window, area_name, docks_info):
    """恢复指定区域的 Dock"""
    area = _name_to_dock_area(area_name)
    if area == Qt.DockWidgetArea.NoDockWidgetArea:
        return
    
    # 找到该区域的所有 Dock
    all_docks = main_window.findChildren(QDockWidget)
    area_dock_widgets = []
    area_dock_sizes = []
    
    for info in docks_info:
        title = info.get("title")
        for dock in all_docks:
            if dock.windowTitle() == title:
                if not info.get("floating", False):
                    area_dock_widgets.append(dock)
                    size = info.get("size", {})
                    if area in [Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea]:
                        area_dock_sizes.append(size.get("width", 200))
                    else:
                        area_dock_sizes.append(size.get("height", 300))
                break
    
    # 使用 resizeDocks 调整尺寸
    if area_dock_widgets and area_dock_sizes:
        try:
            orientation = Qt.Orientation.Horizontal
            if area in [Qt.DockWidgetArea.TopDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea]:
                orientation = Qt.Orientation.Vertical
            
            main_window.resizeDocks(area_dock_widgets, area_dock_sizes, orientation)
            logger.info("📐 已调整 %s 区域 %d 个 Dock 的尺寸", area_name, len(area_dock_widgets))
        except Exception as e:
            logger.warning("📐 调整 %s 区域 Dock 尺寸失败: %s", area_name, e)


def _restore_phase3(main_window, dock_layout):
    """恢复阶段 3：恢复终端 Dock"""
    logger.info("📐 [阶段 3] 恢复终端 Dock")
    
    terminal_info = dock_layout.get("terminal_dock")
    if not terminal_info:
        logger.info("📐 未找到终端 Dock 信息")
        return
    
    if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
        canvas_host = main_window._canvas_host
        if hasattr(canvas_host, '_terminal_dock') and canvas_host._terminal_dock:
            term_dock = canvas_host._terminal_dock
            
            # 恢复可见性
            visible = terminal_info.get("visible", False)
            if visible:
                term_dock.show()
            else:
                term_dock.hide()
            
            logger.info("📐 终端 Dock 已恢复 (visible=%s)", visible)
    
    logger.info("📐 ===== 窗口状态恢复完成 =====")


def _restore_simple(main_window):
    """简单版恢复（向后兼容）"""
    from PySide6.QtCore import QTimer
    
    def _restore_main_dock_sizes():
        main_dock_sizes = main_window.app_config.get("main_dock_sizes", {})
        if main_dock_sizes:
            all_docks = main_window.findChildren(QDockWidget)
            for dock in all_docks:
                title = dock.windowTitle()
                if title and title in main_dock_sizes:
                    _restore_dock_size_simple(dock, main_dock_sizes[title], main_window)
    
    QTimer.singleShot(300, _restore_main_dock_sizes)
    
    def _restore_terminal_dock_size():
        if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
            canvas_host = main_window._canvas_host
            if hasattr(canvas_host, '_terminal_dock') and canvas_host._terminal_dock:
                terminal_size = main_window.app_config.get("terminal_dock_size", {})
                if terminal_size:
                    _restore_dock_size_simple(canvas_host._terminal_dock, terminal_size, canvas_host)
    
    QTimer.singleShot(500, _restore_terminal_dock_size)


def _restore_dock_size_simple(dock, size_info, parent_window):
    """简单版恢复 Dock 尺寸"""
    try:
        if not dock or not size_info:
            return
        
        floating = size_info.get("floating", False)
        dock.setFloating(floating)
        
        if floating:
            x = size_info.get("x")
            y = size_info.get("y")
            width = size_info.get("width")
            height = size_info.get("height")
            if all(v is not None for v in [x, y, width, height]):
                dock.setGeometry(x, y, width, height)
        else:
            width = size_info.get("width")
            height = size_info.get("height")
            
            if width and height:
                area = parent_window.dockWidgetArea(dock)
                if area in [Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea]:
                    parent_window.resizeDocks([dock], [width], Qt.Orientation.Horizontal)
                elif area in [Qt.DockWidgetArea.TopDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea]:
                    parent_window.resizeDocks([dock], [height], Qt.Orientation.Vertical)
    except Exception as e:
        logger.warning("恢复 Dock 尺寸失败: %s", e)


def _center_window(main_window, width, height):
    """将窗口居中显示"""
    screen_geometry = QApplication.primaryScreen().geometry()
    x = (screen_geometry.width() - width) // 2
    y = (screen_geometry.height() - height) // 2
    main_window.setGeometry(x, y, width, height)
```

### 步骤 3：主窗口集成

确保 `main_window.py` 中正确调用新的保存和恢复方法（已有的调用应该已经可以工作）。

### 步骤 4：处理 CanvasHost 中的 Dock

CanvasHost 中的终端 Dock 也需要类似的处理，已经在上面的方案中包含了。

---

## 五、关键技术点

### 5.1 resizeDocks 的使用

```python
# 左右停靠区域，调整宽度
main_window.resizeDocks([dock1, dock2], [width1, width2], Qt.Orientation.Horizontal)

# 上下停靠区域，调整高度
main_window.resizeDocks([dock1, dock2], [height1, height2], Qt.Orientation.Vertical)
```

### 5.2 Qt saveState/restoreState 的限制

- `saveState()` 保存的是布局结构，不保存所有细节
- 需要在 Dock 创建完成后才能调用 `restoreState()`
- 有些状态需要手动补充恢复

### 5.3 分阶段恢复的时机

```
启动 → UI 初始化 → 创建 Dock → [100ms] 恢复 Qt 状态 → [200ms] 调整 Dock 尺寸 → [100ms] 恢复终端
```

---

## 六、测试方案

### 6.1 测试用例

1. **单个 Dock 测试**
   - 打开一个 Dock，调整尺寸
   - 重启应用，验证尺寸是否恢复

2. **多个 Dock 堆叠测试**
   - 打开两个 Dock，堆叠成标签页
   - 调整尺寸，重启验证

3. **浮动 Dock 测试**
   - 将 Dock 拖出成浮动窗口
   - 调整位置和尺寸，重启验证

4. **多区域测试**
   - 左右区域都有 Dock
   - 调整各区域尺寸，重启验证

5. **终端 Dock 测试**
   - 显示/隐藏终端，调整尺寸
   - 重启验证

---

## 七、向后兼容

### 7.1 旧数据处理

- 检测是否有新格式数据（`dock_layout.version == "1.0"`）
- 如果没有，回退到旧的恢复逻辑
- 旧数据（`main_dock_sizes`、`terminal_dock_size`）仍然支持

### 7.2 渐进式升级

- 保存时同时保存新旧两种格式（可选）
- 或者只保存新格式，旧格式作为备份

---

## 八、总结

本方案通过以下方式解决 Dock 吸附堆叠后的尺寸持久化问题：

1. ✅ 结合 Qt 原生 `saveState/restoreState` 和自定义管理
2. ✅ 使用 `resizeDocks()` 替代直接 `resize()`
3. ✅ 分阶段恢复，确保时机正确
4. ✅ 保存完整的 Dock 信息（尺寸、可见性、位置）
5. ✅ 向后兼容旧数据格式

该方案参考了 Photoshop 的面板管理思想，提供了灵活且可靠的 Dock 布局持久化功能。
