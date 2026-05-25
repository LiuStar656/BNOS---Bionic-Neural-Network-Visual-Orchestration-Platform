"""
BNOS Toast 通知系统 - 右上角自动消失的通知弹窗

提供流畅的60fps淡入淡出动画，支持堆叠显示和自动位置调整
显示在窗口右上角，不干扰画布操作
"""
from PyQt6.QtWidgets import QLabel, QApplication, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette

# Toast全局配置（使用rgba格式以支持透明度）
_toast_config = {
    'info_color': 'rgba(50, 50, 50, 230)',
    'success_color': 'rgba(76, 175, 80, 230)',
    'warning_color': 'rgba(255, 152, 0, 230)',
    'error_color': 'rgba(244, 67, 54, 230)',
    'text_color': '#ffffff',
    'opacity': 0.9
}


def set_toast_config(config):
    """设置Toast全局配置"""
    global _toast_config
    _toast_config.update(config)


def get_toast_config():
    """获取Toast全局配置"""
    return _toast_config.copy()


class ToastNotification(QLabel):
    """右上角自动消失的通知弹窗（Toast）- 优化版
    
    使用高精度定时器实现流畅的60fps淡入淡出动画
    支持堆叠显示和自动位置调整
    显示在窗口右上角，不干扰画布操作
    """
    
    def __init__(self, message, parent=None, duration=3000, toast_type="info", stack_index=0):
        super().__init__(message, parent)
        
        # 保存堆叠索引
        self.stack_index = stack_index
        
        # 获取配置
        config = _toast_config
        
        # 根据类型选择背景色
        color_map = {
            'info': config['info_color'],
            'success': config['success_color'],
            'warning': config['warning_color'],
            'error': config['error_color']
        }
        bg_color = color_map.get(toast_type, config['info_color'])
        
        # 使用QPalette设置背景色（更可靠的方式）
        palette = self.palette()
        
        # 支持多种颜色格式：rgba 和 十六进制
        if bg_color.startswith('rgba('):
            # rgba格式
            color_parts = bg_color.replace('rgba(', '').replace(')', '').split(',')
            r, g, b, a = map(int, color_parts)
        elif bg_color.startswith('#'):
            # 十六进制格式
            qcolor = QColor(bg_color)
            r, g, b, a = qcolor.red(), qcolor.green(), qcolor.blue(), 255
        else:
            # 默认颜色
            r, g, b, a = 50, 50, 50, 230
        
        # 在PyQt6中，使用Window代替Background
        palette.setColor(QPalette.ColorRole.Window, QColor(r, g, b, a))
        self.setPalette(palette)
        
        # 设置基础样式
        self.setStyleSheet(f"""
            QLabel {{
                color: {config['text_color']};
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        
        # 设置窗口属性：无边框、不接受焦点、始终在最上层
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.WindowStaysOnTopHint)
        # 添加WA_TranslucentBackground以支持rgba透明度
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 确保背景被绘制
        self.setAutoFillBackground(True)
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
        
        # 计算位置：主窗口内右上角
        if self.parent():
            # 获取主窗口的几何信息
            parent_geo = self.parent().geometry()
            
            # 计算窗口内右上角位置，向内偏移1px
            x = parent_geo.width() - self.width() - 10
            y = 100 + (self.stack_index * 65)  # 向下偏移100px避开标题栏
            
            # 边界检测：确保Toast不会超出窗口底部
            max_y = parent_geo.height() - self.height() - 20
            if y > max_y:
                y = max_y  # 限制在窗口内
            
            # 使用相对位置（相对于父窗口）
            self.move(x, y)
        else:
            # 如果没有父窗口，使用屏幕右上角
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 50 + (self.stack_index * 65)
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
        
        # 计算位置：主窗口内右上角
        if self.parent():
            # 获取主窗口的几何信息
            parent_geo = self.parent().geometry()
            
            # 计算窗口内右上角位置，向内偏移20px
            x = parent_geo.width() - self.width() - 20
            y = 50 + (self.stack_index * 65)  # 向下偏移50px避开标题栏
            
            # 边界检测：确保Toast不会超出窗口底部
            max_y = parent_geo.height() - self.height() - 20
            if y > max_y:
                y = max_y  # 限制在窗口内
            
            # 使用相对位置（相对于父窗口）
            self.move(x, y)
        else:
            # 如果没有父窗口，使用屏幕右上角
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 50 + (self.stack_index * 65)
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