## 🎨 功能更新：方形节点实时状态显示 (2026-06-06)

### 新增功能
- **方形节点实时状态监控**：实现了方形节点的CPU、内存、运行时长实时显示功能
- **资源监控模块**：新增`node_monitor.py`模块，实时收集节点进程的资源使用情况
- **状态显示组件**：创建`node_status_widget.py`组件，可视化展示节点状态信息

### 技术实现
1. **状态显示UI**：
   - CPU占用率显示（含进度条）
   - 内存使用量显示（含进度条）
   - 运行时长计时器
   - 彩色编码：CPU(青色)、内存(红色)、时长(黄色)

2. **监控机制**：
   - 使用psutil库获取系统进程信息
   - 每2秒自动更新一次状态
   - 仅更新画布可见区域内的节点
   - 自动管理节点的添加/移除/更新

3. **样式扩展**：
   - 在`node_style.py`中添加状态显示相关属性
   - 方形节点默认启用状态显示
   - 支持样式切换时自动开启/关闭状态显示

### 文件修改
- `ui/canvas/items/node_style.py`：添加状态显示属性
- `ui/canvas/items/node_item.py`：集成状态显示组件
- `ui/canvas/items/node_status_widget.py`：新增状态显示组件
- `ui/core/node_monitor.py`：新增节点监控模块

### 功能特性
- ✅ 实时显示CPU使用率（0-100%）
- ✅ 实时显示内存使用量（MB）
- ✅ 实时显示运行时长（HH:MM:SS）
- ✅ 进度条可视化资源占用情况
- ✅ 仅更新可见区域内的节点，优化性能
- ✅ 支持节点样式切换时自动适配
- ✅ 与现有节点状态指示灯联动

## 🔧 代码健壮性修复 (2026-06-06)

### 修复内容
- **QTimer导入问题**：在canvas_view.py中添加注释明确QTimer已在文件顶部导入
- **动画帧处理缩进**：优化toast_notification.py中动画处理代码的缩进和可读性
- **README渲染问题**：修复README.md中表格和项目结构的渲染格式

### 文件修改
- `ui/canvas/canvas_view.py`：添加QTimer导入注释
- `ui/core/toast/toast_notification.py`：优化动画代码格式
- `README.md`：统一表格格式和项目结构显示

## 🎨 Toast 通知视觉效果全面修复 (2026-06-06)

### 问题修复
1. **黑色边框问题**：
   - 问题：圆角窗口边缘出现黑色方框
   - 修复：采用双层架构，外层QWidget仅设置WA_TranslucentBackground，内层QLabel承载样式
   - 文件：`ui/core/toast/toast_notification.py`

2. **半透明效果**：
   - 问题：窗口未实现半透明效果
   - 修复：移除WA_StyledBackground和setAutoFillBackground(True)设置，确保窗口直接以半透明圆角样式显示
   - 文件：`ui/core/toast/toast_notification.py`

3. **消失动画**：
   - 问题：消失动画不是平滑的渐隐效果
   - 修复：使用QTimer驱动setWindowOpacity()实现线性淡入淡出动画，替代QGraphicsOpacityEffect
   - 文件：`ui/core/toast/toast_notification.py`

### 技术实现
- **双层架构**：外层透明窗口（QWidget）+ 内层承载样式的QLabel
- **动画优化**：使用QTimer和setWindowOpacity()实现平滑的渐隐效果，动画时长约300ms
- **兼容性**：避免了QGraphicsOpacityEffect在Tool窗口上与WA_TranslucentBackground的兼容性问题

### 验收标准
- ✅ 窗口直接以半透明圆角样式显示，无黑色边框
- ✅ 显示/消失动画平滑自然，时长约300ms
- ✅ 在不同设备和系统版本上测试验证通过
- ✅ 不影响现有功能和接口兼容性

### 文件修改
- `ui/core/toast/toast_notification.py`：重构Toast通知组件实现
- `docs/UPDATE_CN.md`：添加本次修复记录
- `docs/UPDATE_EN.md`：添加英文版本修复记录

---

*最后更新：2026-06-06*