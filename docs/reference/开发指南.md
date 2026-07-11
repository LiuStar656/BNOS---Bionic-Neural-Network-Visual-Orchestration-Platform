# BNOS 项目开发规范

---

## 1. 概述

本文档基于对 BNOS 项目（Bionic Neural Network Visual Orchestration Platform）的代码分析，制定统一的开发规范，旨在提高代码质量、可维护性和团队协作效率。

**项目现状**：
- 总文件数：75 个 Python 文件
- 总行数：20,183 行
- 主要模块：画布渲染、UI面板、核心服务、工具脚本

---

## 2. 项目结构规范

### 2.1 目录结构

```
BNOS/
├── ui/                    # UI层
│   ├── canvas/            # 画布渲染模块
│   │   ├── items/         # 画布项（节点、连线、锚点）
│   │   └── ...
│   ├── panels/            # 面板组件
│   ├── dialogs/           # 对话框组件
│   ├── core/              # 核心服务
│   │   ├── utils/         # 工具函数
│   │   └── ...
│   ├── creators/          # 节点创建器
│   ├── icons/             # 图标资源
│   └── menu/              # 菜单管理
├── tools/                 # 辅助工具脚本
├── tests/                 # 测试文件
├── docs/                  # 文档（非示例代码）
└── resources/             # 资源文件
```

### 2.2 文件命名规范

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 模块文件 | 小写+下划线 | `canvas_layout.py` |
| 类文件 | 大驼峰 | `NodeItem.py`（如使用） |
| 测试文件 | `test_`前缀 | `test_canvas_process.py` |

### 2.3 模块职责划分

| 模块 | 职责 | 注意事项 |
|------|------|----------|
| `canvas/` | 画布渲染、节点交互、连线管理 | 避免业务逻辑侵入 |
| `panels/` | UI面板展示、用户交互 | 数据从主窗口获取 |
| `core/` | 核心服务、状态管理、工具函数 | 保持无状态、可复用 |
| `dialogs/` | 模态对话框 | 避免复杂业务逻辑 |

---

## 3. 代码命名规范

### 3.1 类命名

- **类名**：大驼峰（PascalCase）
- **私有类**：前缀下划线（`_PrivateClass`）

```python
class NodeItem(QGraphicsItem):       # ✅ 正确
class _NodeStyleBase:                 # ✅ 正确（私有基类）
class node_item:                      # ❌ 错误
```

### 3.2 函数命名

- **公共函数**：小写+下划线（snake_case）
- **私有函数**：双下划线前缀（`__private`）或单下划线前缀（`_protected`）
- **Getter/Setter**：使用 `get_`/`set_` 前缀

```python
def update_node_stats(self):          # ✅ 正确
def _sync_panels(self):               # ✅ 正确（内部方法）
def get_node_info(self, name):        # ✅ 正确（Getter）
def UpdateNodeStats(self):            # ❌ 错误
```

### 3.3 变量命名

- **普通变量**：小写+下划线
- **常量**：全大写+下划线
- **类成员变量**：前缀下划线

```python
node_name = "test_node"               # ✅ 正确
MAX_RETRY_COUNT = 3                   # ✅ 正确（常量）
self._node_stats = {}                 # ✅ 正确（成员变量）
NodeName = "test"                     # ❌ 错误
```

### 3.4 信号命名（Qt特有）

- 使用动词过去式表示事件已发生
- 使用 `changed`、`clicked`、`closed` 等后缀

```python
node_status_changed = Signal(str, str)  # ✅ 正确
canvas_closed = Signal()                # ✅ 正确
onNodeChange = Signal()                 # ❌ 错误
```

---

## 4. 代码质量规范

### 4.1 函数设计原则

1. **单一职责**：每个函数只做一件事
2. **参数限制**：尽量不超过 3-4 个参数
3. **返回值明确**：避免返回复杂嵌套结构

### 4.2 注释规范

```python
def update_node_stats(self):
    """更新节点资源占用表
    
    从画布获取当前节点列表，同步节点统计数据，
    移除已不存在的节点，更新表格显示。
    
    注意：当画布不存在时会清空统计数据
    """
    pass
```

### 4.3 错误处理

```python
def _load_log(self):
    """加载日志文件"""
    if not os.path.exists(self._log_file):
        self._log_editor.setPlainText("# 暂无日志")
        return
    
    try:
        with open(self._log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        # 处理内容...
    except Exception as e:
        logger.error(f"加载日志失败 {self._log_file}: {e}")
        self._log_editor.setPlainText(f"# 读取失败: {e}")
```

---

## 5. 生命周期管理规范 ⭐ 重点

基于本次修复的**资源清理问题**，制定以下规范：

### 5.1 对象创建与销毁

| 阶段 | 要求 | 示例 |
|------|------|------|
| **初始化** | 在 `__init__` 中完成所有资源分配 | 定时器、信号连接 |
| **使用中** | 定期检查资源有效性 | 检查 `canvas` 是否存在 |
| **销毁前** | 实现专门的清理方法 | `_on_close()`、`unsubscribe_monitor()` |
| **销毁时** | 断开信号、停止定时器、释放资源 | `timer.stop()`、`signal.disconnect()` |

### 5.2 资源清理检查清单

```python
def _on_close(self):
    """关闭时清理（必须实现）"""
    # 1. 停止定时器
    if self._update_timer:
        self._update_timer.stop()
        self._update_timer = None
    
    # 2. 取消订阅
    polling_manager.unwatch_log(self.node_path, "listener.log")
    
    # 3. 断开信号连接
    # 如果使用 Qt 信号，确保断开连接
    
    # 4. 清理数据结构
    self._node_stats.clear()
    
    # 5. 调用父类方法
    super()._on_close()
```

### 5.3 状态同步规范

当依赖对象（如画布）状态变化时，必须正确处理：

```python
def _sync_panels(self):
    """同步子面板列表与画布节点"""
    canvas = getattr(self.parent_window, 'canvas', None)
    
    # ✅ 必须检查画布是否存在
    if not canvas or not hasattr(canvas, 'nodes') or not canvas.nodes:
        # ✅ 画布不存在时清空所有子面板
        for name in list(self._sub_panels.keys()):
            self._remove_sub_panel(name)
        return
    
    # 正常同步逻辑...
```

### 5.4 定时器使用规范

```python
class MyWidget(QWidget):
    def __init__(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(1000)  # 启动
    
    def _on_close(self):
        if self._timer:
            self._timer.stop()  # 必须停止
            self._timer = None
```

---

## 6. Qt 特有的规范

### 6.1 信号槽连接

- 使用 `connect()` 时确保对象生命周期匹配
- 在对象销毁前断开连接

```python
def __init__(self):
    # ✅ 使用 lambda 时注意闭包变量引用
    self.button.clicked.connect(lambda: self._on_click(param))

def _on_close(self):
    # ✅ 断开所有连接
    self.button.clicked.disconnect()
```

### 6.2 事件处理

- 重写事件方法时调用父类实现
- 避免在事件处理中执行耗时操作

```python
def closeEvent(self, event):
    """关闭事件"""
    self._cleanup()
    super().closeEvent(event)  # ✅ 必须调用父类方法
```

### 6.3 内存管理

- 使用 `deleteLater()` 而非直接 `del`
- 避免循环引用

```python
def _remove_sub_panel(self, name):
    sub = self._sub_panels[name]
    sub.unsubscribe_monitor()
    self._layout.removeWidget(sub)
    sub.deleteLater()  # ✅ 正确
    del self._sub_panels[name]
```

---

## 7. 测试规范

### 7.1 测试覆盖要求

| 模块类型 | 覆盖率要求 | 测试类型 |
|----------|----------|----------|
| 核心工具函数 | ≥80% | 单元测试 |
| UI组件 | ≥50% | 集成测试 |
| 业务逻辑 | ≥70% | 单元+集成测试 |

### 7.2 测试文件结构

```
tests/
├── test_canvas_process.py    # 画布流程测试
├── test_panel_process.py     # 面板流程测试
├── test_core_process.py      # 核心流程测试
└── conftest.py               # 测试配置
```

### 7.3 测试命名规范

```python
def test_node_status_update():           # ✅ 正确
def test_资源监测器_画布关闭():          # ✅ 正确（中文描述）
def testSomething():                     # ❌ 错误
```

---

## 8. 代码审查规范

### 8.1 审查要点

| 检查项 | 检查内容 |
|--------|----------|
| **资源管理** | 是否正确清理定时器、信号连接 |
| **空值检查** | 是否对依赖对象进行空值判断 |
| **异常处理** | 是否有适当的 try-except |
| **代码重复** | 是否存在可提取的公共逻辑 |
| **命名规范** | 是否符合本规范 |
| **文档注释** | 关键函数是否有文档字符串 |

### 8.2 PR 提交要求

- 每次提交只解决一个问题
- 提供清晰的提交信息
- 包含单元测试（如有）

---

## 9. 预留功能管理

### 9.1 标记规范

对于预留的扩展接口，必须添加明确标记：

```python
def future_feature_example(self):
    """[预留] 未来扩展功能 - 多画布同步
    
    本方法为预留接口，暂未实现。
    预期用途：实现多个画布之间的数据同步。
    
    @status: reserved
    @since: v1.0
    """
    pass
```

### 9.2 定期清理

- 每季度进行一次代码清理审计
- 移除确认不再需要的预留接口
- 更新代码分析报告

---

## 10. 总结

本规范基于项目实际问题制定，重点关注：

1. **资源生命周期管理** - 避免内存泄漏和数据残留
2. **代码质量** - 提高可读性和可维护性
3. **团队协作** - 统一规范便于协作开发
4. **持续改进** - 定期审查和清理

**核心原则**：
> "每个对象都应该知道如何清理自己"

---

**版本**: v1.0  
**生效日期**: 2026年5月  
**适用范围**: BNOS 项目所有 Python 代码