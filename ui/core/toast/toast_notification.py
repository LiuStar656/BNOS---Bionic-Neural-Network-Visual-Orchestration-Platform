"""
BNOS Toast 通知系统 - 右上角自动消失的通知弹窗

提供流畅的60fps淡入淡出动画，支持堆叠显示和自动位置调整
显示在窗口右上角，不干扰画布操作
"""
from PyQt6.QtWidgets import QLabel, QApplication, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer


class ToastNotification(QLabel):
    """右上角自动消失的通知弹窗（Toast）- 优化版
    
    使用高精度定时器实现流畅的60fps淡入淡出动画
    支持堆叠显示和自动位置调整
    显示在右上角，不干扰画布操作
    """
    
    def __init__(self, message, parent=None, duration=3000, toast_type="info", stack_index=0):
        super().__init__(message, parent)
        
        # 保存堆叠索引
        self.stack_index = stack_index
        
        # 设置基础样式
        base_style = """
            QLabel {
                background-color: rgba(50, 50, 50, 230);
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
        """
        
        # 根据类型调整颜色
        if toast_type == "success":
            base_style = base_style.replace("rgba(50, 50, 50, 230)", "rgba(76, 175, 80, 230)")
        elif toast_type == "warning":
            base_style = base_style.replace("rgba(50, 50, 50, 230)", "rgba(255, 152, 0, 230)")
        elif toast_type == "error":
            base_style = base_style.replace("rgba(50, 50, 50, 230)", "rgba(244, 67, 54, 230)")
        
        self.setStyleSheet(base_style)
        
        # 设置窗口属性（移除 WindowStaysOnTopHint 避免覆盖其他软件窗口）
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 调整大小以适应文本
        self.adjustSize()
        
        # 初始化透明度效果
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self.opacity_effect)
        
        # 动画参数
        self.duration = duration
        self.fade_duration = 300  # 淡入淡出时间（毫秒）
        self.current_opacity = 0.0
        self.is_fading_in = False
        self.is_fading_out = False
        
        # 使用高精度定时器实现平滑动画（60fps）
        self.animation_timer = QTimer(self)
        self.animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation_timer.timeout.connect(self.update_animation)
        
        # 停留计时器
        self.stay_timer = QTimer(self)
        self.stay_timer.setSingleShot(True)
        self.stay_timer.timeout.connect(self.start_fade_out)
    
    def show_toast(self):
        """显示通知并启动淡入动画"""
        # 先确保大小已调整
        self.adjustSize()
        
        # 计算位置：使用绝对屏幕坐标，固定在主窗口右上角
        if self.parent():
            # 获取主窗口在屏幕上的位置
            parent_window = self.parent()
            window_pos = parent_window.pos()
            window_size = parent_window.size()
            
            # 计算相对于窗口的右上角位置（使用绝对屏幕坐标）
            x = window_pos.x() + window_size.width() - self.width() - 20
            y = window_pos.y() + 40 + (self.stack_index * 60)
            
            # 边界检测：确保Toast不会超出屏幕底部
            screen = QApplication.primaryScreen().geometry()
            max_y = screen.bottom() - self.height() - 10
            if y > max_y:
                y = max_y  # 限制在屏幕内
        else:
            # 如果没有父窗口，使用屏幕右上角
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 40 + (self.stack_index * 60)
        
        self.move(x, y)
        self.show()
        
        # 启动淡入动画
        self.current_opacity = 0.0
        self.is_fading_in = True
        self.is_fading_out = False
        self.animation_timer.start(16)  # 16ms ≈ 60fps
    
    def update_animation(self):
        """更新动画帧 - 手动控制透明度实现流畅动画"""
        if self.is_fading_in:
            # 淡入动画：线性增加透明度
            self.current_opacity += 16.0 / self.fade_duration
            if self.current_opacity >= 1.0:
                self.current_opacity = 1.0
                self.is_fading_in = False
                self.opacity_effect.setOpacity(1.0)
                self.animation_timer.stop()
                
                # 开始停留计时（确保只启动一次）
                if not self.stay_timer.isActive():
                    self.stay_timer.start(self.duration)
            else:
                self.opacity_effect.setOpacity(self.current_opacity)
        
        elif self.is_fading_out:
            # 淡出动画：线性减少透明度
            self.current_opacity -= 16.0 / self.fade_duration
            if self.current_opacity <= 0.0:
                self.current_opacity = 0.0
                self.opacity_effect.setOpacity(0.0)
                self.animation_timer.stop()
                
                # 确保所有定时器都停止
                if self.stay_timer.isActive():
                    self.stay_timer.stop()
                
                # 延迟关闭，确保视觉效果完成
                QTimer.singleShot(50, self.close)
            else:
                self.opacity_effect.setOpacity(self.current_opacity)
    
    def update_position(self):
        """更新位置（用于堆叠时的位置调整）"""
        # 重新调整大小以确保准确性
        self.adjustSize()
        
        # 计算位置：使用绝对屏幕坐标，固定在主窗口右上角
        if self.parent():
            # 获取主窗口在屏幕上的位置
            parent_window = self.parent()
            window_pos = parent_window.pos()
            window_size = parent_window.size()
            
            # 计算相对于窗口的右上角位置（使用绝对屏幕坐标）
            x = window_pos.x() + window_size.width() - self.width() - 20
            y = window_pos.y() + 40 + (self.stack_index * 60)
            
            # 边界检测：确保Toast不会超出屏幕底部
            screen = QApplication.primaryScreen().geometry()
            max_y = screen.bottom() - self.height() - 10
            if y > max_y:
                y = max_y  # 限制在屏幕内
        else:
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 40 + (self.stack_index * 60)
        
        self.move(x, y)
    
    def start_fade_out(self):
        """开始淡出动画"""
        # 防止重复启动淡出
        if self.is_fading_out or self.is_fading_in:
            return
        
        self.is_fading_out = True
        self.animation_timer.start(16)  # 16ms ≈ 60fps

    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        # 停止所有定时器
        self.animation_timer.stop()
        if self.stay_timer.isActive():
            self.stay_timer.stop()
        
        # 接受关闭事件
        event.accept()
