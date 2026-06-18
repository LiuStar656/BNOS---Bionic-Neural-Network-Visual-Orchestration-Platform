# BNOS 完整架构图 (Mermaid)

> **BNOS** (Bionic Neural Network Program Operating System) — 基于 PySide6 的桌面端可视化节点编排平台  
> 生成日期：2026-06-18

---

## 一、启动流程链

```mermaid
flowchart TD
    A["start_bnos_console.bat<br/>Windows 启动脚本<br/>创建虚拟环境 + 安装依赖"] --> B["launcher.py<br/>tkinter 闪屏启动器<br/>启动动画 + 进度条"]
    B --> C["bnos_console.py::main()<br/>PySide6 应用主入口"]
    C --> C1["加载语言 AppConfig"]
    C --> C2["初始化 QApplication<br/>Fusion 风格"]
    C --> C3["初始化 Codicon 图标系统"]
    C --> C4["初始化 ApplicationContext<br/>全局服务上下文"]
    C --> C5["创建 BNOSMainWindow"]
    C --> C6["初始化 UI 服务<br/>Toast / 右键菜单等"]
    C --> C7["加载/恢复项目"]
    C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> C7
    C7 --> D["window.show()"]
    D --> E{"app.exec()"}
    E -->|exit code = 42| F["restart_helper.py<br/>等待旧进程退出<br/>启动新进程"]
    E -->|其他| G["正常退出"]
```

---

## 二、整体分层架构

```mermaid
graph TB
    subgraph VIEW["视图层 Views"]
        direction TB
        MW["BNOSMainWindow<br/>7个 Mixin + 主类"]
        DOCK["各 Dock 面板<br/>NodeListDock | ResourceMonitorDock<br/>NodeMonitorDock | HistoryPanel<br/>TerminalDock | PropertyPanel"]
        NC["NodeCanvas<br/>QGraphicsView/Scene<br/>items/ | mixins/ | drawing/<br/>parameter_widgets/"]
        DLG["Dialogs 对话框<br/>Settings | Color | NodeConfig | File"]
        MC["Menu & Creators<br/>MenuManager<br/>NodeCreatorManager"]
        MW --- DOCK
        MW --- NC
        MW --- DLG
        MW --- MC
    end

    subgraph CORE["核心服务层 Core Services"]
        direction TB
        INFRA["基础设施<br/>EventBus | DI Container | Logger<br/>AppConfig | Theme | i18n<br/>Codicon | ApplicationContext"]
        MGRS["管理器 Managers<br/>PanelManager | DockManager<br/>ProcessManager | PollingManager<br/>ShortcutManager | ToastQueueManager<br/>FileOperationManager | ImportExportManager<br/>WindowStateManager | HistoryManager"]
        SVCS["服务 Services<br/>NodeControlService | NodeRegistry<br/>ShutdownOrchestrator<br/>NodeCreationWorker<br/>ProjectManager"]
        ACTS["Actions & Commands<br/>ActionRegistry | ActionFactory<br/>BuiltinCanvasActions<br/>BuiltinNodeActions<br/>BuiltinProjectActions<br/>BuiltinViewActions<br/>NodeCommands | EdgeCommands<br/>CompoundCommands"]
        INFRA --> MGRS --> SVCS --> ACTS
    end

    subgraph CANVAS["画布引擎层 Canvas Engine"]
        direction TB
        ITEMS["items/ 图形元素<br/>NodeItem | EdgeItem | AnchorItem<br/>AnchorManager | NodeStatusWidget<br/>NodeStyle | node_components/"]
        MIXINS["mixins/ 画布行为 11个<br/>EventHandlers | Connections<br/>NodeManager | Selection<br/>BoxSelect | Menus | BatchOps<br/>Layout | Colors | Background"]
        DRAW["drawing/ 绘图系统<br/>DrawToolbar | DrawLayer<br/>tools/ | styles/ | components/"]
        PARAM["parameter_widgets/ 14种<br/>string | int | float | bool<br/>color | enum | password | range<br/>text | file_picker | dir_picker"]
        ITEMS --- MIXINS --- DRAW --- PARAM
    end

    subgraph RT["节点运行时层 Runtime"]
        direction TB
        NP["node_process<br/>启动/停止节点进程"]
        PM["polling_manager<br/>状态轮询 psutil"]
        PRM["process_manager<br/>进程生命周期管理"]
        NCW["node_creation_worker<br/>异步节点创建"]
        ENM["external_node_manager<br/>外部节点挂载/卸载"]
        JNS["json_node_starter<br/>JSON配置节点启动"]
        NCP["node_config_parser<br/>节点配置解析器"]
        CI["connection_inferrer<br/>连线推断器"]
    end

    subgraph TEST["测试 & 工具层"]
        TST["tests/ 10个测试文件"]
        TL["tools/ 节点生成器<br/>Rust/Python 模板"]
    end

    VIEW --> CORE
    CORE --> CANVAS
    CANVAS --> RT
    RT --> TEST
```

---

## 三、主窗口 Mixin 架构

```mermaid
classDiagram
    class BNOSMainWindow {
        +__main__.py 主类
        +菜单栏
        +工具栏
        +CanvasHost
        +面板创建
    }
    class StateMixin {
        +窗口状态保存与恢复
        +自动打开上次项目
    }
    class LifecycleMixin {
        +启动流程 _init_and_restore()
        +关闭流程 closeEvent()
        +清理链
    }
    class ActionsMixin {
        +消息对话框
        +项目目录打开
        +撤销/重做状态同步
    }
    class PanelMixin {
        +创建所有面板
        +切换/关闭面板
        +节点列表/资源监控/节点监控/历史
    }
    class IPCMixin {
        +进程间通信
        +单实例锁
    }
    class NodeMixin {
        +节点启停操作
        +批量节点操作
    }
    class InteractionMixin {
        +鼠标/键盘交互
        +拖放操作
        +连接线操作
    }

    StateMixin --|> BNOSMainWindow : Mixin
    LifecycleMixin --|> BNOSMainWindow : Mixin
    ActionsMixin --|> BNOSMainWindow : Mixin
    PanelMixin --|> BNOSMainWindow : Mixin
    IPCMixin --|> BNOSMainWindow : Mixin
    NodeMixin --|> BNOSMainWindow : Mixin
    InteractionMixin --|> BNOSMainWindow : Mixin
```

---

## 四、画布 NodeCanvas 详细架构

```mermaid
graph TB
    subgraph NODECANVAS["NodeCanvas (QGraphicsView)"]
        direction TB
        
        subgraph ITEMS["items/ 图形元素"]
            NI["NodeItem<br/>节点图形项<br/>矩形+标题"]
            EI["EdgeItem<br/>连线图形项<br/>贝塞尔曲线"]
            AI["AnchorItem<br/>锚点(端口)<br/>输入/输出圆形"]
            AM["AnchorManager<br/>锚点管理器"]
            NSW["NodeStatusWidget<br/>节点状态指示器"]
            NS["NodeStyle<br/>节点样式管理"]
            
            NI --> NC["node_components/ 解耦子组件"]
            NC --> NC1["header.py 标题栏"]
            NC --> NC2["body.py 主体"]
            NC --> NC3["port_area.py 端口区域"]
            NC --> NC4["status_badge.py 状态徽章"]
            NC --> NC5["resize_handle.py 缩放手柄"]
        end
        
        subgraph MIXINS["mixins/ 画布行为 11个"]
            CEH["canvas_event_handlers<br/>鼠标/键盘事件"]
            CC["canvas_connections<br/>拖拽连线"]
            CNM["canvas_node_manager<br/>节点增删管理"]
            CS["canvas_selection<br/>选择操作"]
            CBS["canvas_box_select<br/>框选操作"]
            CM["canvas_menus<br/>右键菜单"]
            CBO["canvas_batch_ops<br/>批量操作"]
            CL["canvas_layout<br/>自动布局"]
            CCOL["canvas_colors<br/>颜色/主题"]
            CBR["canvas_background_renderer<br/>背景网格渲染"]
            CTRL["controllers<br/>控制器基类"]
        end
        
        subgraph DRAW["drawing/ 绘图系统"]
            DT["draw_toolbar<br/>绘图工具栏"]
            DL["draw_layer<br/>图层管理"]
            TOOLS["tools/<br/>画笔/橡皮/形状"]
            STYLES["styles/<br/>绘图样式"]
            COMP["components/<br/>绘图组件"]
            GI["graphic_items/<br/>自由线条/形状/文本"]
        end
        
        subgraph PARAM["parameter_widgets/ 14种编辑器"]
            BASE["_base.py 基类"]
            PROXY["_proxy_combo 代理下拉框"]
            P1["string | int | float | bool"]
            P2["color | enum | password"]
            P3["range | text"]
            P4["file_picker | dir_picker"]
        end
    end

    ITEMS --- MIXINS --- DRAW --- PARAM
```

---

## 五、面板系统架构

```mermaid
graph TB
    subgraph MAIN["BNOSMainWindow 主窗口布局"]
        direction TB
        
        subgraph LEFT["左侧面板区 Left Dock"]
            NLD["NodeListDock<br/>节点列表 Dock"]
            NLP["NodeListPanel<br/>节点树形列表 Widget<br/>搜索/过滤/拖拽创建<br/>分组/收藏/最近使用"]
            HP["HistoryPanel<br/>历史操作面板<br/>撤销/重做列表"]
            
            NLD --> NLP
        end
        
        subgraph CENTER["中央画布区 Center"]
            CH["CanvasHost<br/>NodeCanvas 宿主<br/>可缩放画布"]
        end
        
        subgraph RIGHT["右侧面板区 Right Dock"]
            RMD["ResourceMonitorDock<br/>资源监控 Dock<br/>CPU/内存/磁盘 实时图表"]
            NMD["NodeMonitorDock<br/>节点运行监控 Dock<br/>运行中节点列表<br/>日志/输出查看<br/>启停控制"]
            PP["PropertyPanel<br/>属性面板<br/>选中节点属性编辑"]
        end
        
        subgraph BOTTOM["底部面板区 Bottom Dock"]
            TD["TerminalDock<br/>终端面板<br/>内嵌终端模拟器<br/>多标签页<br/>命令执行/节点输出"]
        end
    end
    
    subgraph SHARED["_shared/ 面板共享组件"]
        NLS["node_log_sub_panel<br/>节点日志子面板"]
        NPS["node_panel_sync_mixin<br/>面板同步 Mixin"]
        SRC["system_resource_collector<br/>系统资源采集器"]
    end

    LEFT --- CENTER --- RIGHT
    CENTER --- BOTTOM
    LEFT -.- SHARED
    RIGHT -.- SHARED
```

---

## 六、核心服务架构

### 6.1 事件总线 EventBus

```mermaid
flowchart LR
    subgraph PUB["发布者 Publishers"]
        P1["NodeCanvas<br/>画布操作"]
        P2["NodeProcess<br/>节点进程"]
        P3["PollingManager<br/>状态轮询"]
        P4["PanelManager<br/>面板管理"]
        P5["ProjectManager<br/>项目管理"]
    end
    
    EB["EventBus<br/>全局事件总线<br/>发布/订阅模式"]
    
    subgraph SUB["订阅者 Subscribers"]
        S1["ResourceMonitor<br/>资源监控面板"]
        S2["NodeMonitor<br/>节点监控面板"]
        S3["HistoryPanel<br/>历史面板"]
        S4["PropertyPanel<br/>属性面板"]
        S5["ToastNotification<br/>通知系统"]
        S6["ShutdownOrchestrator<br/>关闭编排器"]
    end

    P1 & P2 & P3 & P4 & P5 --> EB
    EB --> S1 & S2 & S3 & S4 & S5 & S6
```

### 6.2 依赖注入 DI Container

```mermaid
flowchart TB
    DI["DI Container<br/>轻量级 IoC 容器<br/>管理核心服务单例"]
    
    DI --> A["IConfig → AppConfig"]
    DI --> B["IEventBus → EventBus"]
    DI --> C["ILogger → Logger"]
    DI --> D["IPanelManager → PanelManager"]
    DI --> E["IDockManager → DockManager"]
    DI --> F["IProcessManager → ProcessManager"]
    
    DI -.->|优势| G["可测试性"]
    DI -.->|优势| H["松耦合"]
    DI -.->|优势| I["集中管理"]
```

### 6.3 Actions & Commands 系统

```mermaid
flowchart TB
    subgraph ACTION["Action 系统 (高层抽象，面向UI)"]
        AD["ActionDefinition<br/>定义动作<br/>名称/图标/快捷键/回调"]
        AR["ActionRegistry<br/>注册中心<br/>统一管理所有动作"]
        AF["ActionFactory<br/>工厂<br/>创建 QAction 实例"]
        
        subgraph BUILTIN["内置动作分类"]
            BCA["builtin_canvas_actions<br/>画布操作<br/>缩放/平移/布局"]
            BNA["builtin_node_actions<br/>节点操作<br/>创建/删除/启停"]
            BPA["builtin_project_actions<br/>项目操作<br/>新建/打开/保存"]
            BVA["builtin_view_actions<br/>视图操作<br/>面板/全屏/主题"]
        end
        
        subgraph NODEACT["node/ 节点专用动作"]
            NA1["start_node_action 启动"]
            NA2["stop_node_action 停止"]
            NA3["restart_node_action 重启"]
        end
        
        AD --> AR --> AF
        AF --> BUILTIN
        AF --> NODEACT
    end
    
    subgraph CMD["Command 系统 (低层抽象，撤销/重做)"]
        BC["BaseCommand<br/>命令基类<br/>execute() / undo()"]
        NC["NodeCommands<br/>节点增删改"]
        EC["EdgeCommands<br/>连线增删改"]
        CC["CompoundCommands<br/>组合命令<br/>批量操作原子性"]
        HM["HistoryManager<br/>撤销/重做栈管理"]
        
        BC --> NC & EC & CC
        NC & EC & CC --> HM
    end
    
    ACTION -.->|UI触发| CMD
```

---

## 七、数据流图

### 7.1 节点创建流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant NC as NodeCreatorManager
    participant NW as NodeCreationWorker (异步)
    participant EB as EventBus
    participant CV as NodeCanvas
    participant NP as NodeListPanel

    User->>NC: 拖拽/菜单创建请求
    NC->>NW: 启动异步创建
    NW->>NW: 加载节点配置/模板
    NW->>CV: 创建 NodeItem 渲染到画布
    NW->>EB: emit("node.created")
    EB->>NP: 更新节点列表
    EB->>NP: 更新收藏/最近使用
```

### 7.2 节点运行流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant NP as node_process
    participant SP as subprocess
    participant PM as PollingManager
    participant RC as ResourceCollector
    participant EB as EventBus
    participant UI as Monitor Panels

    User->>NP: 点击启动按钮
    NP->>SP: Popen() 启动子进程
    SP-->>NP: 返回 PID
    
    loop 每秒轮询
        PM->>RC: psutil 采集 CPU/内存/IO
        RC->>EB: emit("node.status_changed")
        EB->>UI: 更新资源监控面板
        EB->>UI: 更新节点监控面板
    end
    
    User->>NP: 点击停止按钮
    NP->>SP: terminate() / kill()
    SP-->>NP: 进程退出
    NP->>EB: emit("node.stopped")
    EB->>UI: 更新状态显示
```

### 7.3 项目保存/加载流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant PM as ProjectManager
    participant PW as ProjectLoadWorker (异步)
    participant FS as 文件系统 (JSON)
    participant CV as NodeCanvas
    participant EB as EventBus

    rect rgb(40, 60, 40)
        Note over User,FS: 保存流程
        User->>PM: 保存操作
        PM->>CV: 收集节点/连线数据
        CV-->>PM: 返回数据
        PM->>FS: JSON 序列化写入 canvas_layout.json
        FS-->>PM: 保存完成
    end

    rect rgb(60, 40, 40)
        Note over User,FS: 加载流程
        User->>PM: 打开项目
        PM->>PW: 启动异步加载
        PW->>FS: JSON 反序列化读取
        FS-->>PW: 返回数据
        PW->>CV: 批量重建 NodeItem + EdgeItem
        PW->>EB: emit("project.opened")
        EB->>CV: 刷新画布
    end
```

### 7.4 撤销/重做流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant HM as HistoryManager
    participant CMD as Command 栈
    participant CV as NodeCanvas

    User->>CV: 执行操作 (增/删/改节点)
    CV->>CMD: 创建 Command 并入栈
    CMD->>HM: push(command)

    User->>HM: Ctrl+Z 撤销
    HM->>CMD: pop() 取出最近命令
    CMD->>CMD: command.undo()
    CMD->>CV: 画布状态回滚

    User->>HM: Ctrl+Y / Ctrl+Shift+Z 重做
    HM->>CMD: 从 redo 栈取出
    CMD->>CMD: command.execute()
    CMD->>CV: 画布状态恢复
```

### 7.5 安全关闭流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant MW as BNOSMainWindow
    participant SO as ShutdownOrchestrator
    participant NP as node_process
    participant PM as ProjectManager
    participant WS as WindowStateManager
    participant EB as EventBus

    User->>MW: closeEvent / 退出
    MW->>SO: 触发关闭编排
    SO->>EB: emit("app.shutting_down")
    
    par 并行清理
        SO->>NP: 遍历所有运行中节点
        NP->>NP: terminate() 逐个停止
    and
        SO->>PM: 保存当前项目
        PM->>PM: 序列化画布布局到 JSON
    and
        SO->>WS: 保存窗口状态
        WS->>WS: 窗口几何/面板可见性
    end
    
    SO-->>MW: 清理完成
    MW->>MW: QApplication.quit()
```

---

## 八、模块依赖关系图

```mermaid
graph LR
    subgraph ENTRY["入口层"]
        L["launcher.py"]
        BC["bnos_console.py"]
        RH["restart_helper.py"]
    end

    subgraph UI["ui/ 主代码"]
        MW["main_window/"]
        CORE["core/"]
        CV["canvas/"]
        PNL["panels/"]
        DLG["dialogs/"]
        MNU["menu/"]
        CRT["creators/"]
        IC["icons/"]
    end

    subgraph EXT["外部依赖"]
        PS["PySide6 Qt6"]
        PSU["psutil"]
        PYI["PyInstaller"]
        VE["virtualenv"]
        TK["tkinter"]
    end

    subgraph CFG["配置文件"]
        BCJ["bnos_config.json"]
        CSJ["color_settings.json"]
        ACJ["ui/app_config.json"]
        RT["requirements.txt"]
    end

    ENTRY --> UI
    UI --> EXT
    UI --> CFG
    MW --> CORE
    MW --> CV
    MW --> PNL
    CORE --> CV
    CORE --> PNL
```

---

## 九、技术栈

```mermaid
mindmap
  root((BNOS 技术栈))
    UI 框架
      PySide6 / Qt 6
      QGraphicsView / Scene
      QSS + Fusion 暗色主题
    :::urgent large
    图标系统
      Codicon VSCode 图标集
      codicon.ttf 字体
    基础设施
      自研 EventBus 事件总线
      自研 DI 依赖注入容器
      自研 i18n 国际化
      Python logging 日志
    进程管理
      subprocess
      psutil 系统监控
    持久化
      JSON 配置/项目
      AppConfig 应用配置
    打包部署
      PyInstaller
      virtualenv 虚拟环境
      tkinter 启动器
    设计模式
      Mixin 组合模式
      Command 撤销重做
      Observer 轮询监控
      Registry 注册表
      Factory 工厂
      Singleton 单例
```

---

## 十、设计模式应用总览

```mermaid
graph TB
    subgraph PATTERNS["设计模式"]
        M1["Mixin 组合<br/>BNOSMainWindow 7个<br/>NodeCanvas 11个"]
        M2["发布/订阅<br/>EventBus"]
        M3["依赖注入 DI<br/>di.py / container"]
        M4["Command<br/>commands/"]
        M5["注册表<br/>ActionRegistry<br/>NodeRegistry"]
        M6["工厂<br/>ActionFactory<br/>NodeCreatorManager"]
        M7["单例<br/>AppConfig / EventBus<br/>Logger"]
        M8["策略<br/>parameter_widgets/"]
        M9["观察者<br/>PollingManager"]
        M10["编排器<br/>ShutdownOrchestrator"]
    end

    M1 --> M2 --> M3
    M4 --> M5 --> M6
    M7 --> M8
    M9 --> M10
```

---

> 本文档使用 Mermaid 语法生成，可在支持 Mermaid 的 Markdown 渲染器中直接查看图表。
