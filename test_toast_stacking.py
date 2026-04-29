"""
测试Toast通知堆叠显示功能

运行此脚本将演示：
1. 连续显示多个Toast通知
2. Toast自动向上堆叠
3. 超过3个时，最旧的自动淡出
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import BNOSMainWindow


def test_toast_stacking():
    """测试Toast堆叠功能"""
    app = QApplication(sys.argv)
    
    # 创建主窗口（隐藏）
    window = BNOSMainWindow()
    window.show()
    
    # 延迟1秒后开始测试
    def start_test():
        print("🧪 开始测试Toast堆叠功能...")
        print("📌 规则：最多显示3个，新Toast出现时旧的上移，超过3个最旧的淡出")
        
        # 第1个Toast - 立即显示
        window.show_toast("🔔 第1条通知 - 这是最早的通知", "info", 8000)
        print("✅ 显示第1条通知")
        
        # 第2个Toast - 1秒后显示
        QTimer.singleShot(1000, lambda: [
            window.show_toast("✨ 第2条通知 - 第1条应该上移", "success", 8000),
            print("✅ 显示第2条通知")
        ])
        
        # 第3个Toast - 2秒后显示
        QTimer.singleShot(2000, lambda: [
            window.show_toast("⚠️ 第3条通知 - 现在有3个了", "warning", 8000),
            print("✅ 显示第3条通知（已达最大数量）")
        ])
        
        # 第4个Toast - 3秒后显示（第1个应该淡出）
        QTimer.singleShot(3000, lambda: [
            window.show_toast("❌ 第4条通知 - 第1条正在淡出...", "error", 8000),
            print("✅ 显示第4条通知（第1条应该自动淡出）")
        ])
        
        # 第5个Toast - 4秒后显示（第2个应该淡出）
        QTimer.singleShot(4000, lambda: [
            window.show_toast("🎉 第5条通知 - 第2条正在淡出...", "success", 8000),
            print("✅ 显示第5条通知（第2条应该自动淡出）")
        ])
        
        # 第6个Toast - 5秒后显示（第3个应该淡出）
        QTimer.singleShot(5000, lambda: [
            window.show_toast("🚀 第6条通知 - 第3条正在淡出...", "info", 8000),
            print("✅ 显示第6条通知（第3条应该自动淡出）")
        ])
        
        print("\n👀 请观察右下角的Toast通知堆叠效果！")
        print("   - 新Toast出现在底部")
        print("   - 旧Toast自动向上移动")
        print("   - 最多同时显示3个")
    
    # 启动测试
    QTimer.singleShot(1000, start_test)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_toast_stacking()
