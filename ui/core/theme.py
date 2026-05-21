"""
BNOS 深色主题 — VSCode 风格全局样式表
"""
DARK_QSS = """
QMainWindow { background-color: #1e1e1e; border: 2px solid #1e1e1e; }
QWidget#centralWidget { background-color: #1e1e1e; border: none; }
QScrollBar:horizontal, QScrollBar:vertical { background-color: #1e1e1e; border: none; }
QScrollBar:horizontal { height: 10px; } QScrollBar:vertical { width: 10px; }
QScrollBar::handle:horizontal, QScrollBar::handle:vertical { background-color: #424242; border-radius: 5px; min-width: 30px; min-height: 30px; }
QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover { background-color: #555555; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QDialog { background-color: #252526; color: #cccccc; }
QMessageBox { background-color: #252526; color: #cccccc; }
QLabel { color: #cccccc; }
QLineEdit { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
QLineEdit:focus { border-color: #007acc; }
QComboBox { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
QComboBox QAbstractItemView { background-color: #252526; color: #cccccc; selection-background-color: #094771; }
QPushButton { background-color: #0e639c; color: white; border: 1px solid #0e639c; border-radius: 3px; padding: 6px 14px; }
QPushButton:hover { background-color: #1177bb; }
QPushButton:pressed { background-color: #094771; }
QGroupBox { color: #cccccc; border: 1px solid #454545; border-radius: 4px; margin-top: 12px; padding-top: 18px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QTreeWidget { background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c; alternate-background-color: #2d2d2d; }
QTreeWidget::item:selected { background-color: #094771; } QTreeWidget::item:hover { background-color: #2a2d2e; }
QHeaderView::section { background-color: #252526; color: #cccccc; border: none; border-right: 1px solid #3c3c3c; border-bottom: 1px solid #3c3c3c; padding: 4px 8px; }
QTableWidget { background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c; gridline-color: #3c3c3c; }
QTableWidget::item:selected { background-color: #094771; }
QTextEdit, QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; }
QTabWidget::pane { background-color: #1e1e1e; border: 1px solid #3c3c3c; }
QTabBar::tab { background-color: #2d2d2d; color: #cccccc; padding: 8px 16px; border: none; border-right: 1px solid #3c3c3c; }
QTabBar::tab:selected { background-color: #1e1e1e; border-top: 2px solid #007acc; } QTabBar::tab:hover { background-color: #3a3a3a; }
QToolTip { background-color: #383838; color: #cccccc; border: 1px solid #555555; padding: 4px 8px; font-size: 12px; }
QSplitter::handle { background-color: #3c3c3c; width: 2px; } QSplitter::handle:hover { background-color: #007acc; }
QProgressBar { background-color: #3c3c3c; color: white; border: none; border-radius: 2px; text-align: center; }
QProgressBar::chunk { background-color: #0e639c; border-radius: 2px; }
"""
