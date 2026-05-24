"""
窗口状态持久化管理 — 保存/恢复窗口几何、面板状态、画布视图
"""
from PyQt6.QtWidgets import QApplication
from ui.core.logger import logger


def save_state(main_window):
    """保存窗口状态 - 完整布局持久化"""
    try:
        geometry = {
            "x": main_window.geometry().x(),
            "y": main_window.geometry().y(),
            "width": main_window.geometry().width(),
            "height": main_window.geometry().height(),
            "maximized": main_window.isMaximized()
        }
        main_window.app_config.set("window_geometry", geometry)

        if main_window.current_project_path:
            main_window.app_config.set("last_project", main_window.current_project_path)

            view_state = {
                "scale": main_window.canvas.transform().m11(),
                "scroll_x": main_window.canvas.horizontalScrollBar().value(),
                "scroll_y": main_window.canvas.verticalScrollBar().value()
            }
            main_window.app_config.set("canvas_view_state", view_state)

            # 节点列表面板状态由 _save_panel_visibility 处理，这里不再重复保存
            # 保留 node_list_panel 配置项用于向后兼容

            main_window.canvas.save_layout(main_window.current_project_path)

        main_window.app_config.save()
        logger.info("窗口状态已保存")
    except Exception as e:
        logger.error("保存窗口状态失败: %s", e)


def _center_window(main_window, width, height):
    """将窗口居中显示在屏幕上"""
    screen_geometry = QApplication.primaryScreen().geometry()
    x = (screen_geometry.width() - width) // 2
    y = (screen_geometry.height() - height) // 2
    main_window.setGeometry(x, y, width, height)
    logger.info(f"窗口已居中: ({x}, {y})")


def restore_state(main_window):
    """恢复窗口状态 - 完整布局还原"""
    try:
        geom = main_window.app_config.get("window_geometry")
        if geom:
            if geom.get("maximized", False):
                main_window.showMaximized()
            else:
                # 每次打开都将窗口居中
                width = geom.get("width", 1400)
                height = geom.get("height", 900)
                _center_window(main_window, width, height)
        else:
            # 首次打开，窗口居中
            _center_window(main_window, 1400, 900)

        # 节点列表面板的恢复由 _restore_panel_state 处理，这里不再重复处理
        # 保留旧配置项的读取但不进行操作，避免与 _restore_panel_state 冲突

        logger.info("窗口状态已恢复")
    except Exception as e:
        logger.warning("恢复窗口状态失败，使用默认布局: %s", e)