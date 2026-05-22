"""
窗口状态持久化管理 — 保存/恢复窗口几何、面板状态、画布视图
"""
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

            panel_state = {
                "visible": main_window.node_list_panel.isVisible(),
                "x": main_window.node_list_panel.geometry().x(),
                "y": main_window.node_list_panel.geometry().y(),
                "width": main_window.node_list_panel.geometry().width(),
                "height": main_window.node_list_panel.geometry().height()
            }
            main_window.app_config.set("node_list_panel", panel_state)

            main_window.canvas.save_layout(main_window.current_project_path)

        main_window.app_config.save()
        logger.info("窗口状态已保存")
    except Exception as e:
        logger.error("保存窗口状态失败: %s", e)


def restore_state(main_window):
    """恢复窗口状态 - 完整布局还原"""
    try:
        geom = main_window.app_config.get("window_geometry")
        if geom:
            if geom.get("maximized", False):
                main_window.showMaximized()
            else:
                main_window.setGeometry(
                    geom.get("x", 100), geom.get("y", 100),
                    geom.get("width", 1400), geom.get("height", 900)
                )

        panel_state = main_window.app_config.get("node_list_panel")
        if panel_state and hasattr(main_window, 'node_list_panel'):
            if isinstance(panel_state, dict):
                x = panel_state.get("x", 50)
                y = panel_state.get("y", 100)
                w = panel_state.get("width", 280)
                h = panel_state.get("height", 600)
                main_window.node_list_panel.setGeometry(x, y, w, h)

                visible = panel_state.get("visible", False)
                if visible:
                    main_window.node_list_panel.show()
                    main_window.toggle_nodes_action.setChecked(True)
                else:
                    main_window.node_list_panel.hide()
                    main_window.toggle_nodes_action.setChecked(False)

        logger.info("窗口状态已恢复")
    except Exception as e:
        logger.warning("恢复窗口状态失败，使用默认布局: %s", e)
