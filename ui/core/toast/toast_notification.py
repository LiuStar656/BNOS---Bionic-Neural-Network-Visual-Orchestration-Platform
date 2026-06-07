"""
BNOS Toast 通知系统 - 右上角自动消失的通知弹窗

采用"外层透明窗口 + 内层QFrame承载样式"的双层架构，参考 dialog_utils.py 和
floating_panel.py 的成熟实现模式。使用 setWindowOpacity 做淡入淡出动画，
避免 QGraphicsOpacityEffect 与 WA_TranslucentBackground 的兼容性问题。
"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication


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
    """
    
    # 信号：Toast关闭时发出
    closed = pyqtSignal()

    def __init__(self, message, parent=None, duration=3000, toast_type="info", stack_index=0, node_name=None, operation_type=None):
        super().__init__(parent)

        # 保存堆叠索引
        self.stack_index = stack_index
        self.parent_window = parent
        
        # 保存标识符：用于关联特定节点和操作，便于后续替换
        self.node_name = node_name  # 关联的节点名称
        self.operation_type = operation_type  # 操作类型：如 'start', 'stop', 'delete'

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
        self._position_correctly()

        # 关键时序：先设为全透明，再show，再启动淡入动画
        # 这样避免任何"先显示后透明"的闪烁
        self.setWindowOpacity(0.0)
        self._opacity = 0.0
        self.show()

        # 保持在最上层
        self.raise_()

        # 启动淡入
        self._is_fading_in = True
        self._is_fading_out = False
        self._anim_timer.start(16)

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

    # ---------- 位置计算 ----------

    def _position_correctly(self):
        """根据父窗口或屏幕计算正确位置"""
        if self.parent_window:
            # 基于父窗口的内部坐标（向内偏移20px，向下偏移50px避开标题栏）
            pw = self.parent_window
            x = pw.width() - self.width() - 20
            y = 50 + (self.stack_index * 65)

            max_y = pw.height() - self.height() - 20
            if y > max_y:
                y = max_y

            self.move(x, y)
        else:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 50 + (self.stack_index * 65)
            self.move(x, y)

    def update_position(self):
        """对外提供的位置刷新方法（堆叠变化时调用）"""
        self._position_correctly()

    # ---------- 生命周期 ----------

    def closeEvent(self, event):
        """关闭事件：停止所有定时器，避免泄漏"""
        self._anim_timer.stop()
        if self._stay_timer.isActive():
            self._stay_timer.stop()
        # 发射关闭信号
        self.closed.emit()
        event.accept()
