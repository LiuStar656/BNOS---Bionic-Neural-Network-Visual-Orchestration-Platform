# 🚀 启动动画 + 品牌重命名 BnosConsole + README 重构

## 🚀 启动动画 + 品牌重命名 BnosConsole + README 重构 (2026-05-23)

### 启动闪屏

新增 `ui/core/splash_screen.py`（114 行）：
- **ASCII 艺术 BNOS**：6 行 █ 字符拼成，Consolas 13pt 加粗，全黑白配色
- **BNOS CONSOLE** 副标题 + 项目描述（i18n）
- **左下角实时日志**：QTextEdit 80px，启动步骤追加滚动
- **底部进度条**：0→100%，灰色 chunk
- **延迟关闭**：主窗口打开 2 秒后自动消失

### 品牌重命名：BnosGui → BnosConsole

| 旧名称 | 新名称 |
|--------|--------|
| `bnos_gui.py` | `bnos_console.py` |
| `start_bnos_gui.bat` | `start_bnos_console.bat` |
| `start_bnos_gui.sh` | `start_bnos_console.sh` |
| `requirements_gui.txt` | `requirements.txt` |
| `"BnosGui"` 窗口标题 | `"BnosConsole"` |
| `logs/bnos_gui.log` | `logs/bnos_console.log` |
| `_k_app_name` | `"BNOS Console"` (中/英统一) |

影响文件 25+ 个，含 `main_window.py`、`dark_title_bar.py`、`logger.py`、`build_bnos.spec`、README、UPDATE、tests 等。

### 影响文件

`splash_screen.py`(新增)、`bnos_console.py`(重命名+闪屏延迟)、`strings_cn/en.json`、`main_window.py`、`dark_title_bar.py`、`logger.py`、`build_bnos.spec`、启动脚本、README、UPDATE、tests

---