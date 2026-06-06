# 🧠 BNOS Console：仿生神经网络可视化编排平台

> 基于 PyQt6 开发的纯桌面端仿生可视化编排平台，支持多语言节点、拖拽式神经回路构建和实时监控

---

## 🎯 项目亮点  

### 🔧 核心特性

- **🧠 仿生神经网络架构**：模拟人脑神经元网络，节点作为独立进程运行，环境完全隔离
- **🖥️ 纯桌面端应用**：无需云端依赖，数据安全可控，离线也能运行
- **🎨 可视化编排画布**：无限画布、拖拽交互、智能突触连接，ComfyUI 风格直角连线
- **⚡ 多语言节点支持**：Python、Rust 已实装，Node.js、Go、Java、C++、Ruby 开发中
- **👀 实时监控系统**：进程健康检测、状态指示灯、日志查看器，全方位监控节点运行
- **🔒 环境隔离**：每个节点拥有独立虚拟环境，彻底解决依赖冲突问题

### 🚀 技术优势

| 对比维度 | BNOS 平台 | 传统低代码平台 |
|---------|----------|--------------|
| **核心理念** | 代码优先，辅以可视化编排 | 可视化优先，代码扩展受限 |
| **执行模型** | 每个节点独立进程运行 | 中心化引擎管理所有组件 |
| **性能表现** | 原生性能（Rust 比 Python 快 10-100 倍） | 受限于平台解释层 |
| **可扩展性** | 无限制，支持任意编程语言 | 仅限于平台提供的插件 |
| **可移植性** | 节点是独立应用，易于迁移 | 与平台紧密耦合，难以提取 |

---

## 🎨 界面展示

### 🌙 VSCode 风格深色主题
- 黑色无边框窗口，仿 VSCode 深色主题（`#1e1e1e`）
- 自定义标题栏，支持拖拽移动、双击最大化
- 全局深色风格，菜单、滚动条、对话框统一风格

### 🧠 神经网络画布
- **无限缩放**：0.1x-5.0x 自由缩放，支持鼠标滚轮、右键拖拽
- **智能布局**：节点自动避开重叠，拖拽时自动推开相邻节点
- **突触连接**：点击输出锚点 → 输入锚点，自动配置上下游路径
- **批量操作**：框选、Ctrl+点击多选，支持批量移动、启停

### 📊 实时监控面板
- **状态指示灯**：绿色（运行中）/ 灰色（已停止），直观显示节点状态
- **日志查看器**：实时读取 `listener.log`，支持滚动查看和历史回溯
- **进程管理**：一键启停节点，使用进程组确保彻底清理

---

## 🛠️ 快速开始

### 前置要求
- Python 3.12+（推荐 3.12）
- Windows 10/11（主要支持），Linux/macOS（部分支持）
- 500MB+ 磁盘空间（用于虚拟环境）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform.git
cd "BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main"

# 2. 创建虚拟环境
python -m venv myenv_new

# 3. 激活环境
myenv_new\Scripts\activate  # Windows
# source myenv_new/bin/activate  # Linux/macOS

# 4. 安装依赖
pip install -r requirements_gui.txt

# 5. 启动应用
python bnos_gui.py
```

### 一键启动（Windows）
```powershell
& ".\start_bnos_gui.bat"
```

---

## 🎯 应用场景

### 🤖 AI Agent 工作流
- **感知节点**：图像识别、语音转文字、传感器数据采集
- **推理节点**：LLM 调用、逻辑判断、决策生成
- **执行节点**：API 调用、数据库操作、文件写入
- **编排方式**：拖拽连线构建完整的 Agent 工作流

### 📊 数据流水线
- **ETL 流程**：数据清洗 → 转换 → 加载
- **实时处理**：日志收集 → 分析 → 告警
- **批处理任务**：文件扫描 → 处理 → 归档

### 🌐 微服务组件
- **API 网关**：请求路由 → 认证 → 转发
- **后台任务**：定时执行 → 执行 → 结果通知
- **事件驱动**：消息监听 → 业务处理 → 状态更新

### 🔬 科研实验
- **神经网络仿真**：节点 → 突触连接 → 信号传递
- **注意力机制研究**：过滤规则调整 → 任务过滤效果观察
- **涌现行为探索**：多节点协同实验

---

## 📦 项目结构

### 🏗️ 整体架构

```
BNOS/
├── bnos_gui.py                    # 主入口文件 - 初始化 QApplication，启动主窗口
├── start_bnos_gui.bat             # Windows 启动脚本
├── start_bnos_gui.sh              # Linux/macOS 启动脚本
├── build_bnos.spec                # PyInstaller 打包配置
├── app_config.json                # 应用级配置（窗口状态、最后项目路径）
├── canvas_layout.json             # 画布布局持久化（含节点样式）
├── color_settings.json            # 颜色设置持久化
├── requirements_gui.txt           # GUI 依赖列表
│
├── ui/                            # UI 模块
│   ├── __init__.py                # 统一入口
│   ├── main_window.py             # 主窗口类 - 整合所有 UI 组件
│   ├── canvas_widget.py           # 画布兼容入口（Facade 模式，仅 15 行）
│   │
│   ├── core/                      # 核心基础组件
│   │   ├── app_config.py          # 应用配置管理
│   │   ├── theme.py               # 深色 QSS 主题
│   │   ├── node_process.py        # 节点进程管理
│   │   ├── dark_title_bar.py      # VSCode 风格标题栏
│   │   ├── floating_panel.py      # 浮动面板基类
│   │   ├── logger.py              # 全局日志模块（控制台+文件双通道）
│   │   └── toast/                 # Toast 通知系统
│   │       └── toast_notification.py
│   │
│   ├── menu/                      # 菜单系统
│   │   └── menu_manager.py        # 菜单栏管理器
│   │
│   ├── canvas/                    # 画布系统
│   │   ├── __init__.py
│   │   ├── canvas_view.py         # 画布主视图 - 节点绘制、拖拽、连线
│   │   ├── canvas_colors.py       # 颜色管理 Mixin
│   │   ├── canvas_layout.py       # 布局持久化 Mixin
│   │   ├── canvas_menus.py        # 右键菜单 Mixin
│   │   └── items/                 # 画布图形元素
│   │       ├── __init__.py
│   │       ├── node_item.py       # 节点项容器
│   │       ├── node_style.py      # 节点样式系统（方形/圆形）
│   │       ├── edge_item.py       # 连线项（贝塞尔曲线）
│   │       └── anchor_item.py     # 锚点项（输入/输出端口）
│   │
│   ├── panels/                    # 面板组件
│   │   ├── node_list_panel.py     # 节点列表悬浮面板
│   │   ├── property_panel.py      # 配置编辑器、日志查看器、进程控制
│   │   ├── node_group_manager.py  # 节点分组管理
│   │   ├── node_expand_panel.py   # 节点 output.json 查看/编辑
│   │   └── node_monitor.py        # 全局实时日志查看
│   │
│   ├── creators/                  # 节点创建器
│   │   └── node_creator_manager.py # 多语言节点创建管理器
│   │
│   └── docs/                      # UI 文档与示例
│       ├── TOAST_MODULE_README.md
│       └── toast_examples.py
│
├── tools/                         # 节点生成工具
│   ├── README.md
│   ├── python_create_node.py      # Python 节点模板生成器
│   └── rust_create_node.py        # Rust 节点模板生成器
│
└── nodes/                         # 运行时节点目录（由用户项目创建）
    └── [node_name]/               # 单个节点文件夹
        ├── config.json            # 节点配置文件
        ├── main.py                # Python 节点业务逻辑
        ├── listener.py            # Python 节点数据监听
        ├── main.rs                # Rust 节点业务逻辑
        ├── listener.rs            # Rust 节点数据监听
        ├── Cargo.toml             # Rust 项目配置
        ├── start.bat/sh           # 节点启动脚本
        ├── logs/listener.log      # 节点运行日志
        └── venv/                  # Python 独立虚拟环境
```

### 🎯 架构亮点

✅ **模块化设计**：拆分为 Items/Core/Mixin/导出多层架构，职责清晰
✅ **关注点分离**：UI 渲染与业务逻辑隔离，Mixin 模式按职责拆分
✅ **向后兼容**：通过 Facade 模式保持旧导入路径可用
✅ **可扩展**：易于添加自定义节点类型和交互
✅ **可维护**：`main_window.py` 935 行，`canvas_view.py` ~1200 行，代码量可控
✅ **全局日志**：所有 print() 已迁移到 logger，支持控制台和文件双通道输出

---

## 🤝 贡献指南

欢迎贡献代码、报告问题和提出建议！

### 提交 Issue
- **Bug 报告**：描述问题、复现步骤、预期行为、实际行为、环境信息
- **功能请求**：说明需求背景、使用场景、期望效果

### 提交 Pull Request
1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 开启 Pull Request

---

## 📄 开源协议

MIT License © 2026 阿东与守一工作室

---

## 📞 联系方式

- **GitHub**: [https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform](https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform)
- **Email**: 1240543656@qq.com
- **更新日志**: [UPDATE_CN.md](https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform/blob/main/docs/UPDATE_CN.md)

---

> 🌟 如果这个项目对你有帮助，欢迎给个 Star！你的支持是我们前进的动力！

---

## 🎁 近期更新

### 🚀 2026-06-06 更新
- ✅ Toast 通知系统优化：修复黑色底框闪烁，实现平滑渐隐动画
- ✅ 代码健壮性修复：添加导入依赖注释，降低重构风险
- ✅ 文档格式统一：英文版 README 与中文版格式对齐

### 🛠️ 2026-06-05 更新
- ✅ Rust 节点增强：自愈架构、双二进制系统、自动重建功能
- ✅ 节点分组管理：支持拖拽分组、自定义颜色、锁定组保护
- ✅ 动态资源管理器：节点注册表、外部节点挂载、跨项目复用

---

> 📢 欢迎加入 BNOS 社区，一起探索仿生神经网络的无限可能！
