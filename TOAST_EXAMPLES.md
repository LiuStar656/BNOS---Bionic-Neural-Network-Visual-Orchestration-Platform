# BNOS Toast通知使用示例

## 在实际代码中使用Toast

### 示例1：节点操作反馈

```python
class BNOSMainWindow(QMainWindow):
    def start_node(self, node_name):
        """启动节点"""
        try:
            # 启动节点的逻辑...
            self.nodes_data[node_name]['process'].start()
            
            # 显示成功提示
            self.show_toast(f"节点 '{node_name}' 已启动", "success")
            
        except Exception as e:
            # 显示错误提示
            self.show_toast(f"启动失败: {str(e)}", "error", 5000)
    
    def stop_node(self, node_name):
        """停止节点"""
        try:
            # 停止节点的逻辑...
            self.nodes_data[node_name]['process'].terminate()
            
            # 显示成功提示
            self.show_toast(f"节点 '{node_name}' 已停止", "info")
            
        except Exception as e:
            self.show_toast(f"停止失败: {str(e)}", "error")
```

### 示例2：项目操作反馈

```python
def open_project(self):
    """打开项目"""
    project_path = QFileDialog.getExistingDirectory(self, "选择项目文件夹")
    
    if not project_path:
        return  # 用户取消
    
    try:
        # 加载项目的逻辑...
        self.load_project(project_path)
        
        # 显示成功提示（较长时长）
        self.show_toast(f"项目已打开: {os.path.basename(project_path)}", "success", 4000)
        
    except Exception as e:
        self.show_toast(f"打开项目失败: {str(e)}", "error", 5000)

def create_node(self, node_name):
    """创建新节点"""
    try:
        # 创建节点的逻辑...
        self.create_new_node(node_name)
        
        # 显示成功提示
        self.show_toast(f"节点 '{node_name}' 创建成功", "success")
        
    except FileExistsError:
        self.show_toast(f"节点 '{node_name}' 已存在", "warning")
    except Exception as e:
        self.show_toast(f"创建失败: {str(e)}", "error")
```

### 示例3：配置保存反馈

```python
def save_config(self, node_name):
    """保存节点配置"""
    try:
        # 保存配置的逻辑...
        self.save_node_config(node_name)
        
        # 显示简短的成功提示
        self.show_toast("配置已保存", "success", 2000)
        
    except Exception as e:
        self.show_toast(f"保存失败: {str(e)}", "error", 5000)
```

### 示例4：连接操作反馈

```python
def connect_nodes(self, source, target):
    """连接两个节点"""
    try:
        # 创建连线的逻辑...
        self.create_connection(source, target)
        
        # 显示成功提示
        self.show_toast(f"已连接: {source} → {target}", "success")
        
    except Exception as e:
        self.show_toast(f"连接失败: {str(e)}", "error")

def remove_connection(self, connection_id):
    """删除连线"""
    try:
        # 删除连线的逻辑...
        self.delete_connection(connection_id)
        
        # 显示信息提示
        self.show_toast("连线已删除", "info", 2000)
        
    except Exception as e:
        self.show_toast(f"删除失败: {str(e)}", "error")
```

### 示例5：警告提示

```python
def delete_node(self, node_name):
    """删除节点（需要确认）"""
    # 先显示确认对话框（阻断性操作）
    reply = QMessageBox.question(
        self,
        "确认删除",
        f"确定要删除节点 '{node_name}' 吗？\n此操作不可恢复！",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    
    if reply == QMessageBox.StandardButton.Yes:
        try:
            # 删除节点的逻辑...
            self.remove_node(node_name)
            
            # 显示警告提示（因为是不可逆操作）
            self.show_toast(f"节点 '{node_name}' 已删除", "warning", 4000)
            
        except Exception as e:
            self.show_toast(f"删除失败: {str(e)}", "error")
```

## 最佳实践总结

### ✅ 推荐使用的场景

1. **操作成功反馈**
   ```python
   self.show_toast("保存成功", "success")
   ```

2. **状态变更通知**
   ```python
   self.show_toast("节点已启动", "info")
   ```

3. **轻量级错误提示**
   ```python
   self.show_toast("加载失败，请重试", "error")
   ```

4. **一般性警告**
   ```python
   self.show_toast("注意：数据未保存", "warning")
   ```

### ❌ 不推荐使用的场景

1. **需要用户确认的操作** → 使用QMessageBox
   ```python
   # 错误示例
   self.show_toast("确定要删除吗？", "warning")  # ❌
   
   # 正确示例
   reply = QMessageBox.question(...)  # ✅
   ```

2. **严重错误需要立即处理** → 使用QMessageBox.critical
   ```python
   # 错误示例
   self.show_toast("数据库连接失败", "error")  # ❌
   
   # 正确示例
   QMessageBox.critical(self, "严重错误", "数据库连接失败")  # ✅
   ```

3. **频繁连续的通知** → 合并或去重
   ```python
   # 错误示例
   for node in nodes:
       self.show_toast(f"{node} 已更新", "success")  # ❌ 会弹出多次
   
   # 正确示例
   self.show_toast(f"{len(nodes)}个节点已更新", "success")  # ✅
   ```

## 类型选择指南

| 类型 | 颜色 | 使用场景 | 示例 |
|------|------|----------|------|
| info | 灰色 | 一般信息、状态变更 | "节点已加载" |
| success | 绿色 | 操作成功 | "保存成功" |
| warning | 橙色 | 警告、需要注意 | "磁盘空间不足" |
| error | 红色 | 错误、失败 | "连接超时" |

## 时长选择指南

| 时长 | 适用场景 |
|------|----------|
| 2000ms | 简短提示、快速反馈 |
| 3000ms | 一般通知（默认） |
| 4000ms | 重要信息、警告 |
| 5000ms | 错误详情、需要阅读的信息 |
