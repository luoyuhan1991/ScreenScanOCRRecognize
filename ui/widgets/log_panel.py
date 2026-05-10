from PySide6.QtCore import Slot, Qt, QByteArray
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QPainter, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel, QFrame
)


_SVG_BROOM = b'''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"/>
  <path d="M19 6l-1.4 14a2 2 0 0 1-2 1.8H8.4a2 2 0 0 1-2-1.8L5 6"/>
</svg>'''


def _make_broom_icon(color='#475569'):
    svg = _SVG_BROOM.replace(b'currentColor', color.encode())
    renderer = QSvgRenderer(QByteArray(svg))
    pix = QPixmap(14, 14)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return QIcon(pix)


_LEVEL_COLORS = {
    'DEBUG': '#06B6D4',
    'INFO': '#16A34A',
    'WARNING': '#E0A82E',
    'ERROR': '#E5484D',
}


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header 用 QFrame 容器，便于 QSS 加底部 1px 分隔线
        header = QFrame()
        header.setObjectName('logHeader')
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(16, 0, 16, 0)
        header_l.setSpacing(0)
        title = QLabel('运行日志')
        title.setObjectName('logTitle')
        header_l.addWidget(title)
        header_l.addStretch(1)
        btn_clear = QPushButton(' 清空日志')
        btn_clear.setObjectName('logClear')
        btn_clear.setIcon(_make_broom_icon())
        btn_clear.clicked.connect(self._clear)
        header_l.addWidget(btn_clear)
        layout.addWidget(header)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(10000)
        self.text.setObjectName('logText')
        layout.addWidget(self.text, 1)

    @Slot(str, str)
    def append(self, level, message):
        color = _LEVEL_COLORS.get(level.upper(), '#1E293B')
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(message + '\n')
        self.text.setTextCursor(cursor)
        self.text.ensureCursorVisible()

    def _clear(self):
        self.text.clear()
