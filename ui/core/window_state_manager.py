"""
窗口状态持久化管理 — 保存/恢复窗口几何、面板状态、画布视图、Dock尺寸
"""
from PyQt6.QtWidgets import QApplication, QDockWidget
from ui.core.logger import logger


def save_state(main_window):
    """保存窗口状态 - 完整布局持久化"""
    try:
        logger.info("💾 ===== 开始保存窗口状态 =====")
        
        # ===== 保存窗口几何信息 =====
        geometry = {
            "x": main_window.geometry().x(),
            "y": main_window.geometry().y(),
            "width": main_window.geometry().width(),
            "height": main_window.geometry().height(),
            "maximized": main_window.isMaximized()
        }
        logger.info("💾 窗口几何: %s", geometry)
        main_window.app_config.set("window_geometry", geometry)
        
        # ===== 保存主窗口的所有 Dock 尺寸 =====
        main_dock_sizes = {}
        all_docks = main_window.findChildren(QDockWidget)
        logger.info("💾 找到 %d 个 Dock 窗口", len(all_docks))
        
        for i, dock in enumerate(all_docks):
            dock_title = dock.windowTitle()
            if not dock_title:
                logger.warning("💾 跳过第 %d 个 Dock（无标题）", i)
                continue
                
            dock_area = main_window.dockWidgetArea(dock)
            is_floating = dock.isFloating()
            
            logger.info("💾 处理 Dock %d: %s（浮动: %s, 停靠位置: %s）", i, dock_title, is_floating, dock_area)
            
            if is_floating:
                main_dock_sizes[dock_title] = {
                    "floating": True,
                    "x": dock.geometry().x(),
                    "y": dock.geometry().y(),
                    "width": dock.geometry().width(),
                    "height": dock.geometry().height()
                }
            else:
                main_dock_sizes[dock_title] = {
                    "floating": False,
                    "width": dock.width(),
                    "height": dock.height()
                }
        
        main_window.app_config.set("main_dock_sizes", main_dock_sizes)
        logger.info("💾 主窗口 Dock 尺寸已保存: %s", main_dock_sizes)
        
        # ===== 保存 CanvasHost 里的终端 Dock 尺寸 =====
        if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
            ch = main_window._canvas_host
            if hasattr(ch, '_terminal_dock') and ch._terminal_dock:
                term_dock = ch._terminal_dock
                term_floating = term_dock.isFloating()
                
                if term_floating:
                    terminal_size = {
                        "floating": True,
                        "x": term_dock.geometry().x(),
                        "y": term_dock.geometry().y(),
                        "width": term_dock.geometry().width(),
                        "height": term_dock.geometry().height()
                    }
                else:
                    terminal_size = {
                        "floating": False,
                        "width": term_dock.width(),
                        "height": term_dock.height()
                    }
                
                main_window.app_config.set("terminal_dock_size", terminal_size)
                logger.info("💾 终端 Dock 尺寸已保存: %s", terminal_size)
            else:
                logger.info("💾 CanvasHost 没有找到终端 Dock")
        else:
            logger.info("💾 没有找到 CanvasHost")
        
        # ===== 保存画布视图状态 =====
        if main_window.current_project_path:
            main_window.app_config.set("last_project", main_window.current_project_path)

            view_state = {
                "scale": main_window.canvas.transform().m11(),
                "scroll_x": main_window.canvas.horizontalScrollBar().value(),
                "scroll_y": main_window.canvas.verticalScrollBar().value()
            }
            main_window.app_config.set("canvas_view_state", view_state)

            main_window.canvas.save_layout(main_window.current_project_path)

        main_window.app_config.save()
        logger.info("💾 ===== 窗口状态已保存 =====")
    except Exception as e:
        logger.error("❌ 保存窗口状态失败: %s", e, exc_info=True)


def _center_window(main_window, width, height):
    """将窗口居中显示在屏幕上"""
    screen_geometry = QApplication.primaryScreen().geometry()
    x = (screen_geometry.width() - width) // 2
    y = (screen_geometry.height() - height) // 2
    main_window.setGeometry(x, y, width, height)
    logger.info(f"窗口已居中: ({x}, {y})")


def _restore_dock_size(dock, size_info, parent_window):
    """恢复单个 Dock 的尺寸"""
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
                # 对于停靠的 Dock，直接 resize，不设置限制
                dock.resize(width, height)
                parent_window.update()
    
    except Exception as e:
        logger.warning("恢复 Dock 尺寸失败: %s", e)


def restore_state(main_window):
    """恢复窗口状态 - 完整布局还原"""
    try:
        logger.info("📐 ===== 开始恢复窗口状态 =====")
        
        # ===== 恢复窗口几何信息 =====
        geom = main_window.app_config.get("window_geometry")
        if geom:
            logger.info("📐 恢复窗口几何: %s", geom)
            if geom.get("maximized", False):
                main_window.showMaximized()
            else:
                width = geom.get("width", 1400)
                height = geom.get("height", 900)
                _center_window(main_window, width, height)
        else:
            logger.info("📐 没有找到窗口几何配置，使用默认居中")
            _center_window(main_window, 1400, 900)
        
        from PyQt6.QtCore import QTimer
        
        # ===== 300ms: 恢复主窗口的 Dock 尺寸 =====
        def _restore_main_dock_sizes():
            logger.info("📐 [300ms] 开始恢复主窗口 Dock 尺寸")
            main_dock_sizes = main_window.app_config.get("main_dock_sizes", {})
            logger.info("📐 [300ms] 从配置读取 main_dock_sizes: %s", main_dock_sizes)
            
            if main_dock_sizes:
                all_docks = main_window.findChildren(QDockWidget)
                logger.info("📐 [300ms] 主窗口找到 %d 个 Dock", len(all_docks))
                
                for i, dock in enumerate(all_docks):
                    dock_title = dock.windowTitle()
                    if dock_title and dock_title in main_dock_sizes:
                        logger.info("📐 [300ms] 恢复 Dock %d: %s", i, dock_title)
                        _restore_dock_size(dock, main_dock_sizes[dock_title], main_window)
                    else:
                        logger.info("📐 [300ms] 跳过 Dock %d: %s（无配置）", i, dock_title)
            else:
                logger.info("📐 [300ms] 没有找到 main_dock_sizes 配置")
        
        QTimer.singleShot(300, _restore_main_dock_sizes)
        
        # ===== 500ms: 恢复终端 Dock 尺寸 =====
        def _restore_terminal_dock_size():
            logger.info("📐 [500ms] 开始恢复终端 Dock 尺寸")
            if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
                ch = main_window._canvas_host
                if hasattr(ch, '_terminal_dock') and ch._terminal_dock:
                    terminal_size = main_window.app_config.get("terminal_dock_size", {})
                    logger.info("📐 [500ms] 从配置读取 terminal_dock_size: %s", terminal_size)
                    
                    if terminal_size:
                        logger.info("📐 [500ms] 恢复终端 Dock 尺寸")
                        _restore_dock_size(ch._terminal_dock, terminal_size, ch)
                    else:
                        logger.info("📐 [500ms] 没有找到 terminal_dock_size 配置")
                else:
                    logger.info("📐 [500ms] CanvasHost 没有找到终端 Dock")
            else:
                logger.info("📐 [500ms] 没有找到 CanvasHost")
        
        QTimer.singleShot(500, _restore_terminal_dock_size)
        
        logger.info("📐 ===== 窗口状态已恢复 =====")
    except Exception as e:
        logger.error("❌ 恢复窗口状态失败: %s", e, exc_info=True)
