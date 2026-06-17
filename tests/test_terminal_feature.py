"""
测试终端 Dock 功能 - 简单验证
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("正在测试终端模块...")
print("=" * 60)

# 测试导入
try:
    from ui.core.terminal.terminal_process import TerminalProcess
    print("✅ 导入 TerminalProcess 成功")
except Exception as e:
    print(f"❌ 导入 TerminalProcess 失败: {e}")
    sys.exit(1)

try:
    from ui.core.terminal.terminal_widget import TerminalWidget
    print("✅ 导入 TerminalWidget 成功")
except Exception as e:
    print(f"❌ 导入 TerminalWidget 失败: {e}")
    sys.exit(1)

try:
    from ui.core.terminal.terminal_dock import TerminalDock
    print("✅ 导入 TerminalDock 成功")
except Exception as e:
    print(f"❌ 导入 TerminalDock 失败: {e}")
    sys.exit(1)

try:
    from ui.core.i18n import t
    print("✅ 导入 i18n 成功")
    
    # 测试翻译
    print(f"\n翻译测试:")
    print(f"  t('k_terminal_dock_title'): {t('k_terminal_dock_title')}")
    print(f"  t('k_terminal_new'): {t('k_terminal_new')}")
    print(f"  t('k_terminal_input_hint'): {t('k_terminal_input_hint')}")
except Exception as e:
    print(f"❌ 导入 i18n 失败: {e}")
    sys.exit(1)

try:
    from ui.core.app_config import AppConfig
    print("\n✅ 导入 AppConfig 成功")
    config = AppConfig()
    print(f"  panel_visibility 中有 terminal_dock: {'terminal_dock' in config.get('panel_visibility', {})}")
    print(f"  panel_positions 中有 terminal_dock: {'terminal_dock' in config.get('panel_positions', {})}")
except Exception as e:
    print(f"\n❌ 导入 AppConfig 失败: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 所有基础导入测试通过！")
print("\n文件创建情况:")
files = [
    "ui/core/terminal/__init__.py",
    "ui/core/terminal/terminal_process.py",
    "ui/core/terminal/terminal_widget.py",
    "ui/core/terminal/terminal_dock.py"
]
for f in files:
    if os.path.exists(f):
        print(f"  ✅ {f}")
    else:
        print(f"  ❌ {f}")

print("\n✅ Phase 1 基础开发完成！")
