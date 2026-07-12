# 07 except Exception: pass 全面治理

## 概述

全项目消除 100 处 `except Exception: pass`，替换为精确的异常类型。这是 BNOS 历史上最大规模的单次代码质量治理。

---

## 一、为什么要治理

`except Exception: pass` 会静默吞掉包括 `KeyboardInterrupt`、`SystemExit`、`MemoryError` 在内的**所有异常**。在运行时错误场景下，这导致"什么都没发生但也不知道为什么"的体验黑洞。

---

## 二、治理范围

| | 之前 | 之后 |
|------|:---:|:---:|
| `except Exception: pass` | **100 处** / 25 文件 | **0 处** |
| 修改文件数 | — | **26** |

---

## 三、异常类型映射

| 场景 | 新异常类型 | 出现次数 |
|------|------|:---:|
| psutil 进程访问 | `(NoSuchProcess, AccessDenied)` | ~16 |
| 文件 IO / PID 读写 | `OSError` | ~35 |
| Qt 图形项操作 | `(AttributeError, RuntimeError)` | ~25 |
| 进程管理 (kill/terminate) | `(ProcessLookupError, OSError)` | ~8 |
| JSON 配置读写 | `(ValueError, OSError)` | ~10 |
| 其他 (group/dialog/layout) | `RuntimeError` | ~6 |

---

## 四、最严重的 5 个文件

| 文件 | 修复前 | 修复后 |
|------|:---:|:---:|
| `system_resource_collector.py` | 10 | 0 |
| `composite_node.py` | 8 | 0 |
| `settings_dialog.py` | 6 | 0 |
| `edge_item.py` | 4 | 0 |
| `node_config_dialog.py` | 3 | 0 |

---

## 五、原则

每条替换遵循"只捕获真正可能发生的异常"原则：
- 文件操作 → `OSError`（而不是 `Exception`）
- 已退出进程 → `ProcessLookupError`（而不是 `Exception`）
- Qt 已销毁对象 → `RuntimeError`（而不是 `Exception`）
- psutil 权限不足 → `AccessDenied`（而不是 `Exception`）

不会掩盖 bug，同时仍然能优雅处理运行时边界条件。
