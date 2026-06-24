# BNOS - Bionic Neural Network Operating System

🌍 Language | 语言选择：[中文](README_CN.md) | [English](README.md)

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [节点开发规范](节点开发规范.md) (CN) | **Node Developer Guide** — Directory structure, config.json, listener, main logic, startup scripts, communication protocol |
| [config_json 开发规范](config_json_开发规范.md) (CN) | config.json parameter widgets & input/output port detailed configuration (11 widget types) |
| [节点生成器开发准则](节点生成器开发准则.md) (CN) | Node generator development guidelines for new languages (Go/Java/C++ etc.) |
| [Node_Generator_Guidelines_EN.md](Node_Generator_Guidelines_EN.md) | Same as above, English version |

## 📋 Changelog

### 2026-05-18 - Enhanced Node Creation & Startup Scripts

#### ✨ New Features

**1. Rust Node Enhancements**
- ✅ **Dual Executable Detection**: `start.bat` and `start.sh` now detect both main program and listener executables separately
- ✅ **Smart Compilation**: Automatically triggers `cargo build --release` only when either executable is missing
- ✅ **Direct Execution**: Skips compilation when both executables exist, directly launching the listener
- ✅ **Delayed Expansion Support**: Windows batch scripts now use `setlocal enabledelayedexpansion` for proper variable handling
- ✅ **Multi-Level Config Search**: Both `main.rs` and `listener.rs` search for `config.json` in three locations (target/release → target → project root)
- ✅ **Full Path Invocation**: Listener calls main program using complete path to avoid working directory issues
- ✅ **Auto-generated output.json**: New nodes now include an initial `output.json` file with `{"code":0,"data":null}`

**2. Python Node Enhancements**
- ✅ **Auto-generated requirements.txt**: New nodes include a template `requirements.txt` with commented examples
- ✅ **Cross-Platform Dependency Management**: Both Windows (`start.bat`) and Linux/macOS (`start.sh`) now support automatic dependency detection and installation
- ✅ **UTF-8 Encoding Support**: Fixed encoding issues when reading `requirements.txt` on Windows (previously failed with GBK errors)
- ✅ **Smart Dependency Detection**: Filters out comments and empty lines before checking/installing dependencies
- ✅ **Graceful Fallback**: Installation failures show warnings but don't prevent node startup

#### 🔧 Bug Fixes

**Rust Nodes:**
- Fixed Cargo.toml package naming issue (changed from `"1"` to proper node name)
- Fixed binary filename references in startup scripts
- Fixed configuration file path resolution in both listener and main programs
- Removed unused imports causing compiler warnings

**Python Nodes:**
- Fixed UTF-8 encoding handling in dependency detection logic
- Ensured consistent behavior between Windows and Linux/macOS startup scripts

#### 📝 Documentation Updates

- Updated node creation scripts with comprehensive error handling
- Added clear usage instructions in generated `requirements.txt` templates
- Improved logging messages in startup scripts with emoji indicators

---

## 📖 Introduction

BNOS (Bionic Neural Network Operating System) is a general-purpose modular execution engine based on bionic neural networks. The system adopts a brain-inspired architecture where multiple collaborative nodes are combined to build various application systems. It can be used for plugin-based systems, automation pipelines, task scheduling, edge computing, microservices, and other scenarios, as well as for building AI agents. Each node is the smallest execution unit in the system (similar to neurons or functional modules in the brain), and multiple nodes communicate and collaborate through JSON files to jointly realize complex business logic and processing capabilities.

## 🧬 Design Philosophy

This system draws inspiration from the core characteristics of biological neural networks, mapped to general-purpose modular execution scenarios:

- **Functional Nodes (Neurons)**: Each node functions like a neuron or functional module in the brain, responsible for specific subtask processing
- **Node Collaboration (Neural Circuits)**: Multiple nodes connect through data files, forming a collaboration network within the system
- **Attention Mechanism**: Task filtering based on rules simulates the attention focusing mechanism of nodes
- **Duplicate Processing Prevention**: Automatically marks processed tasks to avoid nodes repeatedly executing the same operations (improves efficiency)
- **Modular Design**: Flexibly build various application systems with complex capabilities by combining nodes with different functions

## ⚡ High Concurrency Design Philosophy

BNOS does not require all nodes to support high concurrency, but adopts a brain-inspired architecture:

1. **High-Performance Node Implementation**: High concurrency and high-performance requirements (such as LLM inference, large-scale computing, high-frequency access) are implemented only within individual specialized nodes
2. **Flexible Technology Stack**: These nodes can freely use multi-threading, multi-processing, coroutines, third-party engines, and other technologies without framework restrictions
3. **Lightweight Node Stability**: Other nodes are only responsible for task perception, attention filtering, decision scheduling, and result storage, maintaining lightweight stability
4. **Minimalist Communication**: Inter-node communication is achieved through files, avoiding the complexity of distributed systems
5. **Multi-Language Support**: Nodes can be implemented in different languages (Python, Rust, C++, etc.) based on performance requirements, all communicating through unified JSON protocol

This architecture makes the system both simple and stable, while enabling extreme performance in critical nodes.

## 🏗️ System Architecture

```
Upper Task (upper_data.json)
    ↓
Listener (listener.py) ← Attention Filtering (node attention mechanism)
    ↓
Node Processing Logic (main.py) ← Functional Unit Execution
    ↓
Output to Next Node (output.json) ← Inter-Node Communication
```

### Core Components

- **listener.py / listener.rs**: Node listener responsible for monitoring upper tasks, executing attention filtering, and calling node processing logic
- **main.py / main.rs**: Node processing logic implementing execution logic for specific functional units within the agent
- **config.json**: Node configuration file defining node name, listening path, attention rules, etc.
- **packet.py / packet.rs**: Data packet structure definition file (inter-node communication format)
- **create_node.py / rust_create_node.py**: Node creation tools that automatically generate complete node structures (Python/Rust)
- **Multi-Language Support**: Supports Python, Rust, and other language implementations, all using unified JSON communication protocol

## ✨ Key Features

- 🔒 **Environment Isolation**: Each node has its own independent Python virtual environment (venv), ensuring independence of functional units within the system
- 🎯 **Attention Mechanism**: Supports precise task filtering based on field values; nodes only focus on qualifying tasks (simulates attention focusing)
- 📝 **Duplicate Processing Prevention**: Automatically marks processed tasks to avoid nodes repeatedly executing the same operations (improves system efficiency)
- 📊 **Logging System**: Comprehensive node activity logging with both file and console output for tracking system behavior
- 🚀 **Modular Construction**: Provides node generator for one-click creation of standardized functional nodes, enabling rapid combination to build various application systems
- 💻 **Cross-Platform**: Supports Windows, Linux, and macOS systems
- 🌐 **General-Purpose Workflow Orchestration**: Supports building complex workflows, data pipelines, microservice components, etc. by combining multiple nodes
- 🔌 **Pluggable Design**: Node logic is independently encapsulated, allowing easy replacement, upgrade, or addition of new functional nodes to flexibly adjust system capabilities, suitable for plugin systems, automation toolchains, and other scenarios

## 📁 Project Structure

```
bnos/
├── data/
│   └── upper_data.json          # Upper task data file (task source)
├── node_python_demo/             # Python example node (recommended for rapid development)
│   ├── venv/                     # Independent virtual environment
│   ├── logs/                     # Log directory
│   │   └── listener.log         # Node activity log
│   ├── config.json              # Node configuration (attention parameters)
│   ├── listener.py              # Listener program (task receiver)
│   ├── main.py                  # Node processing logic (functional unit execution)
│   ├── packet.py                # Data packet definition (communication format)
│   ├── output.json              # Output data file (node output)
│   └── start.bat                # Windows startup script
├── node_rust_demo/               # Rust example node (recommended for high performance)
│   ├── src/                      # Rust source code
│   │   ├── main.rs              # Main processing logic
│   │   ├── listener.rs          # Listener and self-healing logic
│   │   └── packet.rs            # Data packet definition
│   ├── Cargo.toml               # Rust project configuration
│   ├── logs/                     # Log directory
│   │   └── listener.log         # Node activity log
│   ├── config.json              # Node configuration (attention parameters)
│   ├── output.json              # Output data file (node output)
│   ├── start.bat                # Windows startup script
│   └── start.sh                 # Linux/macOS startup script
├── python_create_node.py        # Python node creation tool
├── rust_create_node.py          # Rust node creation tool
└── README.md                    # Project documentation
```

## 🚀 Quick Start

### Prerequisites

**For Python Nodes:**
- Python 3.6+
- pip (for creating virtual environments)

**For Rust Nodes:**
- Rust toolchain (rustc, cargo)
- Verify installation: `rustc --version` and `cargo --version`

### Create Functional Nodes

#### Option 1: Python Node (Recommended for Rapid Development)

1. Run the node creation tool in the project root directory:

```bash
python python_create_node.py
```

2. Enter the node name (e.g., data_processor, api_handler, task_scheduler), and the system will automatically generate:
   - Complete node directory structure
   - Independent Python virtual environment
   - Standard configuration file
   - Startup scripts (Windows: `start.bat` / Linux: `start.sh`)

#### Option 2: Rust Node (Recommended for High Performance)

1. Run the Rust node creation tool:

```bash
python rust_create_node.py
```

2. Enter the node name, and the system will automatically generate:
   - Complete Rust project structure
   - Cargo.toml configuration
   - Source code templates (main.rs, listener.rs, packet.rs)
   - Startup scripts with auto-build capability

### Configure Node Attention

Edit the `config.json` file:

```json
{
  "node_name": "data_processor",           // Node name (functional unit ID)
  "listen_upper_file": "../data/upper_data.json",  // Path to upper task file (input channel)
  "output_file": "./output.json",     // Output file path (output channel)
  "filter": {                         // Attention filtering rules (attention mechanism)
    "type": "data_task"
  },
  "output_type": "data_result"         // Output data type identifier
}
```

### Write Node Processing Logic

**For Python Nodes:** Implement the `process()` function in `main.py`:

```python
def process(data):
    """Process input task and return results (functional unit execution)"""
    value = data.get("data", 0)
    return float(value) + 1
```

**For Rust Nodes:** Implement the `process()` function in `src/main.rs`:

```rust
fn process(data: &serde_json::Value) -> Option<serde_json::Value> {
    // Implement your business logic here
    let input = data.get("data")?;
    
    // Process data...
    let result = /* your processing logic */;
    
    Some(result)
}
```

### Start Functional Node

**Python Node:**

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

**Rust Node:**

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

The Rust node will automatically build the project on first run or when source code changes are detected.

## 📋 Configuration Guide

### config.json Parameters

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `node_name` | string | Unique node identifier (functional unit ID) | `"data_processor"` |
| `listen_upper_file` | string | Upper task file path (relative or absolute, input channel) | `"../data/upper_data.json"` |
| `output_file` | string | This node's output file path (output channel) | `"./output.json"` |
| `filter` | object | Attention filtering rules, key-value pair matching (attention mechanism) | `{"type": "data_task"}` |
| `output_type` | string | Output data type identifier (result type) | `"data_result"` |

### Attention Filtering Mechanism (Node Attention)

- If `filter` is an empty object `{}`, the node processes all tasks (broad attention)
- If filtering rules are configured, tasks are processed only when they contain all specified fields with exact value matches (focused attention)
- Example: `{"type": "data_task"}` means the node only focuses on tasks with `type` field value of `"data_task"`

### Data Packet Format (Inter-Node Communication)

**Input Task Packet** (`upper_data.json`):
```json
{
  "type": "data_task",
  "data": 153,
  "_processed_data_processor": true
}
```

**Output Result Packet** (`output.json`):
```json
{
  "code": 0,
  "type": "data_result",
  "data": 154
}
```

## 🔧 Development Guide

### Adding Dependencies

**For Python Nodes:** Add required Python packages to the node's `requirements.txt` file:

```
requests==2.28.0
numpy==1.23.0
openai==1.0.0
```

Then activate the virtual environment and install:

```bash
# Windows
venv\Scripts\activate
pip install -r requirements.txt

# Linux/macOS
source venv/bin/activate
pip install -r requirements.txt
```

**For Rust Nodes:** Add dependencies to `Cargo.toml`:

```toml
[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
chrono = "0.4"
# Add other dependencies...
```

Then build the project:

```bash
cargo build --release
```

### Debugging Tips

1. **View Logs**: Check `logs/listener.log` to understand node operation status (internal agent activity monitoring)
2. **Monitor Data**: Observe changes in `upper_data.json` and `output.json` (internal agent signal flow tracking)
3. **Test Attention**: Modify the `filter` rules in `config.json` to verify task filtering (attention adjustment)

### Log Format

```
[2026-04-24 17:26:11] [INFO] ✅ This is my task, starting processing
[2026-04-24 17:26:11] [INFO] ✅ Processing complete | Marked: _processed_perception_node
[2026-04-24 17:26:12] [ERROR] ❌ Task packet format error
```

## 🔄 Workflow (Node Collaborative Processing)

1. **Task Reception**: `listener.py` continuously monitors the `upper_data.json` file (node receives tasks from upstream nodes)
2. **Attention Filtering**: Determines whether to process the task based on `filter` rules in `config.json` (node attention focusing)
3. **Duplicate Check**: Checks if the task has been processed by the current node (via `_processed_<node_name>` marker, avoiding duplicate execution)
4. **Node Processing**: Calls `main.py` to execute node functional logic, passing JSON task as command-line arguments (functional unit execution)
5. **Output Results**: Writes processing results to `output.json` (node output, passed to downstream nodes)
6. **Mark Completion**: Adds processing markers to `upper_data.json` to prevent duplicate processing (task completion marking)

## ⚠️ Important Notes

1. **JSON Format**: Ensure all JSON files are properly formatted, otherwise parsing errors will occur
2. **File Permissions**: Ensure nodes have read/write permissions for data files
3. **Virtual Environment**: Each node must use an independent virtual environment to avoid dependency conflicts
4. **Concurrency Safety**: The current version does not support running multiple instances of the same node simultaneously
5. **Path Configuration**: Paths in configuration files can be relative or absolute
6. **System Design**: When designing systems, reasonably combine multiple nodes to form complete processing capabilities

## 🎯 Application Scenarios

As a general-purpose modular execution engine, BNOS is suitable for the following scenarios:

- 🔌 **Modular Plugin Systems**: Build scalable plugin architectures through node composition
- 📊 **Data Pipelines**: Construct automated pipelines for data processing, transformation, and analysis
- ⏰ **Task Scheduling**: Implement distributed scheduling and execution of complex tasks
- 🌐 **Edge Computing**: Deploy lightweight node networks on edge devices
- 🏗️ **Microservices**: Build node-based microservice components and API gateways
- 🛠️ **Automation Toolchains**: Create CI/CD, testing, deployment, and other automation toolchains
- 🤖 **AI Agents**: Build multi-node collaborative AI agent systems (perception, reasoning, decision nodes, etc.)
- 🧠 **Brain-Inspired Computing Experiments**: Conduct research experiments in brain-inspired computing and neural network simulation
- ⚡ **High-Performance Computing**: Use Rust nodes for compute-intensive tasks requiring maximum performance

## 🐛 FAQ

### Q: Node is not processing tasks?
A: Check the following:
- Confirm that `filter` rules are correctly configured (attention settings)
- Check `logs/listener.log` for filtering logs
- Verify that `upper_data.json` format is correct

### Q: How to reset node processing state?
A: Manually delete the `_processed_<node_name>` field from `upper_data.json` (clear node memory)

### Q: Virtual environment creation failed?
A: Ensure Python is installed and the `python -m venv` command is available

### Q: How to build a complete application system?
A: Create multiple functional nodes (such as data processing nodes, business logic nodes, API nodes, etc.), configure their `listen_upper_file` and `output_file` to form collaborative workflows, jointly constituting a complete application system. It can also be used to build AI agents by combining perception nodes, reasoning nodes, decision nodes, etc. to implement agent functionality.

### Q: How to choose between Python and Rust nodes?
A: 
- **Choose Python** when: Rapid prototyping, easy debugging, rich ecosystem libraries needed, moderate performance requirements
- **Choose Rust** when: Maximum performance required, memory safety critical, low-latency processing, production environment stability

### Q: Can I mix Python and Rust nodes in the same system?
A: Yes! All nodes communicate through standardized JSON files regardless of implementation language. You can freely combine Python and Rust nodes in the same workflow.

---

### 2026-05-21 - Background Execution & PID Health Detection

#### ✨ New Features

- **Background Process Detection**: GUI now detects nodes running in background from previous sessions via `.pid` files
- **Process Health Check**: Polls running processes every 3 seconds; crashed nodes auto-update to stopped status
- **Startup Scripts Overhaul**: Both `start.bat` and `start.sh` now support `--no-pause` flag, `start /b` / `nohup &` background launch, and automatic `.pid` writing
- **Node Generator Development Guidelines**: Comprehensive guide for creating new language node generators ([Node_Generator_Guidelines_EN.md](Node_Generator_Guidelines_EN.md) | [节点生成器开发准则.md](节点生成器开发准则.md))

#### 🔧 Bug Fixes

- Fixed `subprocess.PIPE` buffer deadlock by switching to `DEVNULL`
- Fixed start scripts blocking foreground execution
- Fixed cross-session process state loss

---

## 📄 License

This project is licensed under the MIT License.

## 👥 Contributing

Contributions are welcome! Please feel free to submit Pull Requests or Issues.

---

---

### Development & Design
Developed & Designed by **Ahdong&Shouey Team**
Last Updated: 2026-05-21
