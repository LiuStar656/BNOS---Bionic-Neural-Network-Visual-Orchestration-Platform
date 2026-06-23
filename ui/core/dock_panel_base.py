"""
Dock 面板统一基类（对标 Photoshop Panel 基类）

设计原则:
- 所有 Dock 面板继承此类而非 QWidget
- 构造函数自动处理 destroyed → dispose 绑定
- 子类只需实现 _init_ui() 和业务逻辑
- 子类通过 _schedule_update() 代替 QTimer.start()
- 子类通过 _run_in_thread() 代替 QThread()
- dispose() 幂等，可在 __del__ / destroyed 信号中安全调用

用法:
    class MyPanel(DockPanelBase):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._init_ui()
            self._schedule_update(1000, self._refresh)

        def _init_ui(self):
            # 添加 UI 组件到此面板
            pass

        def _refresh(self):
            # 每秒调用的更新逻辑
            pass
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from ui.core.lifecycle_managed import LifecycleManaged
from ui.core.i18n import t


class DockPanelBase(QWidget, LifecycleManaged):
    """Dock 面板统一基类

    组合 QWidget + LifecycleManaged，提供:
    - 自动资源清理（destroyed → dispose）
    - 统一更新调度（_schedule_update）
    - 统一线程池（_run_in_thread）
    - 标准面板样式
    """

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        LifecycleManaged.__init__(self)
        self._title = ""
        self._title_label = None

        # 自动绑定：widget 销毁时调用 dispose()
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        """QObject.destroyed 信号的处理器"""
        self.dispose()

    def dispose(self):
        """释放所有资源（子类可重写以添加额外清理）"""
        LifecycleManaged.dispose(self)

    # ── 标题 ──
    def set_panel_title(self, title: str):
        """设置面板标题"""
        self._title = title
        if self._title_label:
            self._title_label.setText(title)

    def get_panel_title(self) -> str:
        """获取面板标题"""
        return self._title

    # ── 标准标题栏 ──
    def _create_standard_title_bar(self, layout: QVBoxLayout, title: str):
        """创建标准的面板标题栏（深色背景 + border-bottom）

        Args:
            layout: 面板的主布局
            title: 标题文本

        Returns:
            (title_bar_widget, title_label)
        """
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #252526; border-bottom: 1px solid #3c3c3c;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(
            "color: rgba(255,255,255,180); font-size: 11px; font-weight: bold; border: none;"
        )
        self._title = title
        top_layout.addWidget(self._title_label)
        top_layout.addStretch()
        layout.addWidget(top_bar)
        return top_bar, self._title_label

    # ── 标准内容区域 ──
    @staticmethod
    def _create_content_area(layout: QVBoxLayout):
        """创建标准的内容区域（带 padding 的 QWidget）

        Args:
            layout: 面板的主布局

        Returns:
            (content_widget, content_layout)
        """
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        layout.addWidget(content_widget, 1)
        return content_widget, content_layout

    # ── 标准初始化 ──
    def _init_panel_layout(self, title: str):
        """创建标准面板布局（标题栏 + 内容区域）

        Args:
            title: 面板标题

        Returns:
            (main_layout, content_layout)
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_standard_title_bar(main_layout, title)
        content_widget, content_layout = self._create_content_area(main_layout)

        return main_layout, content_layout
