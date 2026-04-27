"""
BNOS 主窗口 - 包含完整的界面布局和核心功能
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QFormLayout, QLineEdit, QPushButton, QLabel, QGroupBox,
    QComboBox, QTabWidget, QDialog, QDialogButtonBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QMenu, QGraphicsView, QGraphicsScene,
    QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF, QTimer
from PyQt6.QtGui import QIcon, QFont, QPainter, QPen, QColor, QAction

from ui.canvas_widget import NodeCanvas
from ui.node_list_panel import NodeListPanel


class AppConfig:
    """应用配置管理 - 全局配置记忆系统"""
    
    def __init__(self):
        # 配置文件路径（程序根目录）
        self.config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", 
            "app_config.json"
        )
        
        # 默认配置
        self.config = {
            # 窗口布局持久化
            "window_geometry": {
                "x": 100,
                "y": 100,
                "width": 1400,
                "height": 900,
                "maximized": False
            },
            "splitter_sizes": [250, 1150],  # 左侧节点列表 + 右侧画布
            
            # 项目记忆
            "last_project": None,
            
            # 画布视图状态（最后的项目）
            "canvas_view_state": {
                "scale": 1.0,
                "scroll_x": 0,
                "scroll_y": 0
            }
        }
        
        # 加载配置
        self.load()
    
    def load(self):
        """加载配置 - 带异常处理"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    
                    # 合并配置（保留新字段的默认值）
                    for key in loaded:
                        if key in self.config:
                            if isinstance(self.config[key], dict) and isinstance(loaded[key], dict):
                                # 字典类型：深度合并
                                self.config[key].update(loaded[key])
                            else:
                                # 其他类型：直接覆盖
                                self.config[key] = loaded[key]
                                
                print(f"✅ 配置已加载: {self.config_file}")
            else:
                print(f"ℹ️  配置文件不存在，使用默认配置")
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  配置文件损坏，重置为默认配置: {e}")
            # 备份损坏的文件
            if os.path.exists(self.config_file):
                backup_file = self.config_file + ".bak"
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    print(f"📦 已备份损坏的配置: {backup_file}")
                except:
                    pass
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
    
    def save(self):
        """保存配置 - 带异常处理"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                
            print(f"✅ 配置已保存: {self.config_file}")
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value


class BNOSMainWindow(QMainWindow):
    """BNOS主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 应用配置
        self.app_config = AppConfig()
        
        # 项目状态
        self.current_project_path = None
        self.nodes_data = {}  # {node_name: {config, path, process, status}}
        self.connections = []  # [(source_node, target_node)]
        
        # 初始化UI
        self.init_ui()
        self.init_toolbar()
        self.init_menu()
        
        # 恢复窗口状态
        self.restore_window_state()
        
        # 设置窗口属性
        self.setWindowTitle("BNOS 节点编排平台")
        
        # 自动打开最后的项目
        self.auto_open_last_project()
        
    def init_ui(self):
        """初始化主界面布局"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建分割器（左中两栏）
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板 - 节点列表
        self.node_list_panel = NodeListPanel(self)
        self.main_splitter.addWidget(self.node_list_panel)
        
        # 中间画布 - 节点编排
        self.canvas = NodeCanvas(self)
        self.main_splitter.addWidget(self.canvas)
        
        # 设置分割器比例
        self.main_splitter.setStretchFactor(0, 1)  # 左侧
        self.main_splitter.setStretchFactor(1, 4)  # 中间（最大）
        
        main_layout.addWidget(self.main_splitter)

    def init_toolbar(self):
        """初始化工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 文件操作
        new_project_action = QAction("新建项目", self)
        new_project_action.triggered.connect(self.new_project)
        toolbar.addAction(new_project_action)
        
        open_project_action = QAction("打开项目", self)
        open_project_action.triggered.connect(self.open_project)
        toolbar.addAction(open_project_action)
        
        toolbar.addSeparator()
        
        # 节点操作
        refresh_action = QAction("刷新节点", self)
        refresh_action.triggered.connect(self.refresh_nodes)
        toolbar.addAction(refresh_action)
        
        clear_connections_action = QAction("清空连线", self)
        clear_connections_action.triggered.connect(self.clear_connections)
        toolbar.addAction(clear_connections_action)
        
        toolbar.addSeparator()
        
        # 新建节点
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Python", "Node.js", "Go", "Java", "C++", "Rust", "Shell"])
        self.language_combo.setCurrentText("Python")
        toolbar.addWidget(QLabel("语言:"))
        toolbar.addWidget(self.language_combo)
        
        create_node_action = QAction("新建节点", self)
        create_node_action.triggered.connect(self.create_new_node)
        toolbar.addAction(create_node_action)
        
        toolbar.addSeparator()
        
        # 节点控制
        start_node_action = QAction("启动节点", self)
        start_node_action.triggered.connect(self.start_selected_node)
        toolbar.addAction(start_node_action)
        
        stop_node_action = QAction("停止节点", self)
        stop_node_action.triggered.connect(self.stop_selected_node)
        toolbar.addAction(stop_node_action)
        
    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_project_action = file_menu.addAction("新建项目")
        new_project_action.triggered.connect(self.new_project)
        
        open_project_action = file_menu.addAction("打开项目")
        open_project_action.triggered.connect(self.open_project)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        refresh_action = edit_menu.addAction("刷新节点")
        refresh_action.triggered.connect(self.refresh_nodes)
        
        clear_action = edit_menu.addAction("清空连线")
        clear_action.triggered.connect(self.clear_connections)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about)
        
    def new_project(self):
        """新建项目"""
        # 保存当前项目布局（如果有）
        if self.current_project_path:
            self.canvas.save_layout(self.current_project_path)
        
        project_dir = QFileDialog.getExistingDirectory(
            self, "选择项目目录", "", 
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not project_dir:
            return
        
        # 确认是否在项目目录下创建nodes子目录
        nodes_dir = os.path.join(project_dir, "nodes")
        if not os.path.exists(nodes_dir):
            reply = QMessageBox.question(
                self, "创建节点目录",
                f"在 {project_dir} 下创建 nodes/ 目录？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.makedirs(nodes_dir, exist_ok=True)
            else:
                return
        
        # 绑定项目
        self.current_project_path = project_dir
        self.nodes_data.clear()
        self.connections.clear()
        self.canvas.clear_canvas()
        
        # 刷新节点列表
        self.refresh_nodes()
        
        QMessageBox.information(self, "成功", f"已创建项目: {project_dir}")
        
    def open_project(self):
        """打开项目"""
        # 保存当前项目布局（如果有）
        if self.current_project_path:
            self.canvas.save_layout(self.current_project_path)
        
        project_dir = QFileDialog.getExistingDirectory(
            self, "打开项目目录", "", 
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not project_dir:
            return
        
        nodes_dir = os.path.join(project_dir, "nodes")
        if not os.path.exists(nodes_dir):
            reply = QMessageBox.question(
                self, "未找到节点目录",
                f"{project_dir} 下未找到 nodes/ 目录，是否创建？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.makedirs(nodes_dir, exist_ok=True)
            else:
                return
        
        # 绑定项目
        self.current_project_path = project_dir
        self.nodes_data.clear()
        self.connections.clear()
        self.canvas.clear_canvas()
        
        # 刷新节点列表
        self.refresh_nodes()
        
        # 加载画布布局
        self.canvas.load_layout(project_dir)
        
        QMessageBox.information(self, "成功", f"已打开项目: {project_dir}")
        
    def update_node_status(self, node_name, status):
        """更新节点状态并同步UI"""
        if node_name in self.nodes_data:
            self.nodes_data[node_name]['status'] = status
            
            # 同步更新画布上的节点显示
            self.canvas.sync_node_display(node_name)
            
            # 更新节点列表面板
            self.node_list_panel.update_node_list(self.nodes_data)
        
    def refresh_nodes(self):
        """刷新节点列表"""
        if not self.current_project_path:
            QMessageBox.warning(self, "警告", "请先打开或新建项目")
            return
        
        nodes_dir = os.path.join(self.current_project_path, "nodes")
        if not os.path.exists(nodes_dir):
            QMessageBox.warning(self, "警告", "nodes/ 目录不存在")
            return
        
        # 扫描节点
        self.nodes_data.clear()
        for item in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, item)
            if not os.path.isdir(node_path):
                continue
            
            config_path = os.path.join(node_path, "config.json")
            if not os.path.exists(config_path):
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                node_name = config.get('node_name', item)
                self.nodes_data[node_name] = {
                    'config': config,
                    'path': node_path,
                    'process': None,
                    'status': 'stopped'
                }
            except Exception as e:
                print(f"加载节点 {item} 失败: {e}")
        
        # 更新节点列表面板
        self.node_list_panel.update_node_list(self.nodes_data)
        
        # 同步更新画布上的所有节点显示
        self.canvas.sync_all_nodes_display()
        
    def create_new_node(self):
        """创建新节点"""
        if not self.current_project_path:
            QMessageBox.warning(self, "警告", "请先打开或新建项目")
            return
        
        language = self.language_combo.currentText()
        
        # 弹出对话框输入节点名称
        node_name, ok = QInputDialog.getText(
            self, "新建节点", 
            "请输入节点名称:",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not node_name:
            return
        
        # 直接调用create_node模块中的函数
        try:
            import sys
            import os
            sys.path.append(self.current_project_path)
            
            # 导入create_node模块
            import importlib.util
            spec = importlib.util.spec_from_file_location("create_node", 
                os.path.join(self.current_project_path, "create_node.py"))
            create_node = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(create_node)
            
            # 创建节点目录
            base_dir = os.path.join(self.current_project_path, "nodes")
            node_dir = os.path.join(base_dir, f"node_{node_name}")
            
            if os.path.exists(node_dir):
                QMessageBox.warning(self, "警告", f"节点 {node_dir} 已存在")
                return
            
            os.makedirs(node_dir)
            os.makedirs(os.path.join(node_dir, "logs"))

            print(f"🔧 创建空虚拟环境 venv")
            subprocess.run([sys.executable, "-m", "venv", os.path.join(node_dir, "venv")], check=True)

            with open(os.path.join(node_dir, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("# 在此添加节点依赖\n")

            # ==============================
            # config.json
            # ==============================
            config = {
                "node_name": f"node_{node_name}",
                "listen_upper_file": "../data/upper_data.json",
                "output_file": "./output.json",
                "filter": {},
                "output_type": ""
            }
            with open(os.path.join(node_dir, "config.json"), "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # ==============================
            # packet.py
            # ==============================
            packet = '''UPPER_PACKET = {"data": None}
OUTPUT_PACKET = {"code": 0, "data": None}
'''
            with open(os.path.join(node_dir, "packet.py"), "w", encoding="utf-8") as f:
                f.write(packet.strip())

            # ==============================
            # listener.py
            # ==============================
            listener = '''import os
import json
import time
import subprocess
from datetime import datetime

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(NODE_DIR, "config.json")
LOG_DIR = os.path.join(NODE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def log(msg, level="INFO"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{level}] {msg}"
    print(line)
    with open(os.path.join(LOG_DIR, "listener.log"), "a", encoding="utf-8") as f:
        f.write(line + "\\n")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception as e:
    log(f"配置加载失败: {e}", "ERROR")
    exit(1)

UPPER_FILE = os.path.abspath(os.path.join(NODE_DIR, cfg["listen_upper_file"]))
OUTPUT_FILE = os.path.abspath(os.path.join(NODE_DIR, cfg["output_file"]))
NODE_NAME = cfg["node_name"]
MY_FILTER = cfg.get("filter", {})
PROCESS_FLAG = f"_processed_{NODE_NAME}"

def is_my_data(data):
    if not MY_FILTER:
        return True
    for k, v in MY_FILTER.items():
        if data.get(k) != v:
            return False
    return True

log("=" * 50)
log(f"节点启动: {NODE_NAME}")
log(f"监听: {UPPER_FILE}")
log(f"过滤: {MY_FILTER}")
log("当前环境: 独立虚拟环境")
log("=" * 50)

while True:
    try:
        if not os.path.exists(UPPER_FILE):
            time.sleep(0.2)
            continue

        with open(UPPER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get(PROCESS_FLAG):
            time.sleep(0.2)
            continue

        if not is_my_data(data):
            time.sleep(0.2)
            continue

        log("✅ 开始处理数据")

        # 【关键】只用自己虚拟环境运行 main.py
        if os.name == "nt":
            py_path = os.path.join(NODE_DIR, "venv", "Scripts", "python.exe")
        else:
            py_path = os.path.join(NODE_DIR, "venv", "bin", "python")

        res = subprocess.run(
            [py_path, os.path.join(NODE_DIR, "main.py"), json.dumps(data)],
            capture_output=True, text=True, encoding="utf-8"
        )

        output = res.stdout.strip()
        if not output:
            log("⚠️ 返回空数据")
            continue

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)

        data[PROCESS_FLAG] = True
        with open(UPPER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        log(f"✅ 处理完成: {PROCESS_FLAG}")

    except json.JSONDecodeError:
        log("❌ 数据包格式错误", "ERROR")
        time.sleep(1)
    except Exception as e:
        log(f"❌ 异常: {e}", "ERROR")
        time.sleep(1)

    time.sleep(0.2)
'''
            with open(os.path.join(node_dir, "listener.py"), "w", encoding="utf-8") as f:
                f.write(listener.strip())

            # ==============================
            # main.py
            # ==============================
            main = '''import sys
import json
import os

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(NODE_DIR, "config.json")
with open(config_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

def process(data):
    return data.get("data")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"code": -1, "error": "no input"}))
        sys.exit(1)

    input_data = json.loads(sys.argv[1])
    result = process(input_data)

    print(json.dumps({
        "code": 0,
        "type": cfg["output_type"],
        "data": result
    }, ensure_ascii=False))
'''
            with open(os.path.join(node_dir, "main.py"), "w", encoding="utf-8") as f:
                f.write(main.strip())

            # ==============================
            # output.json
            # ==============================
            with open(os.path.join(node_dir, "output.json"), "w", encoding="utf-8") as f:
                f.write('{"code":0,"data":null}')

            # ==============================
            # 自动生成启动脚本（双击即用）
            # ==============================
            if os.name == "nt":
                start_bat = '''@echo off
cls
echo ======================================
echo        BNOS Node Starter (Windows)
echo ======================================
echo.
cd /d "%~dp0"
chmp 65001 >nul
if not exist "venv\\Scripts\\python.exe" (
    echo ❌ 虚拟环境不存在！
    pause
    exit /b 1
)
call venv\\Scripts\\activate.bat
echo ✅ 启动监听程序...
echo.
venv\\Scripts\\python.exe listener.py
echo.
echo ❌ 程序已退出
pause
'''
                with open(os.path.join(node_dir, "start.bat"), "w", encoding="utf-8") as f:
                    f.write(start_bat)
            else:
                start_sh = '''#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 listener.py
'''
                with open(os.path.join(node_dir, "start.sh"), "w", encoding="utf-8") as f:
                    f.write(start_sh)
                os.chmod(os.path.join(node_dir, "start.sh"), 0o755)

            print(f"\n🎉 节点创建完成：{node_dir}")
            print(f"✅ 独立虚拟环境：venv")
            print(f"✅ 双击启动：start.bat / start.sh")
            print(f"✅ 100% 环境隔离！")
            
            # 成功后刷新节点列表
            self.refresh_nodes()
            QMessageBox.information(self, "成功", f"节点 {node_name} 创建成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建节点失败: {str(e)}")

    def start_selected_node(self):
        """启动选中的节点"""
        selected_node = self.node_list_panel.get_selected_node()
        if not selected_node:
            QMessageBox.warning(self, "警告", "请先选择一个节点")
            return
        
        if selected_node not in self.nodes_data:
            return
        
        node_info = self.nodes_data[selected_node]
        if node_info['status'] == 'running':
            QMessageBox.information(self, "提示", "节点已在运行中")
            return
        
        # 启动节点进程 - 直接执行Python命令而非批处理脚本
        node_path = node_info['path']
        
        # 确定虚拟环境的Python解释器路径
        if os.name == 'nt':  # Windows
            python_exe = os.path.join(node_path, "venv", "Scripts", "python.exe")
        else:  # Linux/Mac
            python_exe = os.path.join(node_path, "venv", "bin", "python")
        
        listener_script = os.path.join(node_path, "listener.py")
        
        if not os.path.exists(python_exe):
            QMessageBox.critical(self, "错误", f"虚拟环境不存在: {python_exe}")
            return
        
        if not os.path.exists(listener_script):
            QMessageBox.critical(self, "错误", f"监听脚本不存在: {listener_script}")
            return
        
        try:
            # 启动进程 - 直接运行Python，不使用shell
            if os.name == 'nt':
                # Windows: 创建新的进程组以便后续可以终止整个进程树
                process = subprocess.Popen(
                    [python_exe, listener_script],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: 使用进程组
                process = subprocess.Popen(
                    [python_exe, listener_script],
                    cwd=node_path,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            node_info['process'] = process
            node_info['status'] = 'running'
            
            # 更新状态
            self.node_list_panel.update_node_status(selected_node, 'running')
            self.canvas.update_node_status(selected_node, 'running')
            
            QMessageBox.information(self, "成功", f"节点 {selected_node} 已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点失败: {str(e)}")
    
    def start_selected_node_by_name(self, node_name):
        """按名称启动节点（供对话框调用）"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'running':
            QMessageBox.information(self, "提示", "节点已在运行中")
            return
        
        # 启动节点进程 - 直接执行Python命令而非批处理脚本
        node_path = node_info['path']
        
        # 确定虚拟环境的Python解释器路径
        if os.name == 'nt':  # Windows
            python_exe = os.path.join(node_path, "venv", "Scripts", "python.exe")
        else:  # Linux/Mac
            python_exe = os.path.join(node_path, "venv", "bin", "python")
        
        listener_script = os.path.join(node_path, "listener.py")
        
        if not os.path.exists(python_exe):
            QMessageBox.critical(self, "错误", f"虚拟环境不存在: {python_exe}")
            return
        
        if not os.path.exists(listener_script):
            QMessageBox.critical(self, "错误", f"监听脚本不存在: {listener_script}")
            return
        
        try:
            # 启动进程 - 直接运行Python，不使用shell
            if os.name == 'nt':
                # Windows: 创建新的进程组以便后续可以终止整个进程树
                process = subprocess.Popen(
                    [python_exe, listener_script],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: 使用进程组
                process = subprocess.Popen(
                    [python_exe, listener_script],
                    cwd=node_path,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            node_info['process'] = process
            node_info['status'] = 'running'
            
            # 更新状态
            self.node_list_panel.update_node_status(node_name, 'running')
            self.canvas.update_node_status(node_name, 'running')
            
            QMessageBox.information(self, "成功", f"节点 {node_name} 已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点失败: {str(e)}")
    
    def stop_selected_node(self):
        """停止选中的节点"""
        selected_node = self.node_list_panel.get_selected_node()
        if not selected_node:
            QMessageBox.warning(self, "警告", "请先选择一个节点")
            return
        
        if selected_node not in self.nodes_data:
            return
        
        node_info = self.nodes_data[selected_node]
        if node_info['status'] == 'stopped':
            QMessageBox.information(self, "提示", "节点未在运行")
            return
        
        # 停止进程
        process = node_info['process']
        if process:
            try:
                if os.name == 'nt':
                    # Windows: 先尝试优雅终止
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制杀死进程及其子进程
                        import signal
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                else:
                    # Linux/Mac: 终止整个进程组
                    import signal
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
            except Exception as e:
                print(f"停止节点时出错: {e}")
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
        
        node_info['process'] = None
        node_info['status'] = 'stopped'
        
        # 更新状态
        self.node_list_panel.update_node_status(selected_node, 'stopped')
        self.canvas.update_node_status(selected_node, 'stopped')
        
        QMessageBox.information(self, "成功", f"节点 {selected_node} 已停止")
    
    def stop_selected_node_by_name(self, node_name):
        """按名称停止节点（供对话框调用）"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'stopped':
            QMessageBox.information(self, "提示", "节点未在运行")
            return
        
        # 停止进程
        process = node_info['process']
        if process:
            try:
                if os.name == 'nt':
                    # Windows: 先尝试优雅终止
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制杀死进程及其子进程
                        import signal
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                else:
                    # Linux/Mac: 终止整个进程组
                    import signal
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
            except Exception as e:
                print(f"停止节点时出错: {e}")
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
        
        node_info['process'] = None
        node_info['status'] = 'stopped'
        
        # 更新状态
        self.node_list_panel.update_node_status(node_name, 'stopped')
        self.canvas.update_node_status(node_name, 'stopped')
        
        QMessageBox.information(self, "成功", f"节点 {node_name} 已停止")

    def clear_connections(self):
        """清空所有连线"""
        reply = QMessageBox.question(
            self, "确认", 
            "确定要清空所有连线吗？\n这将重置所有节点的 listen_upper_file 配置。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 清空所有下游节点的 listen_upper_file
        for node_name, node_info in self.nodes_data.items():
            config = node_info['config']
            config['listen_upper_file'] = ""
            
            config_path = os.path.join(node_info['path'], "config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 清空画布连线
        self.canvas.clear_edges()
        
        QMessageBox.information(self, "成功", "已清空所有连线")

    def closeEvent(self, event):
        """窗口关闭事件，保存所有状态"""
        # 保存当前项目布局
        if self.current_project_path:
            self.canvas.save_layout(self.current_project_path)
        
        # 保存应用配置
        self.save_window_state()
        self.app_config.set("last_project", self.current_project_path)
        self.app_config.save()
        
        # 停止所有运行中的节点
        for node_name, node_info in self.nodes_data.items():
            if node_info['status'] == 'running' and node_info['process']:
                try:
                    node_info['process'].terminate()
                    node_info['process'].wait(timeout=3)
                except:
                    pass
        
        event.accept()
    
    def save_window_state(self):
        """保存窗口状态 - 完整布局持久化"""
        try:
            # 1. 保存窗口几何信息（位置、尺寸、最大化状态）
            geometry = {
                "x": self.geometry().x(),
                "y": self.geometry().y(),
                "width": self.geometry().width(),
                "height": self.geometry().height(),
                "maximized": self.isMaximized()
            }
            self.app_config.set("window_geometry", geometry)
            
            # 2. 保存Splitter比例（节点列表 + 画布）
            if hasattr(self, 'main_splitter'):
                sizes = self.main_splitter.sizes()
                self.app_config.set("splitter_sizes", sizes)
            
            # 3. 保存当前项目路径
            if self.current_project_path:
                self.app_config.set("last_project", self.current_project_path)
                
                # 4. 保存画布视图状态（缩放、滚动位置）
                view_state = {
                    "scale": self.canvas.transform().m11(),  # 获取缩放比例
                    "scroll_x": self.canvas.horizontalScrollBar().value(),
                    "scroll_y": self.canvas.verticalScrollBar().value()
                }
                self.app_config.set("canvas_view_state", view_state)
                
                # 5. 保存画布布局（节点位置、连线）
                self.canvas.save_layout(self.current_project_path)
            
            # 6. 保存到文件
            self.app_config.save()
            
            print("✅ 窗口状态已保存")
            
        except Exception as e:
            print(f"⚠️  保存窗口状态失败: {e}")
    
    def restore_window_state(self):
        """恢复窗口状态 - 完整布局还原"""
        try:
            # 1. 恢复窗口几何信息
            geom = self.app_config.get("window_geometry")
            if geom:
                if geom.get("maximized", False):
                    self.showMaximized()
                else:
                    self.setGeometry(
                        geom.get("x", 100),
                        geom.get("y", 100),
                        geom.get("width", 1400),
                        geom.get("height", 900)
                    )
            
            # 2. 恢复Splitter比例
            splitter_sizes = self.app_config.get("splitter_sizes")
            if splitter_sizes and hasattr(self, 'main_splitter'):
                # 验证数据有效性
                if isinstance(splitter_sizes, list) and len(splitter_sizes) == 2:
                    self.main_splitter.setSizes(splitter_sizes)
            
            print("✅ 窗口状态已恢复")
            
        except Exception as e:
            print(f"⚠️  恢复窗口状态失败，使用默认布局: {e}")
    
    def auto_open_last_project(self):
        """自动打开最后的项目 - 只加载数据，不自动添加节点到画布"""
        last_project = self.app_config.get("last_project")
        if last_project and os.path.exists(last_project):
            nodes_dir = os.path.join(last_project, "nodes")
            if os.path.exists(nodes_dir):
                self.current_project_path = last_project
                
                print(f"📂 自动打开项目: {last_project}")
                
                # 1. 刷新节点列表（加载所有节点数据）
                self.refresh_nodes()
                
                # 2. 加载画布布局（包含节点位置、连线关系、视图状态的完整恢复）
                self.canvas.load_layout(last_project)
                
                # 3. 恢复Splitter比例
                splitter_sizes = self.app_config.get("splitter_sizes")
                if splitter_sizes and hasattr(self, 'main_splitter'):
                    if isinstance(splitter_sizes, list) and len(splitter_sizes) == 2:
                        self.main_splitter.setSizes(splitter_sizes)

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于 BNOS",
            "BNOS 桌面可视化节点编排平台\n\n"
            "版本: 1.0.0\n"
            "基于 PyQt6 开发\n"
            "纯本地文件操作，无后端服务"
        )
