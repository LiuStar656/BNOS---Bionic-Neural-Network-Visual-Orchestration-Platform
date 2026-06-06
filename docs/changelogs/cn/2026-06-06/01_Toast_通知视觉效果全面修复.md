# 🎨 Toast 通知视觉效果全面修复

## 🎨 Toast 通知视觉效果全面修复 (2026-06-06)

### 问题描述

**Toast 通知存在严重视觉缺陷**
- **问题 1：黑色底框闪烁** — 显示通知时先弹出黑色底框，随后才显示正确样式
- **问题 2：消失动画突兀** — 通知消失时瞬间消失，而非平滑渐隐
- **影响**：用户体验差，视觉反馈不流畅，与 BNOS 深色主题不协调

### 问题根因分析

1. **属性冲突** — 原实现同时设置了三个互相冲突的窗口属性：
   - `WA_StyledBackground`：让 Qt 用 QStyle 绘制纯色背景
   - `setAutoFillBackground(True)`：用 QPalette 默认色填充背景（通常为黑色）
   - `WA_TranslucentBackground`：要求窗口透明
   - 三者共存导致窗口显示瞬间以黑色绘制，再被 rgba 颜色覆盖，产生闪烁

2. **动画实现错误** — 使用 `QGraphicsOpacityEffect` 在 Tool 类型的独立窗口上做透明度动画，与 `WA_TranslucentBackground` 存在兼容性问题，导致淡出阶段卡顿或直接消失

### 修复方案

**采用"外层透明窗口 + 内层承载样式"的双层架构（参考 dialog_utils.py / floating_panel.py 的成熟模式）**

1. **继承类调整**：`QLabel` → `QWidget`（作为外层透明窗口容器）
2. **窗口属性精简**：仅设置 `WA_TranslucentBackground`，**不设置** `WA_StyledBackground` 和 `setAutoFillBackground(True)`
3. **样式承载**：在内层 `QLabel` 上通过 stylesheet 设置 `rgba` 背景色 + `border-radius` 圆角 + 文字，真正实现半透明圆角效果
4. **动画重构**：用 `QTimer` 驱动 `setWindowOpacity()` 做线性淡入淡出（每16ms一帧 ≈ 60fps），替代不稳定的 `QGraphicsOpacityEffect`
5. **显示时序优化**：先将窗口 opacity 设为 0.0，再 show，再启动淡入动画，彻底避免任何"先显示后透明"的闪烁

### 技术实现要点

```python
class ToastNotification(QWidget):

    def __init__(self, message, parent=None, duration=3000, toast_type="info", stack_index=0):
        super().__init__(parent)

        # 仅设 WA_TranslucentBackground，不设 WA_StyledBackground / setAutoFillBackground
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 外层：无边距布局（透明窗口自身不绘制任何内容）
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 内层：QLabel 承载 rgba 背景 + border-radius 圆角 + 文字（关键技巧）
        self._label = QLabel(message)
        self._label.setStyleSheet(
            "background-color: rgba(76, 175, 80, 230);"
            "color: #ffffff;"
            "padding: 12px 20px;"
            "border-radius: 8px;"
            "font-size: 14px;"
            "font-weight: bold;"
        )
        outer.addWidget(self._label)

        # 动画：QTimer 驱动 setWindowOpacity()（比 QGraphicsOpacityEffect 更稳定）
        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._anim_timer.timeout.connect(self._tick_animation)

        # 初始全透明，避免显示瞬间出现不透明快照
        self.setWindowOpacity(0.0)

    def show_toast(self):
        """关键时序：opacity=0 → show → 启动淡入动画"""
        self.setWindowOpacity(0.0)
        self._opacity = 0.0
        self.show()
        self._is_fading_in = True
        self._anim_timer.start(16)
```

### 代码优化补充

**动画帧处理可读性优化**
- 在 `if self._opacity >= 1.0:` 和 `if self._opacity <= 0.0:` 前添加空行，增强代码可读性
- 保持代码缩进一致，避免潜在的缩进错误
- 确保代码结构清晰，便于未来维护

### 修改的文件

- `ui/core/toast/toast_notification.py` — 完全重写，采用双层架构 + setWindowOpacity 动画，优化代码格式

### 验收标准

✅ Toast 显示瞬间无黑色底框，直接以半透明圆角样式出现
✅ Toast 消失时平滑渐隐，视觉过渡自然（约 300ms）
✅ 与 dialog_utils.py / floating_panel.py 等已工作的半透明组件行为一致
✅ 支持多种类型（info/success/warning/error）的不同颜色
✅ 支持堆叠显示和自动位置调整（接口不变，向下兼容）
✅ 代码格式规范，可读性强，便于维护
✅ 无新问题引入

---