# BNOS Toast通知快速使用指南 ⚡

## 🎯 什么是Toast通知？

Toast通知是BNOS平台右下角自动消失的提示框，用于替代传统的弹窗对话框，提供更流畅的用户体验。

## 📍 显示位置

```
┌─────────────────────────────┐
│                             │
│      BNOS 主画布区域         │
│                             │
│                             │
│                          ┌──────┐
│                          │ Toast│ ← 右下角，距离边缘20px
│                          └──────┘
└─────────────────────────────┘
```

## 🎨 四种类型

| 类型 | 颜色 | 用途 | 示例 |
|------|------|------|------|
| **info** | 灰色 `rgba(50,50,50)` | 一般信息提示 | "节点已在运行中" |
| **success** | 绿色 `rgba(76,175,80)` | 操作成功反馈 | "节点启动成功" |
| **warning** | 橙色 `rgba(255,152,0)` | 警告提醒 | "请先选择节点" |
| **error** | 红色 `rgba(244,67,54)` | 错误提示 | "操作失败" |

## 💻 代码调用

### 基础用法
```python
# 最简单的调用（默认info类型，3秒）
self.show_toast("这是一条消息")

# 指定类型
self.show_toast("操作成功！", "success")
self.show_toast("请注意", "warning")
self.show_toast("出错了", "error")

# 自定义时长（毫秒）
self.show_toast("长时间提示", "info", 5000)  # 5秒
```

### 实际应用场景

#### 1. 节点操作反馈
```python
# 启动节点
def start_node(self, node_name):
    # ... 启动逻辑 ...
    self.show_toast(f"节点 {node_name} 已启动", "success")

# 停止节点
def stop_node(self, node_name):
    # ... 停止逻辑 ...
    self.show_toast(f"节点 {node_name} 已停止", "success")
```

#### 2. 项目操作反馈
```python
# 创建项目
def new_project(self):
    # ... 创建逻辑 ...
    self.show_toast(f"已创建项目: {project_name}", "success")

# 打开项目
def open_project(self):
    # ... 打开逻辑 ...
    self.show_toast(f"已打开项目: {project_name}", "success")
```

#### 3. 验证和警告
```python
# 检查前置条件
if not self.current_project_path:
    self.show_toast("请先打开或新建项目", "warning")
    return

# 检查节点状态
if node_info['status'] == 'running':
    self.show_toast("节点已在运行中", "info")
    return
```

## ⚙️ 技术细节

### 动画参数
- **淡入时间**：300ms
- **停留时间**：可自定义（默认3000ms）
- **淡出时间**：300ms
- **帧率**：60fps（16ms/帧）

### 生命周期
```
创建 → 淡入(300ms) → 停留(N ms) → 淡出(300ms) → 销毁
```

### 位置计算
```python
# 相对于父窗口右下角
x = parent.right() - toast.width() - 20
y = parent.bottom() - toast.height() - 20
```

## 🔄 与QMessageBox的区别

| 特性 | Toast通知 | QMessageBox |
|------|----------|-------------|
| **阻塞性** | ❌ 非模态，不阻塞 | ✅ 模态，阻塞操作 |
| **自动消失** | ✅ 是 | ❌ 需用户点击 |
| **适用场景** | 成功提示、警告 | 确认操作、严重错误 |
| **用户体验** | 流畅、不打断 | 打断流程 |

## 📋 最佳实践

### ✅ 推荐使用的场景
1. **操作成功反馈**：节点启动/停止、项目创建/打开
2. **轻量级警告**：未选择节点、目录不存在
3. **状态提示**：节点已在运行、配置已保存
4. **临时信息**：刷新完成、加载进度

### ❌ 不应使用的场景
1. **需要用户确认的操作**：删除节点、覆盖文件 → 用 `QMessageBox.question`
2. **严重错误**：系统崩溃、关键依赖缺失 → 用 `QMessageBox.critical`
3. **重要决策**：退出未保存项目 → 用 `QMessageBox.question`

## 🎓 完整示例

```python
class MyFeature:
    def execute_operation(self):
        # 1. 验证前置条件
        if not self.is_ready():
            self.show_toast("系统未就绪，请先配置", "warning")
            return
        
        try:
            # 2. 执行操作
            result = self.do_something()
            
            # 3. 成功反馈
            self.show_toast(f"操作完成！结果: {result}", "success")
            
        except ValueError as e:
            # 4. 一般错误
            self.show_toast(f"输入错误: {str(e)}", "error")
            
        except Exception as e:
            # 5. 严重错误（保留QMessageBox）
            QMessageBox.critical(self, "严重错误", f"系统异常: {str(e)}")
```

## 🔧 自定义扩展

如需修改Toast样式，编辑 `ui/main_window.py` 中的 `ToastNotification.__init__` 方法：

```python
# 修改背景色透明度
background-color: rgba(50, 50, 50, 230);  # 最后一个值是透明度(0-255)

# 修改圆角大小
border-radius: 8px;  # 改为其他值

# 修改字体大小
font-size: 14px;  # 改为其他值

# 修改内边距
padding: 12px 20px;  # 上下12px，左右20px
```

## 📖 相关文档

- [Toast系统集成完成报告](TOAST_INTEGRATION_COMPLETE.md) - 详细的技术实现说明
- [Qt动画优化经验](memory: Qt UI动画性能优化经验) - 高精度定时器技术细节

---

**提示**：所有Toast通知都会自动消失，无需用户干预，让操作流程更加流畅！🚀
