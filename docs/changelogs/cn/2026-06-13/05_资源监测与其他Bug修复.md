# 资源监测与其他 Bug 修复

## 1. 资源监测网络下载首次满载

### 问题

每次打开软件，网络下载会显示满载（100MB/s），持续数秒后才恢复正常。

### 根因

```python
# collector 初始化时
self._last_net_sent = 0      # ← 初始值为 0
self._last_net_recv = 0

# 首次查询
current = psutil.net_io_counters()  # 返回系统启动以来的累计总量
diff_sent = current.bytes_sent - 0   # = 全部累计流量
usage = diff_sent / 100MB * 100      # >> 100%，显示 100%
```

`_last_net_*` 初始值为 0，首次 diff = 系统启动以来的累计总量，对上 100MB/s 上限必然 100%。

### 修复

```python
# 在 SystemResourceCollector 初始化时预热
initial = psutil.net_io_counters()
self._last_net_sent = initial.bytes_sent
self._last_net_recv = initial.bytes_recv
self._last_net_time = time.time()
```

预热一次 `net_io_counters()` 存入 `_last_net_*`，首次查询 diff 为零。

---

## 2. 节点样式切换尺寸不更新

### 问题

节点从面板模式（DetailedNodeStyle）切换到框图模式（RectNodeStyle）后，尺寸仍为面板模式的大尺寸。

### 根因

`DeviceCoordinateCache` 在 `setRect` 改变尺寸时不自动失效缓存。

之前的流程：
```
_destroy_detailed()
  → setCacheMode(DeviceCoordinateCache)  # 先启用缓存
  → setRect(0, 0, 140, 80)               # 再改 rect → 缓存不刷新！
```

旧的大尺寸画面被缓存锁定，后续 `set_style()` 的 `setRect` 虽然改了内部 rect 值，但渲染的仍是缓存中的旧画面。

### 修复

三处改动：

**1. `_destroy_detailed()` — 先 NoCache 再 setRect**
```python
self.setCacheMode(self.CacheMode.NoCache)     # 先禁用缓存
self.setRect(0, 0, w, h)                      # 再改尺寸
```

**2. `set_style()` — 显式管理缓存状态**
```python
self.setCacheMode(self.CacheMode.NoCache)     # apply 前确保无缓存
self.prepareGeometryChange()
self.setRect(0, 0, w, h)
self._style.apply(self)
# apply 完成后，非 detailed 模式重新启用缓存
if sk != "detailed":
    self.setCacheMode(self.CacheMode.DeviceCoordinateCache)
```

**3. `_ensure_rect()` + `QTimer.singleShot(0, ...)` — 事件循环后兜底**
```python
QTimer.singleShot(0, lambda: self._ensure_rect(target_w, target_h))

def _ensure_rect(self, w, h):
    """事件循环后强制校正节点尺寸"""
    current_rect = self.rect()
    if abs(current_rect.width() - w) > 0.5 or abs(current_rect.height() - h) > 0.5:
        self.prepareGeometryChange()
        self.setCacheMode(self.CacheMode.NoCache)
        self.setRect(0, 0, w, h)
        self.setCacheMode(self.CacheMode.DeviceCoordinateCache)
        self.update()
```

---

## 3. 历史记录面板菜单入口补充

`view.history_panel` Action 已注册但未加入任何菜单。在 **工具菜单** 中添加「历史记录」入口：

```python
# menu_manager.py
ActionFactory.create_action(main_window, "view.history_panel", menu=tools_menu)
```

---

## 关键改动文件

| 文件 | 改动 |
|------|------|
| `ui/panels/_shared/system_resource_collector.py` | 预热 `net_io_counters()` 存入 `_last_net_*` |
| `ui/canvas/items/node_item.py` | `_destroy_detailed` NoCache 先、`set_style` 缓存管理、`_ensure_rect` 兜底 |
| `ui/menu/menu_manager.py` | 工具菜单新增「历史记录」入口 |

---

## 验证结果

- ✅ 资源监测网络下载首次显示正确（不再满载）
- ✅ 面板模式→框图模式尺寸正确切换（140x80）
- ✅ 历史记录面板可通过菜单正常打开
