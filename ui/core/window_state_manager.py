"""
【优化】窗口状态持久化管理

核心思路（参考 VSCode）：
1. 保存时：
   - 先调用 Qt saveState()（保存 Dock 布局和分割条位置）
   - 再保存自定义的尺寸信息

2. 恢复时（关键！）：
   - 先创建所有需要的 Dock（在 main_window 中完成）
   - 然后调用 Qt restoreState()（恢复布局和分割条位置）
   - 最后用 resizeDocks() 精确调整尺寸
"""
from PySide6.QtWidgets import QApplication, QDockWidget
from PySide6.QtCore import Qt
from ui.core.logger import logger
import base64


def save_state(main_window):
    """保存窗口状态"""
    try:
        logger.info("[SAVE] ===== 开始保存窗口状态 =====")
        
        # 1. 保存窗口几何信息
        geometry = {
            "x": main_window.geometry().x(),
            "y": main_window.geometry().y(),
            "width": main_window.geometry().width(),
            "height": main_window.geometry().height(),
            "maximized": main_window.isMaximized()
        }
        main_window.app_config.set("window_geometry", geometry)
        
        # 2. 保存 Qt 原生状态（这个最关键！包含 Dock 布局和分割条位置）
        qt_state = main_window.saveState()
        qt_state_base64 = base64.b64encode(qt_state).decode('utf-8')
        
        # 3. 保存 CanvasHost 的状态
        canvas_host_state = None
        canvas_host_area_layouts = None
        if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
            canvas_host = main_window._canvas_host
            # 保存 CanvasHost 的 Qt 原生状态
            canvas_host_qt_state = canvas_host.saveState()
            canvas_host_state_base64 = base64.b64encode(canvas_host_qt_state).decode('utf-8')
            # 收集 CanvasHost 中的区域布局信息
            canvas_host_area_layouts = _collect_canvas_host_area_layouts(canvas_host)
            canvas_host_state = {
                "qt_state": canvas_host_state_base64,
                "area_layouts": canvas_host_area_layouts
            }
            logger.info("[SAVE] 已保存 CanvasHost 状态")
        
        # 4. 收集所有 Dock 信息（用于补充调整尺寸）
        dock_info = _collect_dock_info(main_window)
        
        # 5. 收集区域布局信息（显式保存尺寸）
        area_layouts = _collect_area_layouts(main_window)
        
        # 6. 收集终端 Dock 信息
        terminal_info = _collect_terminal_dock_info(main_window)
        
        # 7. 组合保存数据
        full_state = {
            "version": "4.0",  # 新版本号，添加了 CanvasHost 支持
            "qt_state": qt_state_base64,
            "canvas_host_state": canvas_host_state,
            "docks": dock_info,
            "area_layouts": area_layouts,
            "terminal_dock": terminal_info
        }
        
        main_window.app_config.set("dock_layout", full_state)
        logger.info("[SAVE] 保存完成: %d 个 Dock, %d 个区域", 
                    len(dock_info), len(area_layouts))
        
        # 7. 保存画布视图状态（保持原逻辑）
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
        logger.info("[SAVE] ===== 窗口状态保存完成 =====")
        
    except Exception as e:
        logger.error("❌ 保存窗口状态失败: %s", e, exc_info=True)


def _collect_area_layouts(main_window):
    """收集每个区域的布局信息（显式保存分割条位置）"""
    area_layouts = {}
    
    all_docks = main_window.findChildren(QDockWidget)
    
    # 按区域分组
    for area_enum, area_name in [
        (Qt.DockWidgetArea.LeftDockWidgetArea, "left"),
        (Qt.DockWidgetArea.RightDockWidgetArea, "right"),
        (Qt.DockWidgetArea.TopDockWidgetArea, "top"),
        (Qt.DockWidgetArea.BottomDockWidgetArea, "bottom")
    ]:
        area_docks = []
        for dock in all_docks:
            if main_window.dockWidgetArea(dock) == area_enum and not dock.isFloating():
                area_docks.append({
                    "title": dock.windowTitle(),
                    "width": dock.width(),
                    "height": dock.height(),
                    "visible": dock.isVisible()
                })
        
        if area_docks:
            # 确定该区域的方向
            orientation = "horizontal" if area_name in ["left", "right"] else "vertical"
            
            area_layouts[area_name] = {
                "orientation": orientation,
                "docks": area_docks
            }
            logger.debug("[SAVE] 区域 %s 布局: %d 个 Dock", area_name, len(area_docks))
    
    return area_layouts


def _collect_canvas_host_area_layouts(canvas_host):
    """收集 CanvasHost 中每个区域的布局信息（显式保存分割条位置）"""
    area_layouts = {}
    
    all_docks = canvas_host.findChildren(QDockWidget)
    
    # 按区域分组
    for area_enum, area_name in [
        (Qt.DockWidgetArea.LeftDockWidgetArea, "left"),
        (Qt.DockWidgetArea.RightDockWidgetArea, "right"),
        (Qt.DockWidgetArea.TopDockWidgetArea, "top"),
        (Qt.DockWidgetArea.BottomDockWidgetArea, "bottom")
    ]:
        area_docks = []
        for dock in all_docks:
            if canvas_host.dockWidgetArea(dock) == area_enum and not dock.isFloating():
                area_docks.append({
                    "title": dock.windowTitle(),
                    "width": dock.width(),
                    "height": dock.height(),
                    "visible": dock.isVisible()
                })
        
        if area_docks:
            # 确定该区域的方向
            orientation = "horizontal" if area_name in ["left", "right"] else "vertical"
            
            area_layouts[area_name] = {
                "orientation": orientation,
                "docks": area_docks
            }
            logger.debug("[SAVE] CanvasHost 区域 %s 布局: %d 个 Dock", area_name, len(area_docks))
    
    return area_layouts


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
        logger.debug("[SAVE] 收集 Dock: %s (floating=%s, area=%s, w=%d, h=%d)", 
                    title, dock.isFloating(), area_name, dock.width(), dock.height())
    
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
    """恢复窗口状态（主窗口）
    
    【重要】调用此方法前必须已经创建好了所有的 Dock！
    【注意】CanvasHost 的恢复会在项目打开后单独调用，因为画布 Dock 在那时才创建
    """
    try:
        logger.info("[WS] ===== 开始恢复窗口状态 =====")
        
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
        
        if dock_layout and dock_layout.get("version") in ["1.0", "1.1", "2.0", "3.0", "4.0"]:
            # 分阶段恢复（主窗口）
            from PySide6.QtCore import QTimer
            
            # ===== 阶段 1：立即恢复 Qt 原生状态 =====
            logger.info("[WS] 阶段 1：立即恢复 Qt 原生状态")
            _restore_phase1(main_window, dock_layout)
            
            # ===== 阶段 2：第一次调整尺寸 =====
            QTimer.singleShot(200, lambda: _restore_phase2(main_window, dock_layout))
            
            # ===== 阶段 3：第二次调整尺寸（巩固分割条位置） =====
            QTimer.singleShot(400, lambda: _restore_phase3(main_window, dock_layout))
            
            # ===== 阶段 4：恢复终端 Dock =====
            QTimer.singleShot(500, lambda: _restore_phase4(main_window, dock_layout))
        else:
            logger.info("[WS] 未找到增强版布局数据，使用简单恢复")
            _restore_simple(main_window)
        
        logger.info("[WS] ===== 主窗口状态恢复启动 =====")
        
    except Exception as e:
        logger.error("❌ 恢复窗口状态失败: %s", e, exc_info=True)


def restore_canvas_host_state(main_window):
    """恢复 CanvasHost 的状态
    
    【重要】调用此方法前必须已经创建好了画布 Dock！
    应该在项目打开后调用
    """
    try:
        logger.info("[WS] ===== 开始恢复 CanvasHost 状态 =====")
        
        dock_layout = main_window.app_config.get("dock_layout")
        
        if dock_layout and dock_layout.get("version") in ["4.0"]:
            # 分阶段恢复（CanvasHost）
            from PySide6.QtCore import QTimer
            
            # ===== 阶段 5：恢复 CanvasHost 的 Qt 原生状态 =====
            logger.info("[WS] 阶段 5：恢复 CanvasHost Qt 原生状态")
            _restore_phase5(main_window, dock_layout)
            
            # ===== 阶段 6：第一次调整 CanvasHost 尺寸 =====
            QTimer.singleShot(200, lambda: _restore_phase6(main_window, dock_layout))
            
            # ===== 阶段 7：第二次调整 CanvasHost 尺寸（巩固分割条位置） =====
            QTimer.singleShot(400, lambda: _restore_phase7(main_window, dock_layout))
        else:
            logger.info("[WS] 未找到 CanvasHost 状态数据")
        
        logger.info("[WS] ===== CanvasHost 状态恢复启动 =====")
        
    except Exception as e:
        logger.error("❌ 恢复 CanvasHost 状态失败: %s", e, exc_info=True)


def _restore_phase1(main_window, dock_layout):
    """阶段 1：恢复 Qt 原生状态（最关键！恢复布局和分割条位置）"""
    logger.info("[WS] [阶段 1] 恢复 Qt 原生状态")
    
    try:
        qt_state_base64 = dock_layout.get("qt_state")
        if qt_state_base64:
            qt_state = base64.b64decode(qt_state_base64.encode('utf-8'))
            main_window.restoreState(qt_state)
            logger.info("[WS] [OK] Qt 原生状态已恢复（包含布局和分割条位置）")
    except Exception as e:
        logger.warning("[WS] 恢复 Qt 原生状态失败: %s", e)


def _restore_phase2(main_window, dock_layout):
    """阶段 2：第一次用 area_layouts 调整尺寸"""
    logger.info("[WS] [阶段 2] 第一次调整 Dock 尺寸")
    
    area_layouts = dock_layout.get("area_layouts", {})
    
    if area_layouts:
        _restore_from_area_layouts(main_window, area_layouts, pass_num=1)
    else:
        docks_info = dock_layout.get("docks", [])
        docks_by_area = {}
        for info in docks_info:
            area = info.get("area", "unknown")
            if area not in docks_by_area:
                docks_by_area[area] = []
            docks_by_area[area].append(info)
        for area_name, area_docks in docks_by_area.items():
            _restore_area_docks_legacy(main_window, area_name, area_docks, pass_num=1)


def _restore_phase3(main_window, dock_layout):
    """阶段 3：第二次调整尺寸（巩固分割条位置）"""
    logger.info("[WS] [阶段 3] 第二次调整 Dock 尺寸（巩固分割条）")
    
    area_layouts = dock_layout.get("area_layouts", {})
    
    if area_layouts:
        _restore_from_area_layouts(main_window, area_layouts, pass_num=2)
    else:
        docks_info = dock_layout.get("docks", [])
        docks_by_area = {}
        for info in docks_info:
            area = info.get("area", "unknown")
            if area not in docks_by_area:
                docks_by_area[area] = []
            docks_by_area[area].append(info)
        for area_name, area_docks in docks_by_area.items():
            _restore_area_docks_legacy(main_window, area_name, area_docks, pass_num=2)


def _restore_from_area_layouts(main_window, area_layouts, pass_num=1):
    """用 area_layouts 恢复 Dock 尺寸"""
    all_docks = main_window.findChildren(QDockWidget)
    dock_map = {dock.windowTitle(): dock for dock in all_docks}
    
    for area_name, area_info in area_layouts.items():
        area = _name_to_dock_area(area_name)
        if area == Qt.DockWidgetArea.NoDockWidgetArea:
            continue
        
        orientation = area_info.get("orientation", "horizontal")
        area_docks_info = area_info.get("docks", [])
        
        area_dock_widgets = []
        area_dock_sizes = []
        
        for dock_info in area_docks_info:
            title = dock_info.get("title")
            dock = dock_map.get(title)
            if dock and not dock.isFloating():
                area_dock_widgets.append(dock)
                if orientation == "horizontal":
                    area_dock_sizes.append(dock_info.get("width", 200))
                else:
                    area_dock_sizes.append(dock_info.get("height", 300))
        
        if area_dock_widgets and area_dock_sizes:
            try:
                qt_orientation = Qt.Orientation.Horizontal if orientation == "horizontal" else Qt.Orientation.Vertical
                main_window.resizeDocks(area_dock_widgets, area_dock_sizes, qt_orientation)
                
                logger.info("[WS] [第%d次] %s区域: %s", 
                           pass_num, area_name, area_dock_sizes)
            except Exception as e:
                logger.warning("[WS] 调整失败: %s", e)


def _restore_area_docks_legacy(main_window, area_name, docks_info, pass_num=1):
    """旧版方法：恢复指定区域的 Dock（兼容旧版本）"""
    area = _name_to_dock_area(area_name)
    if area == Qt.DockWidgetArea.NoDockWidgetArea:
        return
    
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
    
    if area_dock_widgets and area_dock_sizes:
        try:
            orientation = Qt.Orientation.Horizontal
            if area in [Qt.DockWidgetArea.TopDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea]:
                orientation = Qt.Orientation.Vertical
            
            main_window.resizeDocks(area_dock_widgets, area_dock_sizes, orientation)
            logger.info("[WS] [第%d次][旧版] %s: %s", 
                       pass_num, area_name, area_dock_sizes)
        except Exception as e:
            logger.warning("[WS] 调整失败: %s", e)


def _restore_phase4(main_window, dock_layout):
    """阶段 4：恢复终端 Dock"""
    logger.info("[WS] [阶段 4] 恢复终端 Dock")
    
    terminal_info = dock_layout.get("terminal_dock")
    if not terminal_info:
        logger.info("[WS] 未找到终端 Dock 信息")
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
            
            # 恢复尺寸（如果是停靠状态） - 阶段 6-7 会再精确调整
            if not terminal_info.get("floating", False):
                size = terminal_info.get("size", {})
                height = size.get("height")
                if height:
                    try:
                        canvas_host.resizeDocks([term_dock], [height], Qt.Orientation.Vertical)
                        logger.info("[WS] 终端高度已设置: %d", height)
                    except Exception as e:
                        logger.warning("[WS] 终端调整失败: %s", e)
            
            logger.info("[WS] 终端 Dock 恢复完成: visible=%s", visible)
    
    logger.info("[WS] ===== 主窗口状态恢复完成 =====")


def _restore_phase5(main_window, dock_layout):
    """阶段 5：恢复 CanvasHost 的 Qt 原生状态（最关键！恢复布局和分割条位置）"""
    logger.info("[WS] [阶段 5] 恢复 CanvasHost Qt 原生状态")
    
    try:
        canvas_host_state = dock_layout.get("canvas_host_state")
        if canvas_host_state:
            if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
                canvas_host = main_window._canvas_host
                canvas_host_qt_state_base64 = canvas_host_state.get("qt_state")
                if canvas_host_qt_state_base64:
                    canvas_host_qt_state = base64.b64decode(canvas_host_qt_state_base64.encode('utf-8'))
                    canvas_host.restoreState(canvas_host_qt_state)
                    logger.info("[WS] [OK] CanvasHost Qt 原生状态已恢复（包含布局和分割条位置）")
    except Exception as e:
        logger.warning("[WS] 恢复 CanvasHost Qt 原生状态失败: %s", e)


def _restore_phase6(main_window, dock_layout):
    """阶段 6：第一次调整 CanvasHost 尺寸"""
    logger.info("[WS] [阶段 6] 第一次调整 CanvasHost 尺寸")
    
    canvas_host_state = dock_layout.get("canvas_host_state")
    if not canvas_host_state:
        logger.info("[WS] 未找到 CanvasHost 状态")
        return
    
    area_layouts = canvas_host_state.get("area_layouts", {})
    if area_layouts:
        if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
            canvas_host = main_window._canvas_host
            _restore_canvas_host_from_area_layouts(canvas_host, area_layouts, pass_num=1)


def _restore_phase7(main_window, dock_layout):
    """阶段 7：第二次调整 CanvasHost 尺寸（巩固分割条位置）"""
    logger.info("[WS] [阶段 7] 第二次调整 CanvasHost 尺寸（巩固分割条）")
    
    canvas_host_state = dock_layout.get("canvas_host_state")
    if not canvas_host_state:
        logger.info("[WS] 未找到 CanvasHost 状态")
        return
    
    area_layouts = canvas_host_state.get("area_layouts", {})
    if area_layouts:
        if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
            canvas_host = main_window._canvas_host
            _restore_canvas_host_from_area_layouts(canvas_host, area_layouts, pass_num=2)
    
    logger.info("[WS] ===== CanvasHost 状态完全恢复 =====")


def _restore_canvas_host_from_area_layouts(canvas_host, area_layouts, pass_num=1):
    """用 area_layouts 恢复 CanvasHost 中 Dock 的尺寸"""
    all_docks = canvas_host.findChildren(QDockWidget)
    dock_map = {dock.windowTitle(): dock for dock in all_docks}
    
    for area_name, area_info in area_layouts.items():
        area = _name_to_dock_area(area_name)
        if area == Qt.DockWidgetArea.NoDockWidgetArea:
            continue
        
        orientation = area_info.get("orientation", "horizontal")
        area_docks_info = area_info.get("docks", [])
        
        area_dock_widgets = []
        area_dock_sizes = []
        
        for dock_info in area_docks_info:
            title = dock_info.get("title")
            dock = dock_map.get(title)
            if dock and not dock.isFloating():
                area_dock_widgets.append(dock)
                if orientation == "horizontal":
                    area_dock_sizes.append(dock_info.get("width", 200))
                else:
                    area_dock_sizes.append(dock_info.get("height", 300))
        
        if area_dock_widgets and area_dock_sizes:
            try:
                qt_orientation = Qt.Orientation.Horizontal if orientation == "horizontal" else Qt.Orientation.Vertical
                canvas_host.resizeDocks(area_dock_widgets, area_dock_sizes, qt_orientation)
                
                logger.info("[WS] [CanvasHost 第%d次] %s区域: %s", 
                           pass_num, area_name, area_dock_sizes)
            except Exception as e:
                logger.warning("[WS] CanvasHost 调整失败: %s", e)


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
        logger.warning("恢复失败: %s", e)


def _center_window(main_window, width, height):
    """将窗口居中显示"""
    screen_geometry = QApplication.primaryScreen().geometry()
    x = (screen_geometry.width() - width) // 2
    y = (screen_geometry.height() - height) // 2
    main_window.setGeometry(x, y, width, height)
    logger.info("窗口已居中: (%d, %d) %dx%d", x, y, width, height)
