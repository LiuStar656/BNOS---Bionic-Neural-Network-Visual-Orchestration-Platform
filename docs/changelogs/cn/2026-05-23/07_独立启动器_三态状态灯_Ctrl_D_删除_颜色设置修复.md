# 🔄 独立启动器 + 三态状态灯 + Ctrl+D 删除 + 颜色设置修复

## 🔄 独立启动器 + 三态状态灯 + Ctrl+D 删除 + 颜色设置修复 (2026-05-23)

### 独立 tkinter 启动器

**替换**内嵌 PyQt6 闪屏为独立 `launcher.py`（251 行）：
- 纯 tkinter 实现，系统 Python 零依赖，可独立打包 EXE
- 闪屏立即弹出 → 后台启动 venv pythonw bnos_console.py → 实时读取进度文件
- 进度条平滑动画，与主程序加载精准同步，100% 后 0.2 秒关闭
- 启动脚本：`.vbs` 零窗口静默启动，`.bat` 备用
- 无 venv 时闪屏显示安装指引后退出

### 三态状态指示灯

| 颜色 | 状态 | 检测逻辑 |
|------|------|---------|
| 灰色 `#888` | 停止 | listener PID 不存在 |
| 绿色 `#44FF44` | 空闲 | listener 运行，无 main 子进程 |
| 红色 `#FF4444` | 运行 | listener + main 子进程都在运行 |

基于 `psutil` 进程树检测，零侵入节点代码。健康检测每 3 秒轮询，UI 全局适配 idle/running/stopped 三态。

### Ctrl+D 统一删除快捷键

`Ctrl+D` 根据焦点上下文：
- 节点列表面板 → 批量删除节点/组
- 画布框选节点 → 从画布移除
- 画布框选图形 → 删除绘图图形

右键删除与右键菜单冲突已移除，改为 Ctrl+D 统一删除。

### 颜色设置修复

- **画布背景**：`drawBackground` 直接 `painter.fillRect` 读取 `canvas_bg_color`，`resetCachedContent` + `repaint` 即时生效
- **颜色对话框**：改为 BNOS 深色主题 Frameless 窗口，可拖动，边框可见
- **key 名对齐**：`choose_color` 的 `canvas_bg` 与 `collect_settings` 的 `temp_canvas_bg_color` 统一

### 快捷键管理系统

新增 `ui/core/shortcut_manager.py`：11 个快捷键中心定义 + 持久化到 `app_config.json` + 设置面板可视化编辑 + 双击捕获新按键。

### 语言切换修复

修复 Python `from import LANG` 值拷贝 bug（新增 `get_lang()`）+ 重启改用 `exit(42)` 退出码驱动 + `AppConfig` 支持新键持久化。

### 影响文件

`launcher.py`(新增)、`node_process.py`、`node_style.py`、`canvas_colors.py`、`canvas_view.py`、`shortcut_manager.py`(新增)、`color_settings_dialog.py`、`settings_dialog.py`、`menu_manager.py`、`main_window.py`、`i18n.py`、`app_config.py`、`start_bnos_console.vbs`(新增)、启动脚本

---