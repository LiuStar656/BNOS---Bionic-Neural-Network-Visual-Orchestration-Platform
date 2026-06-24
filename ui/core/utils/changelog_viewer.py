"""
更新日志查看器 — 根据当前语言读取 docs/changelogs/{cn|en}/README.md 并展示，
支持通过链接导航到其他 .md 文件。
"""
import os
from urllib.parse import unquote
import markdown
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from ui.core.i18n import t, get_lang


_STYLE_CONTAINER = "QWidget { background-color: rgba(30,30,30,220); border-radius: 8px; border: 1px solid rgba(255,255,255,25); }"
_STYLE_TITLE    = "color: white; font-size: 14px; font-weight: bold; background: transparent;"
_STYLE_INFO     = "color: rgba(255,255,255,120); font-size: 11px; background: transparent; padding: 2px 0;"
_STYLE_BACK_BTN = ("QPushButton { color: #4daafc; background: transparent; border: none; font-size: 11px; padding: 0 4px; } "
                   "QPushButton:hover { color: #ffffff; } "
                   "QPushButton:disabled { color: #555; }")

_HTML_CSS = """
body { background: #000000; color: #ffffff; font-size: 13px; line-height: 1.6; margin: 8px; }
h1 { color: #ffffff; font-size: 18px; border-bottom: 1px solid #555; padding-bottom: 6px; margin-top: 4px; }
h2 { color: #ffffff; font-size: 15px; margin-top: 14px; }
h3 { color: #ffffff; font-size: 14px; margin-top: 10px; }
a { color: #4daafc; text-decoration: none; }
strong { color: #ffffff; }
blockquote { border-left: 3px solid #555; padding-left: 10px; color: #ccc; margin: 8px 0; }
hr { border: none; border-top: 1px solid #444; margin: 12px 0; }
details { margin: 6px 0; }
summary { color: #ffffff; font-weight: bold; cursor: pointer; padding: 2px 0; }
summary:hover { color: #cccccc; }
p { margin: 4px 0; }
li { margin: 2px 0; color: #ffffff; }
code { background: #333; color: #e0a040; padding: 1px 4px; border-radius: 3px; }
table { border-collapse: collapse; margin: 8px 0; }
th, td { border: 1px solid #555; padding: 4px 10px; color: #ffffff; }
th { background: #222; }
"""


class ChangelogViewer(QDialog):
    """更新日志查看器 — 支持 .md 文件间导航"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(780, 580)
        self.setWindowTitle(t("k_menu_changelog"))

        self._history = []      # 导航历史栈
        self._base_dir = ""     # changelogs 根目录
        self._pending_url = None  # urlChanged 防重入

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget()
        self._container.setStyleSheet(_STYLE_CONTAINER)
        outer_layout.addWidget(self._container)

        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(4)

        # 标题栏
        title_bar = QHBoxLayout()
        self._title_label = QLabel(t("k_menu_changelog"))
        self._title_label.setStyleSheet(_STYLE_TITLE)
        title_bar.addWidget(self._title_label)
        title_bar.addStretch()

        close_label = QLabel("\u00d7")
        close_label.setStyleSheet(
            "color: rgba(255,255,255,150); font-size: 16px; padding:0 6px; background:transparent;")
        close_label.setCursor(Qt.CursorShape.PointingHandCursor)
        close_label.mousePressEvent = lambda e: self.reject()
        title_bar.addWidget(close_label)
        main_layout.addLayout(title_bar)

        # 导航栏
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(0, 0, 0, 0)
        nav_bar.setSpacing(2)

        self._back_btn = QPushButton("\u25c0")
        self._back_btn.setStyleSheet(_STYLE_BACK_BTN)
        self._back_btn.setFixedWidth(28)
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._go_back)
        nav_bar.addWidget(self._back_btn)

        self._breadcrumb = QLabel()
        self._breadcrumb.setStyleSheet(_STYLE_INFO)
        nav_bar.addWidget(self._breadcrumb, 1)
        nav_bar.addStretch()
        main_layout.addLayout(nav_bar)

        # Web 阅读区
        self._web_view = QWebEngineView()
        self._web_view.setStyleSheet(
            "background: #1e1e1e; border: 1px solid rgba(255,255,255,10); border-radius: 4px;")
        self._web_view.urlChanged.connect(self._on_url_changed)
        main_layout.addWidget(self._web_view, 1)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(t("k_ok"))
        close_btn.setStyleSheet("QPushButton { background: rgba(0,120,212,200); color: white; border: none; border-radius: 4px; padding: 6px 24px; } QPushButton:hover { background: rgba(0,140,240,220); }")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        main_layout.addLayout(btn_row)

        # 初始加载 — 延迟确保 WebEngine 就绪
        lang = get_lang()
        lang_dir = "cn" if lang == "cn" else "en"
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self._base_dir = os.path.join(base_dir, "docs", "changelogs", lang_dir)
        start_path = os.path.join(self._base_dir, "README.md")
        QTimer.singleShot(0, lambda: self.navigate_to(start_path))

    def _on_url_changed(self, url):
        """当用户点击 .md 链接时，拦截并用 markdown 渲染"""
        path = unquote(url.toLocalFile())
        if not path or not path.lower().endswith(".md"):
            return
        if not os.path.isfile(path):
            return
        # 防止 navigate_to → setHtml → urlChanged 循环
        if self._pending_url == path:
            return
        self._pending_url = path
        try:
            self.navigate_to(path)
        finally:
            self._pending_url = None

    def navigate_to(self, file_path):
        """导航到指定 .md 文件"""
        file_path = os.path.normpath(file_path)

        if not os.path.isabs(file_path) and self._history:
            current_dir = os.path.dirname(self._history[-1])
            file_path = os.path.normpath(os.path.join(current_dir, file_path))

        if not os.path.isfile(file_path):
            self._web_view.setHtml(f"<p style='color:#d4d4d4;'>文件不存在: {file_path}</p>")
            return

        self._history.append(file_path)
        self._render_file(file_path)
        self._update_nav()

    def _render_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            html_body = markdown.markdown(
                content,
                extensions=["extra", "sane_lists", "smarty"],
                output_format="html5",
            )
            html = f"<html><head><meta charset='utf-8'><style>{_HTML_CSS}</style></head><body>{html_body}</body></html>"
            self._web_view.setHtml(html, QUrl.fromLocalFile(file_path))
        except Exception:
            self._web_view.setHtml(f"<p style='color:#d4d4d4;'>{t('_k_changelog_read_error')}</p>")

    def _update_nav(self):
        self._back_btn.setEnabled(len(self._history) > 1)
        current = self._history[-1] if self._history else ""
        try:
            rel = os.path.relpath(current, self._base_dir)
        except ValueError:
            rel = current
        self._breadcrumb.setText(f"  {rel}")

    def _go_back(self):
        if len(self._history) <= 1:
            return
        self._history.pop()
        self._history.pop()
        prev = self._history[-1] if self._history else None
        if prev:
            self.navigate_to(prev)

    def exec(self):
        self._center_on_parent()
        return super().exec()

    def _center_on_parent(self):
        parent = self.parent()
        if parent and parent.isVisible():
            pc = parent.mapToGlobal(parent.rect().center())
            self.move(pc.x() - self.width() // 2, pc.y() - self.height() // 2)
        else:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.move(geo.center().x() - self.width() // 2,
                         geo.center().y() - self.height() // 2)


def show_changelog(parent=None):
    viewer = ChangelogViewer(parent)
    viewer.exec()
