"""
BNOS Toast通知测试脚本
用于验证右下角淡入淡出动画效果
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from ui.main_window import ToastNotification


class TestWindow(QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toast通知测试")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建测试按钮
        btn_info = QPushButton("显示Info通知")
        btn_info.clicked.connect(lambda: self.show_test_toast("info"))
        layout.addWidget(btn_info)
        
        btn_success = QPushButton("显示Success通知")
        btn_success.clicked.connect(lambda: self.show_test_toast("success"))
        layout.addWidget(btn_success)
        
        btn_warning = QPushButton("显示Warning通知")
        btn_warning.clicked.connect(lambda: self.show_test_toast("warning"))
        layout.addWidget(btn_warning)
        
        btn_error = QPushButton("显示Error通知")
        btn_error.clicked.connect(lambda: self.show_test_toast("error"))
        layout.addWidget(btn_error)
    
    def show_test_toast(self, toast_type):
        """显示测试Toast"""
        messages = {
            "info": "这是一条信息通知",
            "success": "操作成功！",
            "warning": "警告：请注意此操作",
            "error": "错误：操作失败"
        }
        
        toast = ToastNotification(
            message=messages[toast_type],
            parent=self,
            duration=3000,
            toast_type=toast_type
        )
        toast.show_toast()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
