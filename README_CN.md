# BNOS — 仿生神经网络程序操作系统

🌍 **语言**: [English](README.md) | **中文**

<div align="center">

![BNOS Logo](./bnos_logo.png)

![Python](https://img.shields.io/badge/Python-3.12+-yellow?style=for-the-badge&logo=python)
![PySide6](https://img.shields.io/badge/PySide6-Latest-green?style=for-the-badge&logo=qt)
![Rust](https://img.shields.io/badge/Rust-Supported-orange?style=for-the-badge&logo=rust)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge)

**纯桌面端可视化节点编排平台 — 跨语言、跨进程构建 DAG 工作流。**

</div>

---

## 项目简介

BNOS 是一款基于 PySide6 的桌面应用，用于将计算工作流可视化为**有向无环图（DAG）** 的独立进程编排系统。每个节点是一个独立程序，拥有自己的虚拟环境，可使用任意支持的语言（Python、Rust 等）编写，通过**基于文件的 JSON 协议**和注意力过滤机制通信。

平台提供 VSCode 风格深色界面和无限画布 — 拖拽节点、连线、一键管理生命周期。

> 历史 README 归档于 [docs/archived/README_CN_v1_archived.md](docs/archived/README_CN_v1_archived.md)

---

## 核心设计

### 1. 代码优先，可视化编排

BNOS 不是低代码平台。节点是**真正的程序** — 你可以在任何 IDE 中编写完整源码。画布是架在其上的可视化编排层：管理连线、数据流和生命周期。

### 2. 每节点独立进程隔离

每个节点作为**独立的操作系统进程**运行，拥有自己的 `venv/`。无共享运行时，无依赖冲突。一个节点崩溃，其他节点不受影响。平台通过 PID 文件和定期健康轮询监控进程状态。

### 3. 基于文件的 JSON 通信

节点通过读写 `output.json` 文件进行通信。上游节点写入结果，下游节点轮询读取。**注意力过滤规则**（`node_config.json` 中的 `filter` 字段）使每个节点可选择性地处理匹配的数据类型 — 实现条件 DAG 路由。

### 4. 复合节点 — DAG 压缩

旗舰级功能。在画布上选中多个节点，压缩为**单个复合节点**。平台自动：
- 校验子 DAG（单入口、无环）
- 生成 `orchestrator.py` 编排器，按拓扑顺序执行内部 DAG
- 合并依赖，创建独立的复合 `venv`
- 管理端口路由：外部连线正确重映射到复合边界

复合节点可**展开**（显示内部结构）或**折叠**（显示为单个块）。编排器以常驻轮询进程运行，支持通过 `.pipe` 信号文件**热重载** DAG 拓扑。

---

## 架构

```
launcher.py (tkinter 启动动画)
  └─ bnos_console.py (主入口)
       └─ ApplicationContext (单例服务聚合器)
            ├─ EventBus  (发布-订阅解耦)
            ├─ DIContainer (依赖注入)
            ├─ PollingManager (状态 / 日志 / 配置轮询)
            ├─ ProcessManager (子进程生命周期)
            └─ NodeControlService (节点启停)
       └─ BNOSMainWindow (8 个 Mixin 模块)
            ├─ 画布 (QGraphicsView, 视口裁剪)
            │    ├─ NodeItem (3 种样式：方形 / 圆形 / 详细版)
            │    ├─ EdgeItem (贝塞尔连线)
            │    └─ 绘图层 + 参数控件 (11 种类型)
            ├─ 面板 (节点列表、监测、历史、资源…)
            └─ CompositeNodeManager (压缩 / 展开 / 编排)
```

每个节点的磁盘结构：
```
nodes/<名称>/
  ├─ node_config.json   # listen_upper_file, filter, ports, parameters
  ├─ main.py            # 处理逻辑 (读取 stdin JSON, 写入 stdout JSON)
  ├─ listener.py        # 轮询守护进程: 监听 output.json → 过滤 → 调用 main.py
  ├─ output.json        # main.py 产出, 被下游节点消费
  └─ venv/              # 独立 Python 环境
```

---

## 快速开始

### 前置要求

- Python 3.12+
- Windows 10/11（主要支持），Linux/macOS（部分支持）

### 安装与运行

```bash
git clone https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform.git
cd BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform

# 创建项目虚拟环境
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/macOS

pip install -r requirements.txt

# 启动 (带启动动画)
python launcher.py
# 或直接启动
python bnos_console.py
```

### 第一个工作流

1. **新建项目** → 选择一个文件夹（自动创建 `nodes/`）
2. **新建节点** → 命名、选语言 → 生成配置 + venv + 入口脚本
3. **添加到画布** → 右键节点列表中的节点
4. **连线** → 从 **OUT** 锚点（蓝色）拖到 **IN** 锚点（绿色）
5. **启动** → 双击节点，点击 ▶️

---

## 核心功能

### 可视化画布
无限画布，支持缩放（0.1x–5.0x）、平移、框选、多选，ComfyUI 风格直角连线带折叠手柄。视口裁剪和背景缓存确保 60fps 流畅交互。

### 复合节点系统
将子 DAG 压缩为可复用的复合块。自动生成编排器脚本、隔离 venv 和端口路由。支持画布上展开/折叠，外部连线在复合边界变化时正确重映射。

### 多语言节点
Python 节点已完整支持。Rust 节点提供自愈构建和双二进制架构。Node.js、Go、Java、C++、Ruby 节点生成器开发中。

### 进程健康检测
PID 文件持久化，跨会话恢复。定期健康轮询（2 秒间隔）。`taskkill /F /T` 原子杀进程树。系统扫描兜底检测僵尸进程。

### 节点注册表与外部挂载
`node_registry.json` 持久化记录所有节点。外部目录可**挂载**（引用而非复制）到项目中，带锁定组保护。安全卸载保留源文件。

### 启动队列
可配置的批量启动并发控制。优先级调度、自动重试（3 次）、队列状态持久化。

### 历史回滚
Command 模式实现画布操作 undo/redo。可视化历史面板显示操作时间线，点击任意条目跳转到该状态。

### 类 Photoshop UI
VSCode 深色主题，自定义无边框标题栏，浮动面板，停靠系统，Toast 通知（FIFO 队列、智能替换），i18n 国际化（中/英），IDE 自动检测（VSCode、Trae）。

---

## 项目结构

```
BNOS/
├── launcher.py                     # 启动动画
├── bnos_console.py                 # 主入口 (PySide6 应用)
├── build_bnos.spec                 # PyInstaller 打包配置
│
├── ui/
│   ├── main_window/                # BNOSMainWindow + 8 个 Mixin
│   ├── core/
│   │   ├── node/
│   │   │   ├── composite_node.py   # ★ 复合节点 DAG 引擎 (~2800 行)
│   │   │   ├── node_process.py     # 进程生命周期管理
│   │   │   ├── node_registry.py    # 节点注册表
│   │   │   ├── connection_inferrer.py
│   │   │   └── composite_orchestrator.py
│   │   ├── system/                 # EventBus, DI, PollingManager, IPC
│   │   ├── services/               # ApplicationContext, ProcessManager
│   │   ├── dock/                   # BNOS 停靠系统
│   │   └── project/                # 项目与文件导入导出
│   ├── canvas/                     # QGraphicsView 画布引擎
│   │   ├── items/                  # NodeItem, EdgeItem, AnchorItem
│   │   ├── drawing/                # 绘图层与工具栏
│   │   └── parameter_widgets/      # 11 种参数控件
│   ├── panels/                     # 节点列表、监测、历史等面板
│   └── dialogs/                    # 配置、颜色、文件浏览器等对话框
│
├── tools/                          # 节点模板生成器 (Python, Rust)
├── docs/                           # 文档与更新日志
│   └── archived/                   # 历史 README 归档
└── nodes/                          # 用户创建的节点 (运行时)
```

---

## 扩展开发

### 添加新语言
在 `tools/` 中注册生成器，在 `ui/core/node/language_detector.py` 中添加检测逻辑。

### 自定义节点样式
在 `ui/canvas/items/styles/` 中继承 `NodeStyle`，在 `StyleRegistry` 中注册。

### 添加新参数控件
在 `ui/canvas/parameter_widgets/` 中继承 `ParameterWidget`，在 `WidgetRegistry` 中注册。

---

## 已知限制

- DAG 环检测已实现，但展开态下用户应避免循环连线
- 移动项目文件夹可能导致绝对路径失效
- 画布上超过 100 个节点可能影响性能
- Linux/macOS 功能部分测试

---

## 开源协议

MIT License © 2026 阿东与守一工作室 · [LICENSE](LICENSE)

---

<div align="center">

[快速开始](#快速开始) · [架构](#架构) · [核心功能](#核心功能) · [项目结构](#项目结构)

</div>
