# 🔧 异步删除节点，不阻塞 GUI

## 🔧 异步删除节点，不阻塞 GUI (2026-06-05)

### 问题描述

**删除节点时 GUI 无响应**
- **问题**：删除节点时，由于删除操作是同步阻塞的，导致整个 GUI 无响应，用户无法进行其他操作
- **影响**：批量删除多个节点时，GUI 长时间无响应，用户体验很差

### 修复方案

**异步删除机制**

1. **单个删除异步化**
   - 使用 `QTimer.singleShot` 将删除操作放到事件队列中
   - GUI 可以继续响应用户操作
   - 删除完成后通过回调更新 UI

2. **批量删除逐个执行**
   - 一次确认后逐个异步删除
   - 每个节点删除间隔 100ms
   - 删除完成后显示汇总结果

### 技术实现

```python
def delete_node(self, node_name):
    """删除节点（异步执行，不阻塞 GUI）"""
    # 显示确认对话框
    reply = themed_message(...)
    if not reply:
        return
    
    # 使用 QTimer 异步执行删除
    QTimer.singleShot(10, lambda: self._delete_node_async(node_name, 
        lambda ok, err: self._on_delete_node_complete(node_name, ok, err)))

def batch_delete_nodes(self):
    """批量删除（异步逐个删除）"""
    # 一次确认
    reply = themed_message(...)
    if not reply:
        return
    
    # 异步逐个删除
    def delete_next(index):
        if index >= len(selected_nodes):
            # 显示汇总结果
            return
        self._delete_node_async(node_name, lambda ok, err: delete_next(index + 1))
    
    delete_next(0)
```

### 修改的文件

- `ui/panels/node_list_panel.py` - 添加异步删除方法
- `ui/panels/node_list_dock.py` - 添加异步删除方法

### 验收标准

✅ 删除节点时 GUI 可以正常响应操作
✅ 批量删除只需要一次确认
✅ 删除完成后正确显示结果
✅ 挂载节点在批量删除时会被跳过

---