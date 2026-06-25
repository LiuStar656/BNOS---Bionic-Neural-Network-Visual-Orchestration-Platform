"""
更新日志查看器 — 根据当前语言读取 docs/changelogs/{cn|en}/README.md 并展示，
支持通过链接导航到其他 .md 文件。使用 QTextBrowser 渲染。
"""
import os
import re
from html import escape
import markdown
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget, QTextBrowser
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QColor, QPalette
from ui.core.i18n import t, get_lang


_STYLE_CONTAINER = "QWidget { background-color: rgba(30,30,30,220); border-radius: 8px; border: 1px solid rgba(255,255,255,25); }"
_STYLE_TITLE    = "color: white; font-size: 14px; font-weight: bold; background: transparent;"
_STYLE_INFO     = "color: rgba(255,255,255,120); font-size: 11px; background: transparent; padding: 2px 0;"
_STYLE_BACK_BTN = ("QPushButton { color: #4daafc; background: transparent; border: none; font-size: 11px; padding: 0 4px; } "
                   "QPushButton:hover { color: #ffffff; } "
                   "QPushButton:disabled { color: #555; }")

_STYLE_BROWSER = """
QTextBrowser {
    background: #1e1e1e;
    border: 1px solid rgba(255,255,255,10);
    border-radius: 4px;
    color: #ffffff;
}
"""


class ChangelogViewer(QDialog):
    """更新日志查看器 — 支持 .md 文件间导航"""

    def __init__(self, parent=None, *, start_path=None, title=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(780, 580)
        self.setWindowTitle(title or t("k_menu_changelog"))

        self._history = []      # 导航历史栈
        self._base_dir = ""     # 根目录

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
        self._title_label = QLabel(title or t("k_menu_changelog"))
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

        # 浏览器
        self._browser = QTextBrowser()
        self._browser.setStyleSheet(_STYLE_BROWSER)
        # 消除闪白：viewport + document 默认暗色
        palette = self._browser.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        self._browser.setPalette(palette)
        self._browser.document().setDefaultStyleSheet("body { background: #1e1e1e; color: #fff; }")
        self._browser.setOpenExternalLinks(False)
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_anchor_clicked)
        # QTextBrowser 不支持 <details>，但有基本交互就够了
        main_layout.addWidget(self._browser, 1)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(t("k_ok"))
        close_btn.setStyleSheet("QPushButton { background: rgba(0,120,212,200); color: white; border: none; border-radius: 4px; padding: 6px 24px; } QPushButton:hover { background: rgba(0,140,240,220); }")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        main_layout.addLayout(btn_row)

        # 初始加载
        if start_path:
            self._base_dir = os.path.dirname(os.path.abspath(start_path))
            self.navigate_to(start_path)
        else:
            lang = get_lang()
            lang_dir = "cn" if lang == "cn" else "en"
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self._base_dir = os.path.join(base_dir, "docs", "changelogs", lang_dir)
            start_path = os.path.join(self._base_dir, "README.md")
            self.navigate_to(start_path)

    def _on_anchor_clicked(self, url):
        """处理链接点击 — .md 内部导航，其他用系统浏览器"""
        path = url.toLocalFile()
        if not path:
            # 外部链接用系统浏览器打开
            QDesktopServices.openUrl(url)
            return
        path = os.path.normpath(path)
        if path.lower().endswith(".md"):
            if os.path.isfile(path):
                self.navigate_to(path)
        elif os.path.isfile(path):
            QDesktopServices.openUrl(url)
        else:
            QDesktopServices.openUrl(url)

    def navigate_to(self, file_path):
        """导航到指定 .md 文件"""
        file_path = os.path.normpath(file_path)
        if not os.path.isabs(file_path) and self._history:
            current_dir = os.path.dirname(self._history[-1])
            file_path = os.path.normpath(os.path.join(current_dir, file_path))
        if not os.path.isfile(file_path):
            self._browser.setHtml(
                "<p style='color:#d4d4d4;'>文件不存在: " + escape(file_path) + "</p>")
            return
        self._history.append(file_path)
        self._render_file(file_path)
        self._update_nav()

    def _render_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 去除每行前导空格（README_CN.md 每行有缩进，会干扰 markdown 解析）
            content = "\n".join(line.lstrip() for line in content.split("\n"))
            # <div>/<details> → markdown="1" 让内部 Markdown 被解析
            content = re.sub(r'(<div\b[^>]*)(>)', r'\1 markdown="1"\2', content, flags=re.IGNORECASE)
            content = re.sub(r'(<details\b[^>]*)(>)', r'\1 markdown="1"\2', content, flags=re.IGNORECASE)
            html_body = markdown.markdown(
                content,
                extensions=["extra", "sane_lists"],
                output_format="html5",
            )
            # <details> → 展开的 div（QTextBrowser 不支持 HTML5 details）
            html_body = self._details_to_div(html_body)
            # shields.io 远程图片 → 彩色文字徽章（QTextBrowser 不支持远程图片）
            html_body = self._badge_to_span(html_body)
            # 本地相对路径 → file:/// 绝对路径
            html_body = self._absolutify_urls(html_body, file_path)
            html = ("<html><head><meta charset='utf-8'></head>"
                    + "<body style='background:#1e1e1e;color:#fff;font-size:13px;line-height:1.6;margin:8px;'>"
                    + html_body + "</body></html>")
            self._browser.setHtml(html)
        except Exception as e:
            import traceback
            self._browser.setHtml(
                "<pre style='color:red;'>ERROR: " + escape(str(e)) + "\n" + escape(traceback.format_exc()) + "</pre>")

    # ---- shields.io 颜色映射 ----
    _SHIELDS_COLORS = {
        "blue": "#007ec6", "yellow": "#dfb317", "orange": "#fe7d37",
        "green": "#97ca00", "red": "#e05d44", "brightgreen": "#4c1",
        "lightgrey": "#9f9f9f", "blueviolet": "#8834b4", "ff69b4": "#ff69b4",
        "success": "#97ca00", "important": "#fe7d37", "critical": "#e05d44",
        "informational": "#007ec6", "inactive": "#9f9f9f",
    }

    def _badge_to_span(self, html_body):
        """将 shields.io <img> 转为彩色文字徽章"""
        def _repl(m):
            alt = m.group("alt")
            src = m.group("src")
            # 从 URL 提取颜色: /badge/LABEL-COLOR?...
            color_match = re.search(r'-([a-z]+)(?:\?|$)', src)
            color_name = color_match.group(1) if color_match else "blue"
            bg = self._SHIELDS_COLORS.get(color_name, "#555")
            label = alt or src.rsplit("/", 1)[-1].rsplit("?", 1)[0]
            # 标签带 - 分隔的话取后半段作为显示
            if "-" in label and label.count("-") <= 3:
                label = label.rsplit("-", 1)[-1]
            return (f'<span style="display:inline-block;background:{bg};color:#fff;'
                    f'padding:1px 8px;border-radius:3px;font-size:11px;margin:1px 2px;'
                    f'font-weight:bold;vertical-align:middle;">{escape(label)}</span>')
        return re.sub(
            r'<img\s+alt="(?P<alt>[^"]*)"\s+src="(?P<src>https?://img\.shields\.io/[^"]+)"[^>]*/?>',
            _repl, html_body
        )

    def _details_to_div(self, html_body):
        """<details>/<summary> → 展开的 div（QTextBrowser 不支持 HTML5 details）"""
        html_body = re.sub(
            r'<details[^>]*>',
            '<div style="border:1px solid #444;border-radius:4px;margin:6px 0;padding:4px 10px;">',
            html_body
        )
        html_body = re.sub(
            r'<summary[^>]*>',
            '<div style="color:#4daafc;font-weight:bold;margin-bottom:4px;">',
            html_body
        )
        html_body = html_body.replace('</summary>', '</div>')
        html_body = html_body.replace('</details>', '</div>')
        return html_body

    def _absolutify_urls(self, html_body, md_file_path):
        """相对路径 → file:/// 绝对路径"""
        md_dir = os.path.dirname(md_file_path)

        def _make_abs(attr_val):
            if re.match(r'^(https?:|file:///|data:|#)', attr_val, re.IGNORECASE):
                return attr_val
            abs_path = os.path.normpath(os.path.join(md_dir, attr_val))
            return "file:///" + abs_path.replace("\\", "/")

        return re.sub(
            r'(src|href)="([^"]+)"',
            lambda m: f'{m.group(1)}="{_make_abs(m.group(2))}"',
            html_body
        )

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


def show_about_readme(parent=None):
    """显示关于 — 根据语言加载根目录 README_CN.md 或 README.md"""
    lang = get_lang()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if lang == "cn":
        path = os.path.join(base_dir, "README_CN.md")
    else:
        path = os.path.join(base_dir, "README.md")
    viewer = ChangelogViewer(parent, start_path=path, title=t("k_title_about"))
    viewer.exec()
