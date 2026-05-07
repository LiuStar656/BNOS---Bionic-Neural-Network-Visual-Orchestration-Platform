# BNOS - 仿生神经网络可视化编排平台

🌍 **语言选择**: [English](README.md) | **中文**

<div align="center">

![BNOS Banner](https://img.shields.io/badge/BNOS-可视化编排-blue?style=for-the-badge&logo=python)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-最新-green?style=for-the-badge&logo=qt)
![License](https://img.shields.io/badge/许可证-MIT-red?style=for-the-badge)

**纯桌面端仿生神经网络可视化编排平台**

*将复杂的分布式神经元系统简化为直观的"拖拽-连线-运行"体验*

[快速开始](#-快速开始) • [核心功能](#-核心功能) • [使用文档](#-使用指南) • [贡献指南](#-贡献指南)

</div>

---

## 🆕 最近更新 (2026-05-07)

### ✨ 新增功能与优化

#### 1. **连线锚点位置修复** 🔧
- **问题**：连线在拖动时显示正确，但连接后锚点位置偏移到状态指示灯上
- **修复**：改用 `sceneBoundingRect().center()` 直接获取锚点几何中心，确保连线始终连接到锚点中心
- **影响文件**：`ui/canvas_widget.py` - `EdgeItem.update_path()` 方法
- **技术改进**：避免手动计算偏移量，提高坐标计算的准确性和可靠性

#### 2. **窗口置顶行为优化** 🪟
- **问题**：节点列表、Toast通知和进度窗口在切换应用后仍然全局置顶，覆盖其他软件窗口
- **修复**：移除所有不必要的 `WindowStaysOnTopHint` 标志，保留 `Qt.WindowType.Tool` 标志
- **影响文件**：
  - `ui/node_list_panel.py` - 节点列表面板
  - `ui/main_window.py` - ToastNotification 和 ProgressFloatingWindow
- **效果**：工具窗口只在应用内部保持层级关系，不会干扰其他应用程序的使用

#### 3. **最佳实践记录** 📚
- 创建记忆知识库，记录 QGraphicsItem 锚点位置计算的最佳实践
- 记录 Qt 工具窗口置顶问题的解决方案
- 为后续开发提供技术参考和规范指导

### 🎯 技术亮点

- **更准确的坐标计算**：使用 `sceneBoundingRect().center()` 替代 `scenePos() + offset`
- **更好的用户体验**：工具窗口遵循标准 Windows 窗口行为，不覆盖其他应用
- **代码质量提升**：通过记忆系统沉淀最佳实践，避免重复踩坑

---

## 📖 项目简介

**BNOS（Bionic Neural Network Program Operating System）** 是一款基于 **PyQt6** 开发的纯桌面端**仿生可视化编排平台**，专为 **BNOS 仿生神经网络节点系统** 提供图形化配置、拖拽式神经回路构建和实时监控能力。

### 🎯 解决的核心痛点

1. **神经突触配置复杂**：手动编辑 JSON 配置文件易出错，路径映射繁琐
2. **神经元关系不直观**：传统方式难以清晰展示神经元间的数据流向和依赖关系
3. **神经信号监控困难**：无法实时查看神经元运行状态、日志输出和错误信息
4. **多环境管理混乱**：多个神经元独立运行环境依赖冲突，启停操作繁琐

**BNOS 解决方案**：通过**神经网络画布**、**自动突触路径配置**、**实时神经信号监控**和**一键启停管理**，彻底解决上述问题。

---

## ✨ 核心功能

### 🎨 神经网络可视化编排

- **无限大脑皮层**：支持鼠标滚轮缩放（0.1x-5.0x）、右键拖动画布、自由布局神经元
- **拖拽交互**：从节点列表拖拽神经元到画布，自动计算最优位置避免重叠
- **智能突触连接**：点击输出锚点 → 输入锚点，自动配置上下游监听路径
- **贝塞尔曲线**：优雅的神经突触路径，清晰展示神经信号流向
- **多选支持**：按住 Ctrl 键多选神经元，批量操作

### 📂 项目管理

- **类 VSCode 模式**：打开文件夹作为项目，自动识别 `nodes/` 目录
- **自动保存与恢复**：持久化窗口状态、分隔条比例、最后打开的项目
- **布局隔离**：每个项目的神经元位置独立保存到 `canvas_layout.json`
- **状态持久化**：重启后完整恢复网络拓扑结构

### 🔧 节点全生命周期管理

- **7种语言支持**：Python、Node.js、Go、Java、C++、Rust、Ruby
- **一键创建**：图形化向导生成标准化节点模板，包含独立虚拟环境和启动脚本
- **智能重命名**：右键菜单触发，同步更新文件夹、配置文件和画布引用
- **独立运行环境**：每个节点拥有独立 venv，避免依赖冲突

### ⚙️ 配置编辑器

- **双击编辑**：双击节点或右键"编辑配置"弹出对话框修改 `config.json`
- **注意力机制规则表**：可视化编辑 Filter 规则，支持增删改查
- **实时验证**：配置修改立即生效，无需重启节点
- **终端集成**：一键打开终端并激活独立运行环境进行调试

### 📊 实时监控

- **状态指示灯**：绿色（运行中）/ 灰色（已停止），直观显示节点状态
- **日志查看器**：实时读取 `listener.log`，支持滚动查看和历史回溯
- **进程管理**：一键启停节点，使用进程组确保彻底清理
- **错误提醒**：启动失败、配置错误等异常情况即时反馈

### 🎯 智能 UI 特性

- **Toast 通知系统**：非侵入式弹窗通知，支持堆叠显示
  - ✅ 无数量上限 - 所有通知都可见
  - ✅ 自动淡入淡出动画（300ms）
  - ✅ 边界检测防止超出屏幕
  - ✅ 固定在右上角，跟随窗口移动
  
- **节点列表面板**：浮动面板固定在左上角
  - ✅ 始终可见，跟随窗口移动
  - ✅ 树形结构支持节点分组
  - ✅ Ctrl/Shift 多选支持
  - ✅ 上下文感知右键菜单
  
- **上下文感知菜单**：根据选中状态动态变化
  - 单个节点：启动、停止、重命名、删除、添加到画布
  - 多个节点：批量启停、批量移动到分组
  - 分组：启动组内所有节点、展开/折叠
  - 空白区域：创建分组、刷新、全选

### 💾 数据持久化

- **防抖保存**：画布变化（移动、连线、缩放）后 500ms 自动保存
- **完整恢复**：重启后恢复位置、连线、缩放比例、滚动位置
- **异常容错**：损坏的 JSON 自动备份为 `.bak` 文件
- **颜色设置**：可自定义节点颜色，按项目持久化

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│              BNOS GUI (PyQt6)                    │
│                                                  │
│  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ 节点列表      │  │     神经网络画布          │ │
│  │ 面板         │  │                          │ │
│  │ (左上角)     │  │  [节点 & 突触]           │ │
│  │              │  │                          │ │
│  └──────────────┘  └──────────────────────────┘ │
│         ↓                    ↓                   │
│  ┌──────────────────────────────────────────┐  │
│  │       本地文件系统 (nodes/)               │  │
│  │  config.json | listener.log | output.json │  │
│  └──────────────────────────────────────────┘  │
│         ↓                    ↓                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ 节点_1   │  │ 节点_2   │  │   节点_N     │ │
│  │(venv)    │  │(venv)    │  │  (venv)      │ │
│  └──────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────────────────────────┘
```

### 模块结构

| 模块 | 文件 | 说明 |
|------|------|------|
| **主入口** | `bnos_gui.py` | 初始化 QApplication，启动主窗口 |
| **主窗口** | `ui/main_window.py` | 整合 UI 组件，管理 AppConfig，处理 Toast 通知 |
| **画布** | `ui/canvas_widget.py` | QGraphicsView 实现节点绘制、拖拽、突触连接 |
| **节点列表** | `ui/node_list_panel.py` | 节点/分组树形视图，上下文菜单，多选支持 |
| **属性面板** | `ui/property_panel.py` | 配置编辑器、日志查看器、进程控制对话框 |
| **分组管理器** | `ui/node_group_manager.py` | 节点分组管理、持久化、批量操作 |
| **节点创建器** | `create_node.py` | 多语言模板生成器，自动配置 venv |

---

## 🚀 快速开始

### 前置要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10/11（主要支持），Linux/macOS（部分支持）
- **磁盘空间**: 500MB+（用于虚拟环境）

### 安装步骤

#### 方式一：从源码运行（推荐开发使用）

```bash
# 1. 克隆仓库
git clone https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform.git
cd "BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main"

# 2. 创建虚拟环境
python -m venv myenv_new

# 3. 激活环境
# Windows:
myenv_new\Scripts\activate
# Linux/macOS:
source myenv_new/bin/activate

# 4. 安装依赖
pip install -r requirements_gui.txt

# 5. 启动应用
python bnos_gui.py
```

#### 方式二：使用启动脚本（Windows）

```powershell
# PowerShell（路径含空格时使用 &）
& ".\start_bnos_gui.bat"

# 或 CMD
start_bnos_gui.bat
```

> **提示**：首次运行会自动检查并安装 PyQt6（如果缺失），请耐心等待。

### 创建第一个项目

1. **创建项目**
   ```
   工具栏 → 新建项目 → 选择文件夹
   ```
   系统自动创建 `nodes/` 目录。

2. **创建节点**
   ```
   工具栏 → 新建节点 → 输入名称 → 选择语言 → 确定
   ```
   自动生成完整结构：`config.json`、`main.py`、`listener.py`、`start.bat`、`venv/`

3. **添加到画布**
   ```
   右键节点列表中的节点 → ➕ 添加到画布
   ```
   节点以自动计算的位置出现。

4. **连接节点**
   - 点击源节点的 **OUT** 锚点（蓝色圆点）
   - 拖拽到目标节点的 **IN** 锚点（绿色圆点）
   - 释放鼠标创建突触（自动配置路径）

5. **启动节点**
   ```
   双击节点 → 点击 ▶️ 启动
   ```
   状态灯变绿表示节点正在运行。

---

## 📋 使用指南

### 节点管理

#### 创建节点
```
工具栏 → 新建节点 → 名称 + 语言 → 确定
```
- 支持语言：Python、Node.js、Go、Java、C++、Rust、Ruby
- 自动生成：配置文件、模板代码、启动脚本、独立 venv

#### 重命名节点
```
右键 → ✏️ 重命名 → 新名称 → 确定
```
- 同步更新：文件夹名称、config 中的 `node_name`、画布显示
- 验证规则：名称唯一，仅允许字母、数字、下划线

#### 删除节点
```
右键 → 🗑️ 删除节点 → 确认
```
- 从磁盘删除整个节点文件夹
- 清理相关突触和路径配置

#### 添加到画布
```
右键 → ➕ 添加到画布
```
- 自动布局：避免与现有节点重叠
- 第一个节点：位置 (200, 150)
- 后续节点：从右下角节点偏移 (50, 50)

### 画布操作

#### 导航
- **平移**：右键拖拽
- **缩放**：鼠标滚轮（0.1x - 5.0x）
- **选择**：左键单击
- **多选**：Ctrl + 单击

#### 节点操作
- **移动**：拖拽节点主体（非锚点）
- **突触更新**：贝塞尔曲线实时跟随
- **自动保存**：拖拽停止 500ms 后保存位置

#### 突触管理
- **创建**：OUT 锚点 → IN 锚点
- **删除**：右键突触 → 删除连接
- **清空全部**：工具栏 → 清空连接

#### 视图控制
- **重置**：工具栏 → 重置视图（1.0x 缩放，居中显示）
- **适应内容**：即将推出

### 节点分组

#### 创建分组
```
右键空白区域 → 创建分组 → 输入名称
```

#### 管理分组
```
右键分组 → 展开/折叠
右键节点 → 移动到分组 → 选择分组
```

#### 批量操作
```
Ctrl + 单击多选节点 → 右键 → 批量启动/停止
右键分组 → 启动组内所有节点
```

### 配置编辑

#### 打开配置对话框
```
方式1：双击画布上的节点
方式2：右键 → ⚙️ 编辑配置
方式3：画布节点右键 → ⚙️ 打开配置
```

#### 配置字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `node_name` | string | 节点唯一标识符 | `"data_processor"` |
| `language` | string | 编程语言 | `"Python"` |
| `listen_upper_file` | string | 上游输出文件路径（自动配置） | `"../node_1/output.json"` |
| `output_type` | string | 输出数据类型 | `"data_result"` |
| `filter` | array | 注意力机制过滤规则 | `[{"key": "type", "value": "task"}]` |

#### 过滤规则编辑
- **添加**：点击"➕ 添加规则"按钮
- **删除**：选中行 → "➖ 删除规则"
- **编辑**：双击单元格直接修改
- **空数组**：不过滤，处理所有任务

#### 快捷操作
- **💻 打开命令行**：启动终端并激活独立运行环境
- **📁 打开文件夹**：用文件资源管理器打开节点目录
- **▶️/⏹️ 启动/停止**：控制节点进程
- **📄 查看日志**：实时显示 `listener.log` 内容

### 项目管理

#### 打开项目
```
工具栏 → 打开项目 → 选择文件夹
```
- 自动识别 `nodes/` 目录
- 加载所有节点到列表
- 恢复画布布局（如果存在）

#### 新建项目
```
工具栏 → 新建项目 → 选择文件夹
```
- 创建空的 `nodes/` 目录
- 清空画布和节点列表

#### 自动恢复
- 启动时自动打开上次关闭的项目
- 恢复窗口状态、分隔条比例
- 恢复画布拓扑和视图状态

---

## 🔧 开发者指南

### 项目结构

```
BNOS/
│
├── bnos_gui.py                    # 主入口
├── create_node.py                 # 节点模板生成器
├── start_bnos_gui.bat             # Windows 启动脚本
├── test_and_start_bnos.bat        # 测试 + 启动脚本
│
├── ui/                            # UI 模块
│   ├── __init__.py
│   ├── main_window.py            # 主窗口 + Toast 系统
│   ├── canvas_widget.py          # 神经画布组件
│   ├── node_list_panel.py        # 带分组的节点列表
│   ├── node_group_manager.py     # 分组管理逻辑
│   └── property_panel.py         # 配置对话框
│
├── nodes/                         # 节点实例
│   └── （用户创建的节点）
│
├── docs/                          # 文档
│   ├── README.md                 # 本文件
│   ├── TOAST_NO_LIMIT.md         # Toast 通知指南
│   ├── NODE_LIST_FOLLOWING_FIX_FINAL.md  # UI 定位
│   └── ...
│
├── app_config.json                # 应用配置（窗口状态）
├── canvas_layout.json             # 当前项目布局
├── color_settings.json            # 节点颜色自定义
└── requirements_gui.txt           # Python 依赖
```

### 扩展开发

#### 添加新语言支持

编辑 `ui/canvas_widget.py` 中的 `detect_language()` 方法：

```python
def detect_language(self, node_path):
    """检测节点编程语言"""
    if os.path.exists(os.path.join(node_path, "main.py")):
        return "Python"
    elif os.path.exists(os.path.join(node_path, "main.js")):
        return "Node.js"
    # 添加新语言...
    elif os.path.exists(os.path.join(node_path, "Main.kt")):
        return "Kotlin"
    return "Unknown"
```

#### 自定义节点样式

修改 `ui/canvas_widget.py` 中的 `NodeItem.__init__()`：

```python
# 节点背景色
self.setBrush(QBrush(QColor("#f8f9fa")))  # 改为其他颜色

# 节点尺寸
super().__init__(x, y, w, h, None)  # w=140, h=80 可调
```

#### 添加工具栏按钮

扩展 `ui/main_window.py` 中的 `init_toolbar()` 方法：

```python
custom_action = QAction("自定义功能", self)
custom_action.triggered.connect(self.custom_function)
toolbar.addAction(custom_action)
```

#### 自定义 Toast 通知

`ui/main_window.py` 中的 Toast 系统：

```python
# 显示通知
self.show_toast("操作成功", "success", duration=3000)

# 类型："info", "success", "warning", "error"
# 时长：毫秒（默认 3000）
```

### 打包发布

#### Windows EXE 打包

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller --onefile --windowed --name="BNOS" bnos_gui.py
```

输出：`dist/BNOS.exe`（约 100MB+，包含 PyQt6）

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

### 🛠️ 自动化工具链
- **CI/CD**：代码拉取 → 编译 → 测试 → 部署
- **监控告警**：指标采集 → 阈值判断 → 通知发送
- **运维脚本**：健康检查 → 日志清理 → 备份归档

### 🔬 科研实验
- **神经网络仿真**：节点 → 突触连接 → 信号传递
- **注意力机制研究**：过滤规则调整 → 任务过滤效果观察
- **涌现行为探索**：多节点协同实验

---

## ⚠️ 已知限制

1. **循环依赖检测**：未实现 A→B→A 循环检测，需用户自行避免
2. **路径敏感性**：移动项目文件夹可能导致绝对路径失效（需重新连线）
3. **并发安全**：不支持多实例同时操作同一项目
4. **性能瓶颈**：节点数 >100 时画布可能卡顿（优化待定）
5. **跨平台**：Linux/macOS 功能部分测试

### 最佳实践

✅ **命名规范**：使用小写字母和下划线（`data_processor`）  
✅ **定期保存**：虽然启用自动保存，但重要操作后建议手动保存（Ctrl+S 计划中）  
✅ **日志监控**：启动节点后及时检查日志确认正常运行  
✅ **备份配置**：定期备份 `nodes/` 目录和 `canvas_layout.json`  
✅ **环境隔离**：不要手动修改节点 `venv/` 目录，使用配置对话框中的"打开命令行"功能  

---

## ❓ 常见问题

### Q: 节点启动失败？
**A**: 检查以下项：
- 虚拟环境是否正确创建（检查 `venv/` 目录）
- 启动脚本是否存在（`start.bat` 或 `start.sh`）
- 日志文件 `logs/listener.log` 中的错误信息
- 尝试在配置对话框中点击"💻 打开命令行"手动启动

### Q: 突触连接后下游节点未收到数据？
**A**: 
- 确认上游节点已启动并正常运行
- 检查 `config.json` 中 `listen_upper_file` 路径是否正确
- 查看下游节点日志确认是否被注意力机制规则过滤
- 验证上游节点的 `output.json` 是否有内容

### Q: 重启后画布为空？
**A**: 
- 确认关闭前节点在画布上（而非仅在节点列表中）
- 检查项目文件夹中是否存在 `canvas_layout.json`
- 查看控制台输出是否有加载错误提示

### Q: 如何重置节点处理状态？
**A**: 
- 手动编辑 `upper_data.json`，删除 `_processed_<节点名>` 字段
- 或在配置对话框中停止节点，删除 `output.json`，然后重新启动

---

## 📄 开源协议

MIT License © 2026 Ahdong&Shouey Team

详见 [LICENSE](LICENSE) 文件。

---

## 👥 贡献指南

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

### 开发规范
- 遵循 PEP 8 代码风格
- 添加必要的注释和文档字符串
- 为新功能编写测试用例（计划中）
- 更新相关文档

---

## 🙏 致谢

- **PyQt6 团队**：提供强大的跨平台 GUI 框架
- **BNOS 神经元系统**：提供核心仿生架构概念
- **开源社区**：众多优秀项目的启发

---

## 📞 联系方式

- **开发团队**：Ahdong&Shouey Team
- **GitHub**: [https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform](https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform)
- **邮箱**：1240543656@qq.com
- **最后更新**：2026-05-03

---

<div align="center">

**⭐ 如果 BNOS 帮助到您，请给它一个 Star 以示支持！**

由 Ahdong&Shouey Team 用 ❤️ 打造

</div>
