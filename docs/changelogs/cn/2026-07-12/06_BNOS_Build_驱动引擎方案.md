# 06 BNOS Build 驱动引擎方案

## 概述

重新设计 BNOS Build 方案，从"复制文件到新目录"的**导出模式**变为"向项目根目录注入文件"的**驱动层模式**。驱动引擎与源文件完全隔离，可独立删除和更新。

---

## 一、概念升级

| 之前 | 之后 |
|------|------|
| `bnos build pipeline.json --output ./dist` | `bnos build` |
| 导出整个项目到新文件夹 | 向项目根目录注入 5 个驱动文件 |
| 引擎 = 项目一部分 | **引擎 = 可插拔外挂层**（类比 USB 驱动程序） |

---

## 二、引擎隔离原则

```
项目根目录/
├── nodes/              ← 源文件（引擎不碰）
│   ├── preprocess/
│   │   └── main.py
│   └── inference/
│       └── main.py
│
├── bnos_runtime/       ← 驱动引擎（纯注入）
│   ├── engine.py       ← 入口：类型分发
│   ├── pipeline.json   ← 自动生成
│   ├── standalone_runner.py
│   ├── composite_runner.py
│   └── venv_resolver.py
│
├── .gitignore          ← 推荐忽略 bnos_runtime/
└── pipeline.json       ← 画布拓扑定义（bnos build --update 自动更新）
```

**删除引擎 = `bnos build --clean`**（白名单删除，不碰 `nodes/` 一根毛）。

---

## 三、命令一览

| 命令 | 作用 |
|------|------|
| `bnos build` | 注入驱动引擎（首次） |
| `bnos build --force` | 覆盖已有引擎 |
| `bnos build --clean` | 删除驱动引擎 |
| `bnos build --update` | 节点结构变更后，仅重建 `pipeline.json` + 编排器 |
| `bnos build --docker` | 同时生成 `Dockerfile` + `.dockerignore` |

---

## 四、运行时

```bash
# 无需 BNOS GUI，纯 Python 即可运行
python -m bnos_runtime.engine pipeline.json
```

引擎内部根据 pipeline.json 的节点类型自动分发：独立节点 → `standalone_runner`，复合节点 → 预生成的 `orchestrator.py`。

---

## 五、节点类型混合支持

| 节点类型 | 启动方式 | 运行时 |
|------|------|------|
| 独立节点 | `subprocess.Popen([venv/python, listener.py])` | 每个节点独立进程 |
| 复合节点 (inprocess) | `subprocess.Popen([venv/python, orchestrator.py])` | 单进程 import 子节点 |
| 复合节点 (process) | 分别启动子节点进程 | 多进程 |

---

完整方案见 `docs/design/BNOS_Build_独立应用打包方案.md`。
