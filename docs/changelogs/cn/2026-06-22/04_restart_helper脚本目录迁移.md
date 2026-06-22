# 04_restart_helper脚本目录迁移

**日期**: 2026-06-22

## 背景

根目录下 `bnos_console.py` 作为主程序入口，同时平级放置了 `launcher.py`、`run_tests.py`、`restart_helper.py` 等辅助脚本。其中 `restart_helper.py` 只被 `bnos_console.py` 在重启流程中间接调用，并不需要直接暴露在根目录，导致根目录入口脚本与辅助脚本边界不清。

## 变更内容

### 新增 scripts/ 目录并迁移 restart_helper.py

- 新增目录：`scripts/`
- 原位置：`restart_helper.py` → 新位置：`scripts/restart_helper.py`
- 文件内容保持不变

### bnos_console.py：更新调用路径

在 `bnos_console.py` 中，定位 `restart_helper.py` 的方式由：

```python
restart_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart_helper.py")
```

改为：

```python
restart_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "restart_helper.py")
```

重启流程的功能保持不变：当 `app.exec()` 返回 `42` 时，主程序调用 `scripts/restart_helper.py` 作为中间进程，等待旧父进程退出后启动新实例。

## 受影响的技术文档

以下文档同步更新路径引用，保持与代码一致：

- `docs/BNOS_文件结构图.md`：在 Mermaid 图中新增 `scripts/` 节点，`restart_helper.py` 归入其子节点
- `docs/BNOS_架构图.md`：流程图中 `restart_helper.py` 改为 `scripts/restart_helper.py`
- `docs/BNOS_技术分析报告.md`：LOC 表格中文件名同步
- `docs/BNOS_项目优化分析报告.md`：根目录树形展示与 7.4 小节文件引用同步

## 验证

1. `bnos_console.py` 正常被导入/解析
2. `os.path.join(<脚本目录>, "scripts", "restart_helper.py")` 解析结果存在
3. 手动调用 `python bnos_console.py` → 菜单重启 → 返回码 42 → 新进程成功启动
