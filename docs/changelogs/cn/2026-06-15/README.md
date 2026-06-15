# 【2026-06-15】V2.0.15 - 节点样式统一化、Bug 修复与 venv 可迁移化

---

## 更新列表

### 1. 节点样式统一化与锚点坐标修复

[详细内容](./01_节点样式统一化_锚点坐标修复与生命周期保护.md)

- **节点样式精简**：删除矩形/圆点样式文件（rect.py、dot.py），全系统统一为面板模式 DetailedNodeStyle
- **锚点位置统一**：输入/输出锚点回落位置改为节点两侧边线中点（x=0/nw, y=h/2）
- **坐标系统修复**：修正 `setPos` 多减 `size/2` 的偏移 bug 和 `_find_nearest` 补偿 bug，消除 8px 视觉偏移
- **继承链修正**：DetailedNodeStyle 直接继承 NodeStyle 基类，不再依赖已删除的 RectNodeStyle
- **进程生命周期保护**：TerminalProcess 析构时对已销毁的 QProcess 对象加 RuntimeError 保护

---

### 2. dialog_utils.py pick 函数 UnboundLocalError 修复

[详细内容](./02_dialog_utils_pick函数UnboundLocalError修复.md)

- **根因**：`pick_folder` / `pick_file` / `pick_save_file` 中 `go_up` / `sel_path` 闭包函数定义在 `_create_nav_bar(..., go_up)` 调用之后，Python 前向引用触发 `UnboundLocalError`
- **修复**：将 `go_up` / `sel_path` 定义移至 `_create_nav_bar` 调用之前，删除尾部重复定义
- **影响范围**：打开项目、导入节点、导出节点、导出项目全部恢复正常

---

### 3. 项目打开异步化与画布布局加载修复

[详细内容](./03_项目打开异步化与画布布局加载修复.md)

- **异步化**：`project_open()` 改为 `QTimer.singleShot` 两阶段加载，不再阻塞主线程；`project_refresh(async_mode=True)` 与节点启停流程一致
- **画布布局修复**：第二个项目打开后节点为空的根因 — `canvas_host.py` 中 `canvas_changed.emit()` 信号在 `load_layout()` 之前触发，导致空 dict 回写主窗口 nodes_data。修复后顺序：`load_layout` → `update_canvas_data` → `canvas_changed.emit`
- **用户体验**：打开大项目（50+ 节点）时 Toast 正常显示，UI 可响应

---

### 4. Python 节点虚拟环境可迁移化

[详细内容](./04_Python节点虚拟环境可迁移化.md)

- **创建时去绝对路径**：`python_create_node.py` 用 `--copies` 创建 venv，`start.json` 不再写入 `python_exe` / `path` 绝对路径，由运行时 `node_process.py` 的 fallback 自动推断
- **导入时自动修复**：`_repair_portable_venv()` 重写 `pyvenv.cfg` 的 `home` 指向目标机器 Python，清理 `start.json` 遗留绝对路径
- **打包优化**：`packager.py` 压缩时跳过 `__pycache__` 和 `.pyc`，包体积减少约 30-40%
- **效果**：Python 节点导出为 `.bnos` 后，在其他机器导入**无需重新 `pip install`** 即可直接启动运行

---

## 主要更新

| 类别 | 更新内容 |
|------|----------|
| **样式系统** | 删除 rect.py / dot.py，统一为面板模式 DetailedNodeStyle；锚点位置统一为两侧边线中点；修正 setPos 8px 偏移 |
| **Bug 修复** | dialog_utils 三函数 `UnboundLocalError`；第二项目打开画布布局丢失；TerminalProcess QProcess 析构保护 |
| **异步化** | project_open 改为 QTimer.singleShot 两阶段异步加载，与节点启停的 async_mode 一致 |
| **节点可迁移化** | start.json 去绝对路径；导入时 `_repair_portable_venv` 动态修复 `pyvenv.cfg`；打包跳过字节码缓存 |
| **代码质量** | canvas_host.py 信号触发顺序修正；packager.py zip 压缩跳过字节码缓存；169/169 编译通过 |

---

## 验证结果

- ✅ 169/169 Python 源文件编译通过
- ✅ 打开项目对话框：`pick_folder` 正常，无 `UnboundLocalError`
- ✅ 导入/导出节点对话框：`pick_file` / `pick_save_file` 正常
- ✅ 同时打开两个项目：第二个项目画布布局正确加载
- ✅ 大项目打开：不阻塞主线程，Toast 正常显示
- ✅ Python 节点跨机器迁移：导入后无需重新 pip install，直接启动
- ✅ 节点样式：面板模式正确渲染，无 8px 锚点偏移
- ✅ `PyQt6` / `pyqtSignal` / `pyqtSlot` 全代码残留为 0
