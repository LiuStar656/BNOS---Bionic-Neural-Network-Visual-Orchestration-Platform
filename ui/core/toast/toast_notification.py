"""
BNOS Toast 通知系统 - 右上角自动消失的通知弹窗

采用"外层透明窗口 + 内层QFrame承载样式"的双层架构，参考 dialog_utils.py 和
floating_panel.py 的成熟实现模式。使用 setWindowOpacity 做淡入淡出动画，
避免 QGraphicsOpacityEffect 与 WA_TranslucentBackground 的兼容性问题。

新增功能：
- Toast显示区域严格限制在右上角固定区域内
- 跟随窗口移动、大小调整自动更新位置（使用定时器轮询方案）
- Toast与画布dock关闭按钮垂直对齐
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication, QDockWidget
from PySide6.QtCore import Qt, QTimer, Signal, QRect, QPoint
from PySide6.QtGui import QGuiApplication

# 尝试导入BnosDock
try:
    from ui.core.bnos_dock import BnosDock
    HAS_BNOS_DOCK = True
except ImportError:
    HAS_BNOS_DOCK = False


# ---------------- 全局配置 ----------------

_toast_config = {
    'info_color': 'rgba(50, 50, 50, 230)',
    'success_color': 'rgba(76, 175, 80, 230)',
    'warning_color': 'rgba(255, 152, 0, 230)',
    'error_color': 'rgba(244, 67, 54, 230)',
    'text_color': '#ffffff',
}


def set_toast_config(config):
    """设置Toast全局配置"""
    global _toast_config
    _toast_config.update(config)


def get_toast_config():
    """获取Toast全局配置"""
    return _toast_config.copy()


# ---------------- Toast 组件 ----------------

class ToastNotification(QWidget):
    """右上角自动消失的通知弹窗（Toast）

    架构要点：
    - 外层：QWidget，仅设 WA_TranslucentBackground，完全透明，不绘制任何内容
    - 内层：QLabel，通过 stylesheet 绘制 rgba 背景色 + border-radius 圆角 + 文字
    - 动画：QTimer 驱动 setWindowOpacity() 做淡入淡出，每16ms一帧 ≈ 60fps
    - 边界限制：Toast显示区域严格限制在右上角固定区域内
    - 跟随移动：使用定时器轮询检测父窗口变化，自动更新位置
    """
    
    # 信号：Toast关闭时发出
    closed = Signal()

    # Toast显示区域配置（相对于父窗口）
    _DISPLAY_AREA_WIDTH = 320    # 显示区域宽度
    _DISPLAY_AREA_HEIGHT = 400   # 显示区域高度
    _DISPLAY_AREA_MARGIN_RIGHT = 15  # 右边缘距离
    _DISPLAY_AREA_MARGIN_TOP = 40    # 上边缘距离（避开标题栏）
    _TOAST_SPACING = 55           # Toast之间的垂直间距

    def __init__(self, message, parent=None, duration=3000, toast_type="info", stack_index=0, node_name=None, operation_type=None):
        super().__init__(parent)

        # 保存堆叠索引
        self.stack_index = stack_index
        self.parent_window = parent
        
        # 保存标识符：用于关联特定节点和操作，便于后续替换
        self.node_name = node_name  # 关联的节点名称
        self.operation_type = operation_type  # 操作类型：如 'start', 'stop', 'delete'

        # 跟踪定时器
        self._tracking_timer = QTimer(self)
        self._tracking_timer.timeout.connect(self._update_position_if_needed)
        self._last_parent_geometry = QRect()

        # 选取背景色
        config = _toast_config
        color_map = {
            'info': config['info_color'],
            'success': config['success_color'],
            'warning': config['warning_color'],
            'error': config['error_color'],
        }
        bg_color = color_map.get(toast_type, config['info_color'])
        text_color = config['text_color']

        # ---------- 关键：窗口属性（与 dialog_utils / floating_panel 保持一致）----------
        # 仅设置 WA_TranslucentBackground，不设置 WA_StyledBackground
        # 不调用 setAutoFillBackground(True)，否则会与透明度冲突产生黑色底框
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 注：故意不设置 WA_StyledBackground 和 setAutoFillBackground

        # ---------- 外层布局（无边距，配合内层绘制背景） ----------
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---------- 内层：承载背景色、圆角、文字 ----------
        # 参考 dialog_utils.py 的模式：外层透明窗口 + 内层QWidget承载样式
        self._label = QLabel(message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "background-color: " + bg_color + ";"
            "color: " + text_color + ";"
            "padding: 12px 20px;"
            "border-radius: 8px;"
            "font-size: 14px;"
            "font-weight: bold;"
        )
        outer.addWidget(self._label)

        # 自适应文本大小
        self.adjustSize()

        # ---------- 动画参数 ----------
        self.duration = duration
        self._fade_duration = 300   # 淡入淡出时间（毫秒）
        self._opacity = 0.0         # 当前透明度
        self._is_fading_in = False
        self._is_fading_out = False

        # 高精度定时器（每16ms一帧 ≈ 60fps）
        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._anim_timer.timeout.connect(self._tick_animation)

        # 停留计时器：到达显示时长后触发淡出
        self._stay_timer = QTimer(self)
        self._stay_timer.setSingleShot(True)
        self._stay_timer.timeout.connect(self.start_fade_out)

        # 初始全透明，避免显示瞬间出现不透明快照
        self.setWindowOpacity(0.0)

    # ---------- 显示入口 ----------

    def show_toast(self):
        """显示通知并启动淡入动画"""
        self.adjustSize()
        
        # 先尝试初始定位
        self._position_correctly()
        
        # 设为全透明，然后显示
        self.setWindowOpacity(0.0)
        self._opacity = 0.0
        self.show()
        
        # 启用位置跟踪（跟随父窗口移动）
        self._start_tracking()
        
        # 延迟重新定位，等界面完全初始化
        QTimer.singleShot(150, self._delayed_positioning)

        # 保持在最上层
        self.raise_()

        # 启动淡入
        self._is_fading_in = True
        self._is_fading_out = False
        self._anim_timer.start(16)
    
    def _delayed_positioning(self):
        """延迟定位方法：等界面完全初始化后再计算位置"""
        self._position_correctly()

    # ---------- 动画 ----------

    def _tick_animation(self):
        """动画帧回调"""
        if self._is_fading_in:
            # 线性淡入：每帧 +16/_fade_duration
            self._opacity += 16.0 / self._fade_duration
            
            if self._opacity >= 1.0:
                self._opacity = 1.0
                self._is_fading_in = False
                self.setWindowOpacity(1.0)
                self._anim_timer.stop()

                # 淡入完成，开始计时停留
                if not self._stay_timer.isActive():
                    self._stay_timer.start(self.duration)
            else:
                self.setWindowOpacity(self._opacity)

        elif self._is_fading_out:
            # 线性淡出：每帧 -16/_fade_duration
            self._opacity -= 16.0 / self._fade_duration
            
            if self._opacity <= 0.0:
                self._opacity = 0.0
                self._is_fading_out = False
                self.setWindowOpacity(0.0)
                self._anim_timer.stop()

                # 停止停留计时并关闭
                if self._stay_timer.isActive():
                    self._stay_timer.stop()
                self.close()
            else:
                self.setWindowOpacity(self._opacity)

    def start_fade_out(self):
        """开始淡出动画"""
        if self._is_fading_out or self._is_fading_in:
            return
        self._is_fading_out = True
        self._anim_timer.start(16)

    # ---------- 位置跟踪 ----------

    def _start_tracking(self):
        """启动位置跟踪定时器"""
        if self.parent_window:
            # 记录初始父窗口几何信息
            self._last_parent_geometry = self.parent_window.geometry()
            # 每100ms检查一次父窗口变化
            self._tracking_timer.start(100)

    def _update_position_if_needed(self):
        """如果父窗口位置/大小变化，更新Toast位置"""
        if not self.parent_window:
            return
            
        current_geometry = self.parent_window.geometry()
        if current_geometry != self._last_parent_geometry:
            self._last_parent_geometry = current_geometry
            self._position_correctly()

    # ---------- 位置计算 ----------

    def _position_correctly(self):
        """计算Toast位置，严格限制在显示区域内"""
        if self.parent_window:
            self._position_relative_to_parent()
        else:
            self._position_relative_to_screen()

    def _position_relative_to_parent(self):
        """相对于主窗口定位 - Toast在主窗口右上角，但不遮挡画布dock的关闭按钮
        
        定位策略：
        1. Toast位于主窗口右上角（绑定在主窗口坐标系）
        2. 查找画布dock的关闭按钮位置
        3. 计算避让起始Y坐标：所有Toast都从关闭按钮下方开始堆叠
        """
        pw = self.parent_window
        
        # 获取主窗口在屏幕上的位置
        parent_top_left = pw.mapToGlobal(pw.rect().topLeft())
        parent_bottom_right = pw.mapToGlobal(pw.rect().bottomRight())
        
        # 🔧 第1步：先计算Toast在主窗口右上角的标准位置
        toast_x = parent_bottom_right.x() - self.width() - self._DISPLAY_AREA_MARGIN_RIGHT
        base_toast_y = parent_top_left.y() + self._DISPLAY_AREA_MARGIN_TOP
        
        # 🔧 第2步：查找画布dock的关闭按钮，计算避让的起始Y坐标
        avoid_y = base_toast_y
        
        # 查找画布dock（优先在CanvasHost中查找）
        canvas_dock = None
        canvas_host = None
        
        if hasattr(pw, '_canvas_host'):
            canvas_host = pw._canvas_host
        
        if canvas_host and hasattr(canvas_host, '_canvas_docks'):
            for dock in canvas_host._canvas_docks:
                if dock.isVisible():
                    canvas_dock = dock
                    break
        
        if not canvas_dock and HAS_BNOS_DOCK:
            for widget in pw.findChildren(BnosDock):
                if widget.isVisible():
                    canvas_dock = widget
                    break
        
        # 如果找到画布dock和关闭按钮，计算避让的起始Y
        if canvas_dock:
            close_btn = getattr(canvas_dock, '_close_btn', None)
            if close_btn:
                close_btn_global_bottom = close_btn.mapToGlobal(close_btn.rect().bottomRight())
                # 避让的起始Y = 关闭按钮下方 + 5px 间距
                avoid_y = close_btn_global_bottom.y() + 5
        
        # 🔧 第3步：选择较高的那个作为最终的起始Y
        # 如果标准起始Y比避让起始Y高，用避让起始Y
        final_base_y = max(base_toast_y, avoid_y)
        
        # 🔧 第4步：计算当前Toast的Y坐标（考虑堆叠索引）
        toast_y = final_base_y + (self.stack_index * self._TOAST_SPACING)
        
        # 🔧 第5步：边界检查（基于主窗口坐标系）
        max_safe_x = parent_bottom_right.x() - self.width() - 5
        max_safe_y = parent_bottom_right.y() - self.height() - 5
        min_safe_x = parent_top_left.x() + 5
        min_safe_y = parent_top_left.y() + 50  # 避开标题栏
        
        x = max(min(toast_x, max_safe_x), min_safe_x)
        y = max(min(toast_y, max_safe_y), min_safe_y)
        
        self.move(x, y)
    
    def _position_fallback_relative(self):
        """备用定位方法：在父窗口内部的右上角显示"""
        pw = self.parent_window
        
        # 获取父窗口的客户区（标题栏下方）在屏幕上的位置
        client_top_left = pw.mapToGlobal(pw.rect().topLeft())
        
        # 计算显示区域相对于父窗口的位置
        display_area_x_relative = pw.width() - self._DISPLAY_AREA_WIDTH - self._DISPLAY_AREA_MARGIN_RIGHT
        display_area_y_relative = self._DISPLAY_AREA_MARGIN_TOP
        
        # 转换为屏幕坐标
        area_x = client_top_left.x() + display_area_x_relative
        area_y = client_top_left.y() + display_area_y_relative
        area_width = self._DISPLAY_AREA_WIDTH
        area_height = self._DISPLAY_AREA_HEIGHT
        
        # 确保显示区域不超出父窗口
        max_area_x_relative = pw.width() - self.width() - self._DISPLAY_AREA_MARGIN_RIGHT
        display_area_x_relative = min(display_area_x_relative, max_area_x_relative)
        display_area_x_relative = max(display_area_x_relative, self._DISPLAY_AREA_MARGIN_RIGHT)
        area_x = client_top_left.x() + display_area_x_relative
        
        max_area_bottom_relative = pw.height() - self._DISPLAY_AREA_MARGIN_TOP
        area_height = min(area_height, max_area_bottom_relative - display_area_y_relative)
        
        # Toast宽度不超过显示区域宽度
        toast_width = min(self.width(), area_width - 20)
        if self.width() > toast_width:
            self._label.setWordWrap(True)
            self.adjustSize()
        
        # 计算Toast位置
        x = area_x + (area_width - self.width()) // 2
        y = area_y + (self.stack_index * self._TOAST_SPACING)
        
        # 边界检查
        max_y = area_y + area_height - self.height()
        if y > max_y:
            y = max_y
        
        parent_bottom_right = pw.mapToGlobal(pw.rect().bottomRight())
        max_safe_x = parent_bottom_right.x() - self.width() - 5
        max_safe_y = parent_bottom_right.y() - self.height() - 5
        min_safe_x = client_top_left.x() + 5
        min_safe_y = client_top_left.y() + 5
        
        x = max(min(x, max_safe_x), min_safe_x)
        y = max(min(y, max_safe_y), min_safe_y)
        
        self.move(x, y)

    def _position_relative_to_screen(self):
        """相对于屏幕定位（没有父窗口时）"""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        
        # 计算显示区域
        area_x = screen.width() - self._DISPLAY_AREA_WIDTH - self._DISPLAY_AREA_MARGIN_RIGHT
        area_y = self._DISPLAY_AREA_MARGIN_TOP
        
        # Toast位置
        x = area_x + (self._DISPLAY_AREA_WIDTH - self.width()) // 2
        y = area_y + (self.stack_index * self._TOAST_SPACING)
        
        # 边界检查
        max_y = area_y + self._DISPLAY_AREA_HEIGHT - self.height()
        if y > max_y:
            y = max_y
        
        self.move(x, y)

    def update_position(self):
        """对外提供的位置刷新方法（堆叠变化时调用）"""
        self._position_correctly()

    # ---------- 生命周期 ----------

    def closeEvent(self, event):
        """关闭事件：停止所有定时器，避免泄漏"""
        # 停止动画定时器
        self._anim_timer.stop()
        if self._stay_timer.isActive():
            self._stay_timer.stop()
        # 停止跟踪定时器
        if self._tracking_timer.isActive():
            self._tracking_timer.stop()
        # 发射关闭信号
        self.closed.emit()
        event.accept()
