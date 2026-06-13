# Resource Monitor and Other Bug Fixes

## 1. Resource Monitor Network Download 100% on Startup

### Problem

Every time the software was opened, network download showed 100% (100MB/s) for several seconds before returning to normal.

### Root Cause

```python
# On collector initialization
self._last_net_sent = 0      # ← Initial value is 0
self._last_net_recv = 0

# First query
current = psutil.net_io_counters()  # Returns cumulative total since system boot
diff_sent = current.bytes_sent - 0   # = All cumulative traffic
usage = diff_sent / 100MB * 100      # >> 100%, shown as 100%
```

`_last_net_*` initialized to 0, first diff = cumulative total since system boot. Against the 100MB/s cap, it's guaranteed to hit 100%.

### Fix

```python
# Pre-warm on SystemResourceCollector initialization
initial = psutil.net_io_counters()
self._last_net_sent = initial.bytes_sent
self._last_net_recv = initial.bytes_recv
self._last_net_time = time.time()
```

Pre-warm one `net_io_counters()` call into `_last_net_*`, first query diff is zero.

---

## 2. Node Style Switch Size Not Updating

### Problem

After switching a node from panel mode (DetailedNodeStyle) to block diagram mode (RectNodeStyle), the size remained at the panel mode's large dimensions.

### Root Cause

`DeviceCoordinateCache` does not auto-invalidate when `setRect` changes the size.

Previous flow:
```
_destroy_detailed()
  → setCacheMode(DeviceCoordinateCache)  # Enables cache first
  → setRect(0, 0, 140, 80)               # Then changes rect → cache not invalidated!
```

The old large-sized paint is locked in cache. Subsequent `set_style()` `setRect` calls change the internal rect value, but rendering still uses the cached old visual.

### Fix

Three changes:

**1. `_destroy_detailed()` — NoCache first, then setRect**
```python
self.setCacheMode(self.CacheMode.NoCache)     # Disable cache first
self.setRect(0, 0, w, h)                      # Then change size
```

**2. `set_style()` — Explicit cache state management**
```python
self.setCacheMode(self.CacheMode.NoCache)     # Ensure no cache before apply
self.prepareGeometryChange()
self.setRect(0, 0, w, h)
self._style.apply(self)
# After apply, re-enable cache for non-detailed mode
if sk != "detailed":
    self.setCacheMode(self.CacheMode.DeviceCoordinateCache)
```

**3. `_ensure_rect()` + `QTimer.singleShot(0, ...)` — Post-event-loop safety net**
```python
QTimer.singleShot(0, lambda: self._ensure_rect(target_w, target_h))

def _ensure_rect(self, w, h):
    """Force-correct node size after event loop"""
    current_rect = self.rect()
    if abs(current_rect.width() - w) > 0.5 or abs(current_rect.height() - h) > 0.5:
        self.prepareGeometryChange()
        self.setCacheMode(self.CacheMode.NoCache)
        self.setRect(0, 0, w, h)
        self.setCacheMode(self.CacheMode.DeviceCoordinateCache)
        self.update()
```

---

## 3. History Panel Menu Entry Addition

`view.history_panel` Action was registered but missing from menus. Added「History」entry to **Tools menu**:

```python
# menu_manager.py
ActionFactory.create_action(main_window, "view.history_panel", menu=tools_menu)
```

---

## Key Files Changed

| File | Change |
|------|--------|
| `ui/panels/_shared/system_resource_collector.py` | Pre-warm `net_io_counters()` into `_last_net_*` |
| `ui/canvas/items/node_item.py` | `_destroy_detailed` NoCache first, `set_style` cache management, `_ensure_rect` safety net |
| `ui/menu/menu_manager.py` | Tools menu added「History」entry |

---

## Verification Results

- ✅ Resource monitor network download displays correctly on first load (no more 100%)
- ✅ Panel mode → Block diagram mode size switches correctly (140x80)
- ✅ History panel opens normally via menu
