"""自绘 sidebar：垂直堆叠的卡片按钮，每张卡 = SVG 图标 + 小字 label。
mockup 是 64px 窄栏 + 图标在上文字在下，QListWidget 难以精确还原，故改成自定义 QWidget。"""

from PySide6.QtCore import Qt, Signal, QByteArray
from PySide6.QtGui import QPainter, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel


# ----- SVG 图标（搬自 mockup HTML） -----
# 颜色用 currentColor，运行时通过两次渲染（gray / white）生成两套 pixmap

_SVG_SCAN = b'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="7"/>
  <circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none"/>
  <line x1="12" y1="2" x2="12" y2="4.5"/><line x1="12" y1="19.5" x2="12" y2="22"/>
  <line x1="2" y1="12" x2="4.5" y2="12"/><line x1="19.5" y1="12" x2="22" y2="12"/>
</svg>'''

_SVG_SETTINGS = b'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3
    1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.8.3l-.1.1
    a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1
    A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 9 4.6
    a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1A1.7 1.7 0 0 0 15 4.6a1.7 1.7 0 0 0 1.8-.3l.1-.1
    a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1
    a1.7 1.7 0 0 0-1.5 1z"/>
</svg>'''

_SVG_ABOUT = b'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="9.5"/>
  <line x1="12" y1="16" x2="12" y2="11.5"/>
  <circle cx="12" cy="8" r="0.6" fill="currentColor" stroke="none"/>
</svg>'''


def _render_svg_to_pixmap(svg_bytes, color, size=24):
    """把 currentColor 替换为目标颜色后渲染成 pixmap。
    用 4x oversample 再 smooth scale，避免低分辨率下笔画糊掉。"""
    svg = svg_bytes.replace(b'currentColor', color.encode())
    renderer = QSvgRenderer(QByteArray(svg))
    big = QPixmap(size * 4, size * 4)
    big.fill(Qt.transparent)
    p = QPainter(big)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(p)
    p.end()
    return big.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class _NavItem(QFrame):
    """单个 sidebar 项：图标 + 文字，点击切换。"""

    clicked = Signal(int)

    def __init__(self, index, label, svg_bytes, parent=None):
        super().__init__(parent)
        self._index = index
        self._active = False
        self.setObjectName('navItem')
        self.setCursor(Qt.PointingHandCursor)

        self._pix_inactive = _render_svg_to_pixmap(svg_bytes, '#475569', size=28)
        self._pix_active = _render_svg_to_pixmap(svg_bytes, '#FFFFFF', size=28)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self._icon = QLabel()
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setPixmap(self._pix_inactive)
        layout.addWidget(self._icon)

        self._text = QLabel(label)
        self._text.setAlignment(Qt.AlignCenter)
        self._text.setObjectName('navItemText')
        layout.addWidget(self._text)

    def set_active(self, active):
        if self._active == active:
            return
        self._active = active
        self._icon.setPixmap(self._pix_active if active else self._pix_inactive)
        # 重新触发 QSS 选择器
        self.setProperty('active', active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)


class Sidebar(QWidget):
    """三项导航：扫描 / 设置 / 关于。currentRowChanged Signal 兼容老 API。"""

    PAGE_SCAN = 0
    PAGE_SETTINGS = 1
    PAGE_ABOUT = 2

    currentRowChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('sidebar')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        self._items = []
        for idx, (label, svg) in enumerate((
            ('扫描', _SVG_SCAN),
            ('设置', _SVG_SETTINGS),
            ('关于', _SVG_ABOUT),
        )):
            item = _NavItem(idx, label, svg)
            item.clicked.connect(self._on_item_clicked)
            layout.addWidget(item)
            self._items.append(item)
        layout.addStretch(1)

        self._current = 0
        self._items[0].set_active(True)

    def _on_item_clicked(self, idx):
        if idx == self._current:
            return
        self._items[self._current].set_active(False)
        self._items[idx].set_active(True)
        self._current = idx
        self.currentRowChanged.emit(idx)

    def setCurrentRow(self, idx):
        self._on_item_clicked(idx)
