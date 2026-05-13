from PySide6.QtCore import Slot, Qt, QByteArray
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QPainter, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel, QFrame,
    QSizePolicy,
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
    'DEBUG':   '#1E293B',  # mockup 普通文本（默认黑），DEBUG 不刻意上色避免喧宾夺主
    'INFO':    '#16A34A',
    'WARNING': '#E0A82E',
    'ERROR':   '#E5484D',
}

# 时间戳 / 分隔横线的颜色（mockup --log-time / --text-muted）
_TIME_COLOR = '#6B7280'
_ARROW_COLOR = '#94A3B8'

# "2026-05-10 18:03:47.031 - 实际消息..." 格式：把开头 "YYYY-MM-DD HH:MM:SS(.fff)" 当作 time
import re as _re
_TIME_RE = _re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)(\s+-\s+)(.*)$')


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # QSS 对裸 QWidget 的 background 要求 styled-background 属性
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName('logPanel')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header 用 QFrame 容器，便于 QSS 加底部 1px 分隔线
        header = QFrame()
        header.setObjectName('logHeader')
        header.setFixedHeight(40)
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
        btn_clear.setCursor(Qt.PointingHandCursor)
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
        """按 mockup 样式分段着色：时间戳灰 + " - " 浅灰 + 消息按 level 上色。
        消息开头若不带时间戳就整段按 level 着色，向下兼容。"""
        msg_color = _LEVEL_COLORS.get(level.upper(), '#1E293B')
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.End)

        m = _TIME_RE.match(message)
        if m:
            time_part, sep_part, body_part = m.group(1), m.group(2), m.group(3)
            self._insert_colored(cursor, time_part, _TIME_COLOR)
            self._insert_colored(cursor, sep_part, _ARROW_COLOR)
            self._insert_colored(cursor, body_part + '\n', msg_color)
        else:
            self._insert_colored(cursor, message + '\n', msg_color)

        self.text.setTextCursor(cursor)
        self.text.ensureCursorVisible()

    @staticmethod
    def _insert_colored(cursor, text, hex_color):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

    def _clear(self):
        self.text.clear()
