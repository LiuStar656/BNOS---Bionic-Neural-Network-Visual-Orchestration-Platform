# CanvasHost 多余空间修复

## 一、问题概述

**问题描述**：CanvasHost 中出现未知的多余空间，占据了画布区域下方的一部分显示空间，影响用户体验。

**原因定位**：在 `_remove_blank_placeholder()` 方法中创建的 `central_placeholder` 控件没有正确隐藏，导致它占用了可见空间。

## 二、根因分析

在 `CanvasHost._remove_blank_placeholder()` 方法中，为了让 Qt 的 Dock 系统正确工作，需要设置一个中央控件作为占位符。但原实现中没有正确设置该控件的属性，导致它占用了可见空间：

```python
# 原实现
central_placeholder = QWidget(self)
central_placeholder.setStyleSheet("background: transparent;")
central_placeholder.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)  # ❌ 没有真正隐藏
```

虽然设置了透明背景，但控件本身仍会占用布局空间，导致出现多余的空白区域。

## 三、修复方案

对 `central_placeholder` 控件添加以下属性设置，确保它完全不占用可见空间：

```python
central_placeholder = QWidget(self)
central_placeholder.setStyleSheet("background: transparent;")
central_placeholder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)  # 透明背景
central_placeholder.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)    # 不绘制不透明区域
central_placeholder.setFixedSize(0, 0)                                            # 固定大小为0
central_placeholder.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)  # 忽略布局策略
```

## 四、影响范围

| 文件 | 变更点 |
| --- | --- |
| `ui/core/canvas_host.py` | 优化 `central_placeholder` 控件属性设置；新增 `QSizePolicy` 导入 |

## 五、验证

- **语法检查**：`python _check_syntax.py` 通过
- **功能验证步骤**：
  1. 启动 BNOS，打开一个项目
  2. 检查画布区域下方是否还有多余的空白空间
  3. 验证画布能够正常占据整个可用区域
  4. 切换项目或创建新项目 → 验证空间问题不再出现
