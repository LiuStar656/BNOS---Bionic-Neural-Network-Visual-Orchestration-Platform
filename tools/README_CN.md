  # BNOS - 仿生神经网络节点操作系统

  🌍 Language | 语言选择：[中文](README_CN.md) | [English](README.md)

  ## 📋 更新日志

  ### 2026-05-18 - 增强节点创建与启动脚本

  #### ✨ 新功能

  **1. Rust 节点增强**
  - ✅ **双可执行文件检测**: `start.bat` 和 `start.sh` 现在分别检测主程序和监听器可执行文件
  - ✅ **智能编译**: 仅在任一可执行文件缺失时自动触发 `cargo build --release`
  - ✅ **直接运行**: 当两个可执行文件都存在时跳过编译，直接启动监听器
  - ✅ **延迟扩展支持**: Windows 批处理脚本现在使用 `setlocal enabledelayedexpansion` 确保变量正确处理
  - ✅ **多级配置查找**: `main.rs` 和 `listener.rs` 都在三个位置搜索 `config.json`（target/release → target → 项目根目录）
  - ✅ **完整路径调用**: 监听器使用完整路径调用主程序，避免工作目录问题
  - ✅ **自动生成 output.json**: 新节点现在包含初始的 `output.json` 文件，内容为 `{"code":0,"data":null}`

  **2. Python 节点增强**
  - ✅ **自动生成 requirements.txt**: 新节点包含模板 `requirements.txt` 文件，带有注释示例
  - ✅ **跨平台依赖管理**: Windows (`start.bat`) 和 Linux/macOS (`start.sh`) 现在都支持自动依赖检测和安装
  - ✅ **UTF-8 编码支持**: 修复了 Windows 上读取 `requirements.txt` 时的编码问题（之前会出现 GBK 错误）
  - ✅ **智能依赖检测**: 在检查/安装依赖前过滤掉注释行和空行
  - ✅ **优雅降级**: 安装失败时显示警告但不会阻止节点启动

  #### 🔧 Bug 修复

  **Rust 节点:**
  - 修复了 Cargo.toml 包名问题（从 `"1"` 改为正确的节点名称）
  - 修复了启动脚本中的二进制文件名引用
  - 修复了监听器和主程序中的配置文件路径解析
  - 移除了导致编译器警告的未使用导入

  **Python 节点:**
  - 修复了依赖检测逻辑中的 UTF-8 编码处理
  - 确保 Windows 和 Linux/macOS 启动脚本行为一致

  #### 📝 文档更新

  - 更新了节点创建脚本，添加了全面的错误处理
  - 在生成的 `requirements.txt` 模板中添加了清晰的使用说明
  - 改进了启动脚本中的日志消息，添加了表情符号指示器

  ---

  ## 📖 项目简介

  BNOS（Bionic Neural Network Operating System）是基于仿生神经网络的通用模块化执行引擎。系统采用类脑架构，通过组合多个协同工作的节点来构建各种应用系统，可用于插件化系统、自动化流水线、任务调度、边缘计算、微服务等场景，同时也可用于构建 AI 智能体。每个节点是系统中的最小执行单元（类似大脑中的神经元或功能模块），多个节点通过 JSON 文件进行通信和协作，共同实现复杂的业务逻辑和处理能力。

  ## 🧬 设计理念

  本系统借鉴生物神经网络的核心特征，映射到通用模块化执行场景：

  - **功能节点（神经元）**: 每个节点如同大脑中的神经元或功能模块，负责特定的子任务处理
  - **节点协同（神经回路）**: 多个节点通过数据文件建立连接，形成系统的协作网络
  - **注意力机制**: 基于过滤规则的任务筛选，模拟节点的注意力聚焦机制
  - **防重复处理**: 自动标记已处理任务，避免节点重复执行相同操作（提升效率）
  - **模块化设计**: 通过组合不同功能的节点，灵活构建具有复杂能力的各类应用系统

  ## ⚡ 高并发设计理念

  BNOS 不要求所有节点都支持高并发，而是采用类脑架构：

  1. **高性能节点独立实现**: 高并发、高性能需求（如 LLM 推理、大规模计算、高频访问）仅在单个专业节点内部实现
  2. **技术栈自由选择**: 该节点可自由使用多线程、多进程、协程、第三方引擎等技术，不受框架限制
  3. **轻量节点保持稳定**: 其他节点仅负责任务感知、注意力过滤、决策调度、结果存储，保持轻量稳定
  4. **极简通信机制**: 节点间通过文件实现极简通信，避免分布式系统的复杂性
  5. **多语言支持**: 可根据性能需求使用不同语言实现节点（Python、Rust、C++等），所有节点通过统一的 JSON 协议通信

  这种架构让系统既简单稳定，又能在关键节点实现极致性能。

  ## 🏗️ 系统架构

  ```
  上层任务 (upper_data.json)
      ↓
  监听器 (listener.py) ← 注意力过滤（节点注意力机制）
      ↓
  节点处理逻辑 (main.py) ← 功能单元执行
      ↓
  输出给下一个节点 (output.json) ← 节点间通信
  ```

  ### 核心组件

  - **listener.py / listener.rs**: 节点监听器，负责监听上层任务、执行注意力过滤、调用节点处理逻辑
  - **main.py / main.rs**: 节点处理逻辑，实现智能体内部特定功能单元的执行逻辑
  - **config.json**: 节点配置文件，定义节点名称、监听路径、注意力规则等
  - **packet.py / packet.rs**: 数据包结构定义文件（节点间通信格式）
  - **python_create_node.py / rust_create_node.py**: 节点创建工具，自动生成新节点的完整结构（Python/Rust）
  - **多语言支持**: 支持 Python、Rust 等多种语言实现，所有节点使用统一的 JSON 通信协议

  ## ✨ 主要特性

  - 🔒 **环境隔离**: 每个节点拥有独立的 Python 虚拟环境（venv），确保系统内各功能单元的独立性
  - 🎯 **注意力机制**: 支持基于字段值的精确任务过滤，节点只关注符合条件的任务（模拟注意力聚焦）
  - 📝 **防重复处理**: 自动标记已处理任务，避免节点重复执行相同操作（提升系统效率）
  - 📊 **日志系统**: 完善的节点活动日志记录，支持文件和控制台双输出，便于追踪系统行为
  - 🚀 **模块化搭建**: 提供节点生成器，一键创建标准化功能节点，快速组合构建各类应用系统
  - 💻 **跨平台**: 支持 Windows 和 Linux/macOS 系统
  - 🌐 **通用流程编排**: 支持通过组合多个节点构建复杂的工作流、数据流水线、微服务组件等
  - 🔌 **可插拔设计**: 节点逻辑独立封装，可轻松替换、升级或添加新的功能节点，灵活调整系统能力，适用于插件系统、自动化工具链等场景

  ## 📁 项目结构

  ```
  bnos/
  ├── data/
  │   └── upper_data.json          # 上层任务数据文件（任务源）
  ├── node_python_demo/             # Python 示例节点（推荐快速开发）
  │   ├── venv/                     # 独立虚拟环境
  │   ├── logs/                     # 日志目录
  │   │   └── listener.log         # 节点活动日志
  │   ├── config.json              # 节点配置（注意力参数）
  │   ├── listener.py              # 监听器程序（任务接收器）
  │   ├── main.py                  # 节点处理逻辑（功能单元执行）
  │   ├── packet.py                # 数据包定义（通信格式）
  │   ├── output.json              # 输出数据文件（节点输出）
  │   └── start.bat                # Windows 启动脚本
  ├── node_rust_demo/               # Rust 示例节点（推荐高性能场景）
  │   ├── src/                      # Rust 源代码
  │   │   ├── main.rs              # 主处理逻辑
  │   │   ├── listener.rs          # 监听器和自愈逻辑
  │   │   └── packet.rs            # 数据包定义
  │   ├── Cargo.toml               # Rust 项目配置
  │   ├── logs/                     # 日志目录
  │   │   └── listener.log         # 节点活动日志
  │   ├── config.json              # 节点配置（注意力参数）
  │   ├── output.json              # 输出数据文件（节点输出）
  │   ├── start.bat                # Windows 启动脚本
  │   └── start.sh                 # Linux/macOS 启动脚本
  ├── python_create_node.py        # Python 节点创建工具
  ├── rust_create_node.py          # Rust 节点创建工具
  └── README.md                    # 项目说明文档
  ```

  ## 🚀 快速开始

  ### 前置要求

  **Python 节点：**
  - Python 3.6+
  - pip（用于创建虚拟环境）

  **Rust 节点：**
  - Rust 工具链 (rustc, cargo)
  - 验证安装: `rustc --version` 和 `cargo --version`

  ### 创建功能节点

  #### 方案一：Python 节点（推荐快速开发）

  1. 在项目根目录运行节点创建工具：

  ```bash
  python python_create_node.py
  ```

  2. 输入节点名称（如 data_processor、api_handler、task_scheduler），系统将自动生成：
    - 完整的节点目录结构
    - 独立的 Python 虚拟环境
    - 标准配置文件
    - 启动脚本（Windows: `start.bat` / Linux: `start.sh`）

  #### 方案二：Rust 节点（推荐高性能场景）

  1. 运行 Rust 节点创建工具：

  ```bash
  python rust_create_node.py
  ```

  2. 输入节点名称，系统将自动生成：
    - 完整的 Rust 项目结构
    - Cargo.toml 配置文件
    - 源代码模板（main.rs, listener.rs, packet.rs）
    - 具备自动编译能力的启动脚本

  ### 配置节点注意力

  编辑 `config.json` 文件：

  ```json
  {
    "node_name": "data_processor",           // 节点名称（功能单元ID）
    "listen_upper_file": "../data/upper_data.json",  // 监听的上层任务文件路径（输入通道）
    "output_file": "./output.json",     // 输出文件路径（输出通道）
    "filter": {                         // 注意力过滤规则（注意力机制）
      "type": "data_task"
    },
    "output_type": "data_result"         // 输出数据类型标识
  }
  ```

  ### 编写节点处理逻辑

  **Python 节点：** 在 `main.py` 中实现 `process()` 函数：

  ```python
  def process(data):
      """处理输入任务并返回结果（功能单元执行）"""
      value = data.get("data", 0)
      return float(value) + 1
  ```

  **Rust 节点：** 在 `src/main.rs` 中实现 `process()` 函数：

  ```rust
  fn process(data: &serde_json::Value) -> Option<serde_json::Value> {
      // 在此实现你的业务逻辑
      let input = data.get("data")?;
      
      // 进行处理...
      let result = /* 你的处理逻辑 */;
      
      Some(result)
  }
  ```

  ### 启动功能节点

  **Python 节点：**

  Windows:
  ```bash
  cd node_python_demo
  start.bat
  ```

  Linux/macOS:
  ```bash
  cd node_python_demo
  chmod +x start.sh
  ./start.sh
  ```

  **Rust 节点：**

  Windows:
  ```bash
  cd node_rust_demo
  start.bat
  ```

  Linux/macOS:
  ```bash
  cd node_rust_demo
  chmod +x start.sh
  ./start.sh
  ```

  Rust 节点会在首次运行或检测到源代码更改时自动构建项目。

  ## 📋 配置说明

  ### config.json 配置项

  | 字段 | 类型 | 说明 | 示例 |
  |------|------|------|------|
  | `node_name` | string | 节点唯一标识符（功能单元ID） | `"data_processor"` |
  | `listen_upper_file` | string | 上层任务文件路径（相对或绝对路径，输入通道） | `"../data/upper_data.json"` |
  | `output_file` | string | 本节点输出文件路径（输出通道） | `"./output.json"` |
  | `filter` | object | 注意力过滤规则，键值对匹配（注意力机制） | `{"type": "data_task"}` |
  | `output_type` | string | 输出数据类型标识（结果类型） | `"data_result"` |

  ### 注意力过滤机制（节点注意力）

  - 如果 `filter` 为空对象 `{}`，节点将处理所有任务（广泛注意力）
  - 如果配置了过滤规则，只有当任务包含所有指定字段且值完全匹配时才会被处理（聚焦注意力）
  - 示例：`{"type": "data_task"}` 表示节点只关注 `type` 字段值为 `"data_task"` 的任务

  ### 数据包格式（节点间通信）

  **输入任务包** (`upper_data.json`):
  ```
  {
    "type": "data_task",
    "data": 153,
    "_processed_data_processor": true
  }
  ```

  **输出结果包** (`output.json`):
  ```
  {
    "code": 0,
    "type": "data_result",
    "data": 154
  }
  ```

  ## 🔧 开发指南

  ### 添加依赖

  **Python 节点：** 在节点的 `requirements.txt` 文件中添加所需的 Python 包：

  ```
  requests==2.28.0
  numpy==1.23.0
  openai==1.0.0
  ```

  然后激活虚拟环境并安装：

  ```bash
  # Windows
  venv\Scripts\activate
  pip install -r requirements.txt

  # Linux/macOS
  source venv/bin/activate
  pip install -r requirements.txt
  ```

  **Rust 节点：** 在 `Cargo.toml` 中添加依赖：

  ```toml
  [dependencies]
  serde = { version = "1.0", features = ["derive"] }
  serde_json = "1.0"
  chrono = "0.4"
  # 添加其他依赖...
  ```

  然后构建项目：

  ```bash
  cargo build --release
  ```

  ### 调试技巧

  1. **查看日志**: 检查 `logs/listener.log` 文件了解节点运行状态（智能体内部活动监测）
  2. **监控数据**: 观察 `upper_data.json` 和 `output.json` 的变化（智能体内部信号流追踪）
  3. **测试注意力**: 修改 `config.json` 中的 `filter` 规则验证任务筛选（注意力调整）

  ### 日志格式

  ```
  [2026-04-24 17:26:11] [INFO] ✅ 这是我的任务，开始处理
  [2026-04-24 17:26:11] [INFO] ✅ 处理完成 | 已标记: _processed_perception_node
  [2026-04-24 17:26:12] [ERROR] ❌ 任务包格式错误
  ```

  ## 🔄 工作流程（节点协同处理）

  1. **任务接收**: `listener.py` 持续监控 `upper_data.json` 文件（节点接收来自上游节点的任务）
  2. **注意力过滤**: 根据 `config.json` 中的 `filter` 规则判断是否处理该任务（节点注意力聚焦）
  3. **防重复检查**: 检查任务是否已被当前节点处理过（通过 `_processed_<node_name>` 标记，避免重复执行）
  4. **节点处理**: 调用 `main.py` 执行节点功能逻辑，传入 JSON 任务作为命令行参数（功能单元执行）
  5. **输出结果**: 将处理结果写入 `output.json`（节点输出，传递给下游节点）
  6. **标记完成**: 在 `upper_data.json` 中添加处理标记，防止重复处理（任务完成标记）

  ## ⚠️ 注意事项

  1. **JSON 格式**: 确保所有 JSON 文件格式正确，否则会导致解析错误
  2. **文件权限**: 确保节点有读写数据文件的权限
  3. **虚拟环境**: 每个节点必须使用独立的虚拟环境，避免依赖冲突
  4. **并发安全**: 当前版本不支持多实例同时运行同一节点
  5. **路径配置**: 配置文件中的路径可以是相对路径或绝对路径
  6. **系统设计**: 设计系统时，合理组合多个节点形成完整的处理能力

  ## 🎯 适用场景

  BNOS 作为通用模块化执行引擎，适用于以下场景：

  - 🔌 **模块化插件系统**: 通过节点组合构建可扩展的插件架构
  - 📊 **数据流水线**: 构建数据处理、转换、分析的自动化流水线
  - ⏰ **任务调度**: 实现复杂任务的分布式调度和执行
  - 🌐 **边缘计算**: 在边缘设备上部署轻量级节点网络
  - 🏗️ **微服务**: 构建基于节点的微服务组件和API网关
  - 🛠️ **自动化工具链**: 创建CI/CD、测试、部署等自动化工具链
  - 🤖 **AI智能体**: 构建多节点协作的AI智能体系统（感知、推理、决策节点等）
  - 🧠 **类脑计算实验**: 进行类脑计算、神经网络模拟等研究实验
  - ⚡ **高性能计算**: 使用 Rust 节点处理需要极致性能的计算密集型任务

  ## 🐛 常见问题

  ### Q: 节点没有处理任务？
  A: 检查以下几点：
  - 确认 `filter` 规则是否正确配置（注意力设置）
  - 查看 `logs/listener.log` 是否有过滤日志
  - 验证 `upper_data.json` 文件格式是否正确

  ### Q: 如何重置节点处理状态？
  A: 手动删除 `upper_data.json` 中的 `_processed_<node_name>` 字段（清除节点记忆）

  ### Q: 虚拟环境创建失败？
  A: 确保已安装 Python 并且 `python -m venv` 命令可用

  ### Q: 如何构建完整的应用系统？
  A: 通过创建多个功能节点（如数据处理节点、业务逻辑节点、API节点等），配置它们的 `listen_upper_file` 和 `output_file` 形成协同工作流，共同构成一个完整的应用系统。也可用于构建AI智能体，通过组合感知节点、推理节点、决策节点等实现智能体功能。

  ### Q: 如何选择 Python 节点还是 Rust 节点？
  A: 
  - **选择 Python** 当：需要快速原型开发、易于调试、需要丰富的生态库、性能要求适中
  - **选择 Rust** 当：需要极致性能、内存安全至关重要、低延迟处理、生产环境稳定性要求高

  ### Q: 可以在同一系统中混合使用 Python 和 Rust 节点吗？
  A: 可以！所有节点无论使用何种语言实现，都通过标准化的 JSON 文件进行通信。你可以在同一个工作流中自由组合 Python 和 Rust 节点。

  ## 📋 更新日志

  ### 2026-05-18 - 增强节点创建与启动脚本

  #### ✨ 新功能

  **1. Rust 节点增强**
  - ✅ **双可执行文件检测**: `start.bat` 和 `start.sh` 现在分别检测主程序和监听器可执行文件
  - ✅ **智能编译**: 仅在任一可执行文件缺失时自动触发 `cargo build --release`
  - ✅ **直接运行**: 当两个可执行文件都存在时跳过编译，直接启动监听器
  - ✅ **延迟扩展支持**: Windows 批处理脚本现在使用 `setlocal enabledelayedexpansion` 确保变量正确处理
  - ✅ **多级配置查找**: `main.rs` 和 `listener.rs` 都在三个位置搜索 `config.json`（target/release → target → 项目根目录）
  - ✅ **完整路径调用**: 监听器使用完整路径调用主程序，避免工作目录问题
  - ✅ **自动生成 output.json**: 新节点现在包含初始的 `output.json` 文件，内容为 `{"code":0,"data":null}`

  **2. Python 节点增强**
  - ✅ **自动生成 requirements.txt**: 新节点包含模板 `requirements.txt` 文件，带有注释示例
  - ✅ **跨平台依赖管理**: Windows (`start.bat`) 和 Linux/macOS (`start.sh`) 现在都支持自动依赖检测和安装
  - ✅ **UTF-8 编码支持**: 修复了 Windows 上读取 `requirements.txt` 时的编码问题（之前会出现 GBK 错误）
  - ✅ **智能依赖检测**: 在检查/安装依赖前过滤掉注释行和空行
  - ✅ **优雅降级**: 安装失败时显示警告但不会阻止节点启动

  #### 🔧 Bug 修复

  **Rust 节点:**
  - 修复了 Cargo.toml 包名问题（从 `"1"` 改为正确的节点名称）
  - 修复了启动脚本中的二进制文件名引用
  - 修复了监听器和主程序中的配置文件路径解析
  - 移除了导致编译器警告的未使用导入

  **Python 节点:**
  - 修复了依赖检测逻辑中的 UTF-8 编码处理
  - 确保 Windows 和 Linux/macOS 启动脚本行为一致

  #### 📝 文档更新

  - 更新了节点创建脚本，添加了全面的错误处理
  - 在生成的 `requirements.txt` 模板中添加了清晰的使用说明
  - 改进了启动脚本中的日志消息，添加了表情符号指示器

  ---

  ---

### 2026-05-21 - 后台运行与进程健康检测

#### ✨ 新功能

- **后台进程检测**: GUI 通过 `.pid` 文件检测上一会话中后台运行的节点
- **进程健康检测**: 每 3 秒轮询运行中进程；崩溃节点自动更新为停止状态
- **启动脚本改造**: `start.bat` 和 `start.sh` 全面支持 `--no-pause` 参数、`start /b` / `nohup &` 后台启动、自动写 `.pid` 文件
- **节点生成器开发准则**: 新增标准开发指南，用于创建新语言节点生成器 ([节点生成器开发准则.md](节点生成器开发准则.md) | [Node_Generator_Guidelines_EN.md](Node_Generator_Guidelines_EN.md))

#### 🔧 Bug 修复

- 修复 `subprocess.PIPE` 缓冲区死锁，改为 `DEVNULL`
- 修复启动脚本前台阻塞问题
- 修复跨会话进程状态丢失

  ---

  ## 📄 许可证

  本项目采用 MIT License 开源协议。

  ## 👥 贡献

  如需添加新功能或修复问题，欢迎提交 Pull Request 或 Issue。

  ---

  ---

  ### 开发与设计
  由 **阿东与守一团队（Ahdong&Shouey Team）** 开发设计
  最后更新：2026-05-21
