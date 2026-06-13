# Photoshop 风格历史回滚功能

## 背景

原有的 undo/redo 存在以下问题：

1. **双向栈模式**：redo 栈在新操作后丢失，无法回溯到更早状态后继续
2. **无可视化历史**：用户不知道 undo 会回退到哪个状态，也不知道总共做了多少步操作
3. **锚点恢复不可靠**：多端口场景下，undo 重做连线时锚点可能恢复到错误的端口

需要一个像 Photoshop 那样的历史面板：清晰的列表、可点击跳转、不会丢失 redo 能力。

---

## 设计方案

采用 **扁平命令列表 + current_index 指针** 替代双向栈：

```
         commands[]
         ↓
[0] [1] [2] [3] [4] [5] [6] [7] ...
                  ↑
            current_index = 4

undo → current_index = 3, execute commands[4].undo()
redo → current_index = 4, execute commands[5].execute()
jump_to(2) → undo [4], undo [3], execute [2]
```

- **jump_to(n)**：一口气 undo/execute 到目标位置，支持从历史面板点击任意条目跳转
- **新操作覆盖尾部**：`current_index=4` 时执行新操作 → 丢弃 [5,6,7]，追加新 command 到 [5]
- **redo 能力不丢失**：只要不执行新操作，redo 始终可用

---

## 实现架构

```
ui/core/commands/
├── base.py              # Command 基类 (execute/undo/description)
├── history_manager.py   # HistoryManager 单例 (commands[] + current_index)
├── node_commands.py     # CreateNodeCommand / DeleteNodeCommand / MoveNodeCommand
└── edge_commands.py     # CreateEdgeCommand / DeleteEdgeCommand
```

### Command 基类

```python
class Command(ABC):
    @abstractmethod
    def execute(self): ...

    @abstractmethod
    def undo(self): ...

    @property
    def description(self) -> str: ...
```

### HistoryManager 单例

```python
class HistoryManager(QObject):
    COMMANDS_LIMIT = 500
    history_changed = Signal()   # UI 刷新信号
    index_changed = Signal(int)

    def execute_command(self, command): ...
    def record_only(self, command): ...
    def undo(self): ...
    def redo(self): ...
    def jump_to(self, index): ...
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
```

### HistoryPanel UI

- `HistoryPanelWidget`：QWidget 内部面板，包含 QListWidget 显示操作列表 + 清除按钮 + 信息标签
- 连接 `history_manager.history_changed` / `index_changed` 信号自动刷新
- 点击列表项 → `jump_to(index)` 跳转到对应状态

---

## Bug 修复历程

### 删线报错：`ValueError: list.remove(x): x not in list`

- **根因**：`_record_delete_edge` 中 `DeleteEdgeCommand.execute()` 内部已移除 edge，外层再 `self.edges.remove(edge)` 报错
- **修复**：录制后检查 `edge not in self.edges`，已移除则跳过

### 重连线提示"已存在"

- **根因**：`_record_create_edge` 用 `execute_command()` 二次执行 `create_edge`
- **修复**：改为 `record_only()` 只记录不二次执行

### 小锚点连线删除后撤回连到大锚点

- **第一层根因**：`_record_delete_edge` 没传端口名
- **第二层根因**：`_resolve_anchor` 用 `node.input_ports`（不存在）
- **第三层根因**：`edge.target_port_name` 属性不存在 → EdgeItem 存为 `_desired_target_port_name`
- **修复**：`getattr(edge, '_desired_target_port_name', None)` 正确解析目标端口名

---

## 关键改动文件

| 文件 | 改动 |
|------|------|
| `ui/core/commands/base.py` | Command 抽象基类 |
| `ui/core/commands/history_manager.py` | HistoryManager 单例（扁平列表 + current_index + jump_to） |
| `ui/core/commands/edge_commands.py` | CreateEdgeCommand / DeleteEdgeCommand（含 `_resolve_anchor`） |
| `ui/core/commands/node_commands.py` | CreateNodeCommand / DeleteNodeCommand / MoveNodeCommand |
| `ui/panels/history_panel.py` | HistoryPanelWidget + HistoryPanelDock |
| `ui/canvas/canvas_connections.py` | 连线增删自动录制 + `_desired_target_port_name` |
| `ui/canvas/canvas_view.py` | 重放保护机制 |
| `ui/main_window/panel.py` | `show_history_panel()` 方法 |
| `ui/menu/menu_manager.py` | 工具菜单新增「历史记录」入口 |

---

## 验证结果

- ✅ undo/redo 正确恢复节点位置、连线、锚点绑定
- ✅ HistoryPanel 可视化列表实时更新
- ✅ 多端口场景下锚点恢复正确（不再 fallback 到 default 锚点）
- ✅ 删线 → undo 恢复连线 → 锚点端口正确
- ✅ 从菜单栏「工具 → 历史记录」打开面板正常
