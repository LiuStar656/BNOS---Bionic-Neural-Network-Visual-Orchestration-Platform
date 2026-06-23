# 画布 Dock 双击边缘自动嵌入功能

## 一、功能概述

新增画布 Dock 双击边缘自动嵌入功能，当用户双击漂浮状态下的画布 Dock 边缘区域时，Dock 会自动嵌入到 CanvasHost 容器中，并隐藏标题栏，提供更简洁的画布视图。

## 二、功能特性

| 特性 | 说明 |
| --- | --- |
| 触发方式 | 双击漂浮状态下的 Dock 边缘区域（4 像素范围内） |
| 自动嵌入 | 双击后自动取消漂浮状态，嵌入到 CanvasHost 容器 |
| 标题栏隐藏 | 嵌入后自动隐藏标题栏，提供更简洁的画布视图 |
| 默认行为屏蔽 | 屏蔽双击标题栏的默认行为（如最大化/还原） |
| 显式恢复 | 提供 `show_title_bar()` 方法显式恢复标题栏 |

## 三、实现方案

### 1. 双击事件处理

在 `BnosDock.mouseDoubleClickEvent` 中检测双击位置是否在边缘区域：

```python
def mouseDoubleClickEvent(self, event):
    """双击事件：屏蔽双击标题栏功能，仅允许边缘区域触发自动嵌入"""
    if self._is_floating:
        pos = event.pos()
        border = 4
        w, h = self.width(), self.height()
        
        is_on_edge = (pos.x() < border or pos.x() > w - border or
                     pos.y() < border or pos.y() > h - border)
        
        if is_on_edge:
            self._auto_embed_and_hide_title()
            event.accept()
            return
    
    event.ignore()  # 屏蔽默认的双击标题栏行为
```

### 2. 自动嵌入与标题栏隐藏

```python
def _auto_embed_and_hide_title(self):
    """自动嵌入到父容器并隐藏标题栏"""
    if not self.parent() or not hasattr(self.parent(), 'addDockWidget'):
        return
    
    # 取消漂浮状态（嵌入到父容器）
    self.setFloating(False)
    
    # 隐藏标题栏
    self.hide_title_bar()
```

### 3. 标题栏管理方法

```python
def hide_title_bar(self):
    """隐藏标题栏"""
    if self._title_bar_hidden:
        return
    
    self._title_bar_hidden = True
    self.setTitleBarWidget(None)
    self.title_bar_hidden.emit(True)
    self._central_widget.setStyleSheet("background-color: #252526; margin: 0px;")

def show_title_bar(self):
    """显示标题栏"""
    if not self._title_bar_hidden:
        return
    
    self._title_bar_hidden = False
    self.setTitleBarWidget(self._title_widget)
    self.title_bar_hidden.emit(False)
```

### 4. 新增信号

```python
title_bar_hidden = Signal(bool)  # 标题栏隐藏状态变化信号
```

## 四、影响范围

| 文件 | 变更点 |
| --- | --- |
| `ui/core/bnos_dock.py` | 新增 `mouseDoubleClickEvent`、`_auto_embed_and_hide_title`、`hide_title_bar`、`show_title_bar`、`is_title_bar_hidden` 方法；新增 `title_bar_hidden` 信号 |

## 五、交互流程

1. 用户将画布 Dock 拖出成为浮动窗口
2. 用户双击浮动窗口的边缘区域（4 像素范围）
3. Dock 自动嵌入到 CanvasHost 容器中
4. 标题栏自动隐藏，画布占据完整可用空间
5. 通过 `show_title_bar()` 方法可显式恢复标题栏

## 六、验证

- **语法检查**：`python _check_syntax.py` 通过
- **功能验证步骤**：
  1. 启动 BNOS，打开一个项目
  2. 将画布 Dock 拖出成为浮动窗口
  3. 双击浮动窗口的边缘区域 → 验证自动嵌入并隐藏标题栏
  4. 双击窗口内部区域 → 验证不会触发嵌入
  5. 验证标题栏保持隐藏状态直到显式恢复
