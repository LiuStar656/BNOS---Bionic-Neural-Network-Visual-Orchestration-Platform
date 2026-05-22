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
QDialog QLabel { color: #cccccc; }
QDialog QLineEdit { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
QDialog QPushButton { background-color: #0e639c; color: white; border: none; border-radius: 3px; padding: 6px 14px; }
QDialog QPushButton:hover { background-color: #1177bb; }
QMessageBox { background-color: #252526; color: #cccccc; }
QMessageBox QLabel { color: #cccccc; font-size: 13px; }
QMessageBox QPushButton { background-color: #0e639c; color: white; border: none; border-radius: 3px; padding: 6px 18px; min-width: 80px; }
QMessageBox QPushButton:hover { background-color: #1177bb; }
QInputDialog { background-color: #252526; color: #cccccc; }
QInputDialog QLabel { color: #cccccc; }
QInputDialog QLineEdit { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
QInputDialog QPushButton { background-color: #0e639c; color: white; border: none; border-radius: 3px; padding: 6px 14px; }
QInputDialog QPushButton:hover { background-color: #1177bb; }
QFileDialog { background-color: #252526; }
QFileDialog QLabel { color: #cccccc; }
QFileDialog QLineEdit { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; }
QFileDialog QTreeView, QFileDialog QListView { background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c; }
QFileDialog QTreeView::item:selected, QFileDialog QListView::item:selected { background-color: #094771; }
QFileDialog QPushButton { background-color: #0e639c; color: white; border: none; border-radius: 3px; padding: 6px 14px; }
QFileDialog QPushButton:hover { background-color: #1177bb; }
QColorDialog { background-color: #252526; }
QColorDialog QLabel { color: #cccccc; }
QColorDialog QPushButton { background-color: #0e639c; color: white; border: none; border-radius: 3px; padding: 6px 14px; }
QColorDialog QPushButton:hover { background-color: #1177bb; }
QMenu { background-color: #252526; color: #cccccc; border: 1px solid #454545; padding: 4px 0; }
QMenu::item { padding: 6px 30px 6px 20px; }
QMenu::item:selected { background-color: #094771; }
QMenu::separator { height: 1px; background-color: #454545; margin: 4px 10px; }
QLabel { color: #cccccc; }
QLineEdit { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
QLineEdit:focus { border-color: #007acc; }
QComboBox { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
QComboBox::drop-down { border: none; }
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
