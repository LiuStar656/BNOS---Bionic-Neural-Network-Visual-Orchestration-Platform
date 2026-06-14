# 【2026-06-14】V2.0.14 - PyQt6 → PySide6 全栈迁移

---

## 更新列表

### 1. PyQt6 → PySide6 全栈迁移

[详细内容](./01_PyQt6迁移PySide6全栈替换.md)

- 许可证升级：GPL v3 → **LGPL v3**，免除闭源商用授权费
- 100 个源文件，233 处 import 替换
- 66 处 `pyqtSignal` → `Signal`，4 处 `pyqtSlot` → `Slot`
- 零业务逻辑变更，纯 API 名称映射
- signals 信号 emit/connect 调用语法无需修改

---

## 主要更新

| 类别 | 更新内容 |
|------|----------|
| **依赖替换** | PyQt6 → PySide6 6.11.1，requirements.txt 更新 |
| **语法适配** | pyqtSignal → Signal，pyqtSlot → Slot |
| **文档更新** | README/CHANGELOG/国际化字符串同步更新 |
| **构建配置** | build_bnos.spec hiddenimports 更新为 PySide6 |

---

## 验证结果

- ✅ 169/169 Python 源文件编译通过
- ✅ 启动测试：主窗口、Dock 面板、画布、IPC 全部正常
- ✅ 终端面板 (QProcess) 正常工作
- ✅ 节点加载/停止/监控正常
- ✅ 历史回滚 (undo/redo) 正常
- ✅ 资源监测轮询正常
- ✅ 窗口状态持久化正常
- ✅ `pyqtSignal` / `PyQt6` 残留为 0
