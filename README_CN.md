# BNOS - 仿生神经网络可视化编排平台

🌍 Language | 语言选择：**中文** | [English](README_EN.md)（待翻译）

## 📖 项目简介

**BNOS（Bionic Neural Network Program Operating System）** 是一款基于 **PyQt6** 的纯桌面端**类脑可视化编排平台**，专为 **BNOS 仿生神经网络节点系统** 提供图形化配置、拖拽式神经回路构建和实时监控能力。

> **核心理念**：将复杂的分布式神经元系统简化为直观的"拖拽-连线-运行"体验，让每个开发者都能轻松构建类脑架构的应用系统，如同搭建一个具有思维能力的数字大脑。

### 🎯 解决的核心痛点

1. **神经突触配置复杂度高**：手动编辑 JSON 配置文件容易出错，路径映射繁琐
2. **神经元关系不直观**：传统方式难以清晰展示神经元间的数据流向和依赖关系
3. **神经信号监控困难**：无法实时查看神经元运行状态、日志输出和错误信息
4. **多环境管理混乱**：多个神经元的独立运行环境依赖冲突，启动/停止操作繁琐

BNOS 通过**神经网络画布**、**自动突触路径配置**、**实时神经信号监控**和**一键启停**，彻底解决了这些问题。

---

## ✨ 核心特性

### 🎨 神经网络可视化编排
- **无限大脑皮层**：支持鼠标滚轮缩放、右键拖拽平移，自由布局神经元
- **拖拽交互**：从神经元列表拖拽神经元到画布，自动计算最优位置避免重叠
- **智能突触连接**：点击输出锚点 → 输入锚点，自动配置上下游监听路径
- **贝塞尔曲线**：优雅的神经突触路径，清晰展示神经信号流向

### 📂 大脑实例管理
- **仿 VSCode 模式**：打开文件夹即大脑实例，自动识别 `nodes/` 目录
- **自动保存**：最后打开的大脑实例路径、窗口位置、Splitter 比例持久化
- **神经网络布局隔离**：每个大脑实例的神经元位置、突触关系独立保存到 `canvas_layout.json`
- **重启恢复**：关闭程序后重新打开，神经网络状态完全还原

### 🔧 神经元全生命周期管理
- **7 种语言支持**：Python、Node.js、Go、Java、C++、Rust、Ruby
- **一键创建**：图形化向导生成标准化神经元模板，包含独立运行环境和启动脚本
- **智能重命名**：右键菜单触发，同步更新文件夹名、配置文件和神经网络引用
- **神经元独立运行环境**：每个神经元拥有独立 venv，避免依赖冲突

### ⚙️ 配置编辑
- **双击编辑**：双击神经元或右键"编辑配置"，弹出对话框修改 `config.json`
- **注意力机制规则表格**：可视化编辑 Filter 过滤规则，支持增删改查
- **实时验证**：配置修改后立即生效，无需重启神经元
- **命令行集成**：一键打开终端并激活独立运行环境，方便调试

### 📊 实时监控
- **状态指示灯**：绿色（活跃中）/ 灰色（休眠），直观显示神经元状态
- **日志查看器**：实时读取 `listener.log`，支持滚动查看和历史回溯
- **进程管理**：一键启动/停止神经元，使用进程组确保彻底清理
- **错误提示**：启动失败、配置错误等异常情况即时反馈

### 💾 状态持久化
- **防抖保存**：神经元移动、突触变更、视图缩放等操作后 500ms 自动保存
- **完整恢复**：重启后神经元位置、突触关系、缩放比例、滚动位置完全还原
- **异常容错**：JSON 损坏自动备份为 `.bak`，程序不崩溃

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│              BNOS GUI (PyQt6)                    │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 神经元列表│  │ 神经网络画布  │  │ 配置对话框 │ │
│  │ Panel    │  │  Canvas      │  │  Dialog   │ │
│  └──────────┘  └──────────────┘  └───────────┘ │
│         ↓              ↓               ↓        │
│  ┌──────────────────────────────────────────┐  │
│  │       本地文件系统 (nodes/)               │  │
│  │  config.json | listener.log | output.json │  │
│  └──────────────────────────────────────────┘  │
│         ↓              ↓               ↓        │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Neuron_1 │  │  Neuron_2    │  │ Neuron_3  │ │
│  │ (venv)   │  │   (venv)     │  │  (venv)   │ │
│  └──────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────┘
```

### 核心组件

| 模块 | 文件 | 功能 |
|------|------|------|
| **主入口** | `bnos_gui.py` | 初始化 QApplication，启动 MainWindow |
| **主窗口** | `ui/main_window.py` | 整合左侧列表、中间画布、右侧工具栏；管理 AppConfig |
| **神经网络画布** | `ui/canvas_widget.py` | QGraphicsView 实现神经元绘制、拖拽、突触连接、布局保存 |
| **神经元列表** | `ui/node_list_panel.py` | 显示大脑实例内的所有神经元，提供右键菜单（启动、日志、删除、重命名） |
| **配置对话框** | `ui/property_panel.py` | NodeConfigDialog，编辑 config.json，查看日志，启停控制 |
| **神经元工具** | `create_node.py` | 多语言神经元模板生成器，自动创建 venv 和启动脚本 |

---

## 🚀 快速开始

### 前置要求

- **Python**: 3.8+
- **操作系统**: Windows 10/11（主要支持）、Linux/macOS（部分功能待测试）
- **磁盘空间**: 至少 500MB（用于独立运行环境和依赖库）

### 安装步骤

#### 方法一：源码运行（推荐开发使用）

```bash
# 1. 克隆或下载项目
git clone <your-repo-url>
cd "Bionic Neural Network Program Operating System"

# 2. 创建虚拟环境
python -m venv myenv_new

# 3. 激活虚拟环境
# Windows:
myenv_new\Scripts\activate
# Linux/macOS:
source myenv_new/bin/activate

# 4. 安装依赖
pip install pyqt6

# 5. 启动程序
python bnos_gui.py
```

#### 方法二：使用启动脚本（Windows）

```powershell
# PowerShell（路径含空格需用 & 包裹）
& "f:\Bionic Neural Network Program Operating System\start_bnos_gui.bat"

# 或 CMD
start_bnos_gui.bat
```

> **注意**：首次运行时脚本会自动检查并安装 PyQt6，请耐心等待。

### 构建第一个大脑实例

1. **打开大脑实例文件夹**
   - 点击工具栏"打开项目"按钮
   - 选择一个空文件夹（如 `D:/MyBNOSProject`）
   - 系统自动创建 `nodes/` 子目录

2. **创建神经元**
   - 点击工具栏"新建节点"按钮
   - 输入神经元名称（如 `data_processor`）
   - 选择语言（如 Python）
   - 系统自动生成完整神经元结构

3. **添加到神经网络画布**
   - 在左侧神经元列表右键神经元
   - 选择"➕ 添加到画布"
   - 神经元出现在画布中心

4. **创建神经突触**
   - 点击神经元右侧 **OUT** 锚点（蓝色圆点）
   - 拖动到另一个神经元的左侧 **IN** 锚点（绿色圆点）
   - 松开鼠标，自动配置监听路径

5. **激活神经元**
   - 双击神经元打开配置对话框
   - 点击"▶️ 启动"按钮
   - 状态灯变绿，表示神经元正在活跃运行

---

## 📋 使用指南

### 神经元管理

#### 创建神经元
```
工具栏 → 新建节点 → 输入名称 → 选择语言 → 确定
```
- 支持的语言：Python、Node.js、Go、Java、C++、Rust、Ruby
- 自动生成：`config.json`、`listener.py`、`main.py`、`start.bat/sh`、`venv/`

#### 重命名神经元
```
神经元列表右键 → ✏️ 重命名 → 输入新名称 → 确定
```
- 同步更新：文件夹名、`config.json` 中的 `node_name`、神经网络画布显示
- 校验规则：名称唯一、仅允许字母数字下划线

#### 删除神经元
```
神经元列表右键 → 🗑️ 删除节点 → 确认
```
- 物理删除：整个神经元文件夹从磁盘移除
- 清理突触：自动删除相关神经突触，清除上下游 `listen_upper_file`

#### 添加到神经网络画布
```
神经元列表右键 → ➕ 添加到画布
```
- 有序布局：自动计算位置，避免与现有神经元重叠
- 首次添加：放置在 (200, 150)
- 后续添加：在最右下角神经元基础上偏移 (50, 50)

### 神经网络画布操作

#### 基本交互
- **平移**：右键按住拖拽
- **缩放**：鼠标滚轮（范围 0.1x - 5.0x）
- **选中**：左键点击神经元
- **多选**：按住 Ctrl 点击多个神经元

#### 神经元拖拽
- 左键按住神经元主体区域（非锚点）即可拖动
- 神经突触实时跟随神经元移动（贝塞尔曲线动态更新）
- 停止拖动 500ms 后自动保存位置

#### 神经突触操作
- **创建**：点击源神经元 OUT 锚点 → 拖动到目标神经元 IN 锚点
- **删除**：右键点击神经突触 → 选择"删除连线"
- **清空**：工具栏 → "清空连线"（会清除所有 listen_upper_file 配置）

#### 视图控制
- **重置视图**：工具栏 → "重置视图"（恢复到 1.0x 缩放，居中显示）
- **适应内容**：待实现（自动调整缩放以显示所有神经元）

### 配置编辑

#### 打开配置对话框
```
方式1：双击神经网络画布上的神经元
方式2：神经元列表右键 → ⚙️ 编辑配置
方式3：画布神经元右键 → ⚙️ 打开配置
```

#### 配置项说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `node_name` | string | 神经元唯一标识 | `"data_processor"` |
| `language` | string | 编程语言 | `"Python"` |
| `listen_upper_file` | string | 上游输出文件路径（自动配置） | `"../node_1/output.json"` |
| `output_type` | string | 输出数据类型 | `"data_result"` |
| `filter` | array | 注意力机制过滤规则（表格形式） | `[{"key": "type", "value": "task"}]` |

#### 注意力机制规则编辑
- **添加规则**：点击"➕ 添加规则"按钮
- **删除规则**：选中行后点击"➖ 删除规则"
- **编辑规则**：直接双击单元格修改
- **空规则**：表示不过滤，处理所有任务

#### 快捷操作
- **💻 打开命令行**：启动终端并激活独立运行环境（需先启动神经元）
- **📁 打开文件夹**：用资源管理器打开神经元目录
- **▶️ 启动 / ⏹️ 停止**：控制神经元进程
- **📄 查看日志**：实时显示 `listener.log` 内容

### 大脑实例管理

#### 打开大脑实例
```
工具栏 → 打开项目 → 选择文件夹
```
- 自动识别 `nodes/` 目录
- 加载所有神经元到左侧列表
- 恢复神经网络布局（如果存在 `canvas_layout.json`）

#### 新建大脑实例
```
工具栏 → 新建项目 → 选择文件夹
```
- 创建空的 `nodes/` 目录
- 清空神经网络画布和神经元列表

#### 自动恢复
- 程序启动时自动打开上次关闭前的大脑实例
- 恢复窗口位置、大小、Splitter 比例
- 恢复神经网络神经元位置、突触关系、视图状态

---

## 🔧 开发指南

### 项目结构

```
Bionic Neural Network Program Operating System/
│
├── bnos_gui.py                    # 主入口
├── create_node.py                 # 神经元模板生成器
├── start_bnos_gui.bat             # Windows 启动脚本
├── package_bnos.bat               # Windows 打包脚本
│
├── ui/                            # UI 模块
│   ├── __init__.py
│   ├── main_window.py            # 主窗口 + AppConfig
│   ├── canvas_widget.py          # 神经网络画布组件
│   ├── node_list_panel.py        # 神经元列表面板
│   └── property_panel.py         # 配置对话框
│
├── nodes/                         # 示例神经元（可删除）
│   ├── node_test/
│   └── node_llama_cpp_engine/
│
├── docs/                          # 文档
│   ├── README.md                 # 本文件
│   ├── QUICK_START.md
│   └── ...
│
├── app_config.json                # 应用级配置（窗口状态、最后大脑实例）
├── canvas_layout.json             # 当前大脑实例神经网络布局（自动生成）
└── myenv_new/                     # 虚拟环境（gitignore）
```

### 扩展开发

#### 添加新语言支持
编辑 `ui/canvas_widget.py` 中的 `detect_language()` 方法：

```python
def detect_language(self, node_path):
    """检测神经元语言"""
    if os.path.exists(os.path.join(node_path, "main.py")):
        return "Python"
    elif os.path.exists(os.path.join(node_path, "main.js")):
        return "Node.js"
    # 添加新语言...
    elif os.path.exists(os.path.join(node_path, "Main.kt")):
        return "Kotlin"
    return "Unknown"
```

#### 自定义神经元样式
修改 `ui/canvas_widget.py` 中 `NodeItem.__init__()` 的颜色和尺寸：

```python
# 神经元背景色
self.setBrush(QBrush(QColor("#f8f9fa")))  # 改为其他颜色

# 神经元尺寸
super().__init__(x, y, w, h, None)  # w=140, h=80 可调整
```

#### 添加新的工具栏按钮
在 `ui/main_window.py` 的 `init_toolbar()` 方法中添加：

```python
custom_action = QAction("自定义功能", self)
custom_action.triggered.connect(self.custom_function)
toolbar.addAction(custom_action)
```

### 打包发布

#### Windows EXE 打包

```bash
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 执行打包脚本
package_bnos.bat

# 或使用命令
pyinstaller --onefile --windowed --name="BNOS节点编排平台" bnos_gui.py
```

生成的 `dist/BNOS节点编排平台.exe` 即可分发。

> **注意**：打包后的 exe 体积较大（约 100MB+），因为包含了 PyQt6 库。

---

## 🎯 适用场景

BNOS 可视化平台适用于以下场景：

### 🤖 AI 智能体构建
- **感知神经元**：图像识别、语音转录、传感器数据采集
- **推理神经元**：LLM 调用、逻辑判断、决策生成
- **执行神经元**：API 调用、数据库操作、文件写入
- **编排方式**：拖拽连线形成完整的 Agent 工作流

### 📊 数据流水线
- **ETL 流程**：数据清洗 → 转换 → 入库
- **实时处理**：日志采集 → 分析 → 告警
- **批量任务**：文件扫描 → 处理 → 归档

### 🌐 微服务组件
- **API 网关**：请求路由 → 鉴权 → 转发
- **后台任务**：定时调度 → 执行 → 结果通知
- **事件驱动**：消息监听 → 业务处理 → 状态更新

### 🛠️ 自动化工具链
- **CI/CD**：代码拉取 → 编译 → 测试 → 部署
- **监控告警**：指标采集 → 阈值判断 → 通知发送
- **运维脚本**：健康检查 → 日志清理 → 备份归档

### 🔬 类脑计算实验
- **神经网络模拟**：神经元 → 突触连线 → 信号传递
- **注意力机制研究**：Filter 规则调整 → 任务筛选效果观察
- **分布式协作**：多神经元协同 →  emergent behavior 探索

---

## ⚠️ 注意事项

### 已知限制

1. **循环依赖检测**：目前未实现 A→B→A 的循环检测，用户需自行避免
2. **跨大脑实例移动**：移动大脑实例文件夹后，绝对路径可能失效，需重新连线
3. **并发安全**：不支持多实例同时操作同一大脑实例
4. **大规模神经网络性能**：神经元数量 >100 时，画布渲染可能卡顿（待优化）

### 最佳实践

1. **命名规范**：神经元名称使用小写字母和下划线（如 `data_processor`）
2. **定期保存**：虽然自动保存，但重要操作后建议手动保存（Ctrl+S，待实现）
3. **日志监控**：启动神经元后及时查看日志，确认运行正常
4. **备份配置**：重要大脑实例定期备份 `nodes/` 目录和 `canvas_layout.json`
5. **环境隔离**：不要手动修改神经元的 `venv/` 目录，使用配置对话框的"打开命令行"功能

### 常见问题

#### Q: 神经元启动失败？
**A**: 检查以下几点：
- 独立运行环境是否正确创建（查看 `venv/` 目录）
- 启动脚本是否存在（`start.bat` 或 `start.sh`）
- 查看日志文件 `logs/listener.log` 中的错误信息
- 尝试在配置对话框中点击"💻 打开命令行"手动启动

#### Q: 神经突触连接后下游神经元没有收到数据？
**A**: 
- 确认上游神经元已启动并正常运行
- 检查 `config.json` 中的 `listen_upper_file` 路径是否正确
- 查看下游神经元日志，确认是否被注意力机制规则过滤
- 验证上游神经元的 `output.json` 是否有内容

#### Q: 重启后神经网络画布为空？
**A**: 
- 确认关闭前神经元已在画布上（不是仅在神经元列表中）
- 检查大脑实例文件夹下是否存在 `canvas_layout.json`
- 查看控制台输出，确认加载时是否有错误提示

#### Q: 如何重置神经元处理状态？
**A**: 
- 手动编辑 `upper_data.json`，删除 `_processed_<node_name>` 字段
- 或在配置对话框中停止神经元，删除 `output.json`，再重新启动

---

## 📄 许可证

本项目采用 **MIT License** 开源协议。

```
MIT License

Copyright (c) 2026 Ahdong&Shouey Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👥 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 提交 Issue
- **Bug 报告**：描述问题、复现步骤、预期行为、实际行为、环境信息
- **功能请求**：说明需求背景、使用场景、期望效果

### 提交 Pull Request
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发规范
- 遵循 PEP 8 代码风格
- 添加必要的注释和文档字符串
- 确保新功能有相应的测试用例（待完善）
- 更新相关文档

---

## 🙏 致谢

- **PyQt6 团队**：提供强大的跨平台 GUI 框架
- **BNOS 神经元系统**：提供核心的类脑架构理念
- **开源社区**：众多优秀项目的启发

---

## 📞 联系方式

- **开发团队**：阿东与守一团队（Ahdong&Shouey Team）
- **GitHub**：[(https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform)]
- **邮箱**：[1240543656@qq.com]
- **最后更新**：2026-04-27

---

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！**
