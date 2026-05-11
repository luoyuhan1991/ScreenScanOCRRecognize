"""SettingsPage 用到的可复用控件：
- SwitchToggle：mockup .switch 36×20 药丸开关，QSS 不支持，自绘 paintEvent
- SettingsCard：mockup .settings-card 白底圆角卡片
- SettingsRow：HBox 行 [label][控件]，相邻 row 之间画 1px 灰底分隔线
- HotkeyDisplay：[kbd 标签][编辑铅笔]，只读展示当前热键
"""
import os

from PySide6.QtCore import Qt, Signal, QByteArray, QSize
from PySide6.QtGui import QPainter, QColor, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
)

from config.config import PROJECT_ROOT

_ICON_DIR = os.path.join(PROJECT_ROOT, 'ui', 'icons')


def _svg_icon(filename, color, size=14):
    """读 SVG，把 currentColor 替换成目标颜色后渲染成 QIcon。"""
    with open(os.path.join(_ICON_DIR, filename), 'rb') as f:
        data = f.read().replace(b'currentColor', color.encode())
    renderer = QSvgRenderer(QByteArray(data))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(p)
    p.end()
    return QIcon(pix)


class SwitchToggle(QWidget):
    """36×20 药丸开关。off=#CBD5E1，on=#2F6FEB；内圈白色 16×16 滑块。
    QSS 没有这种东西，paintEvent 自绘。点击切换并发 toggled(bool)。"""

    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = bool(checked)
        self.setFixedSize(36, 20)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        # 药丸轨道
        track_color = QColor('#2F6FEB' if self._checked else '#CBD5E1')
        p.setPen(Qt.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(0, 0, 36, 20, 10, 10)
        # 内圆滑块
        x = 18 if self._checked else 2
        p.setBrush(QColor('#FFFFFF'))
        p.drawEllipse(x, 2, 16, 16)
        p.end()


class SettingsCard(QFrame):
    """mockup .settings-card：白底 + 1px 灰边 + 圆角 + 14/16 内边距。
    用法：card = SettingsCard('常规设置'); card.add_row(SettingsRow(...))"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName('settingsCard')
        self._box = QVBoxLayout(self)
        self._box.setContentsMargins(16, 14, 16, 14)
        self._box.setSpacing(0)
        title_lbl = QLabel(title)
        title_lbl.setObjectName('settingsCardTitle')
        self._box.addWidget(title_lbl)
        self._box.addSpacing(4)

    def add_row(self, row_widget):
        """添加一行 row。第二行起会在顶部自动画 1px 灰分隔线（mockup
        .settings-row + .settings-row { border-top }）。"""
        self._box.addWidget(row_widget)


class SettingsRow(QFrame):
    """单行：左侧文字 label + 右侧控件。
    - with_separator：True 顶部画 1px 灰分隔线
    - expand_control：True 时控件占据 label 右侧所有剩余空间（slider 用）；
      False 时 stretch 在中间，控件靠右紧凑显示（switch / combo 用）
    """

    def __init__(self, label_text, control_widget,
                 with_separator=True, expand_control=False, parent=None):
        super().__init__(parent)
        self.setObjectName('settingsRowSep' if with_separator else 'settingsRow')
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 8, 0, 8)
        h.setSpacing(8)
        if label_text is not None:
            lbl = QLabel(label_text)
            lbl.setObjectName('settingsRowLabel')
            h.addWidget(lbl)
        if expand_control:
            # slider 行：label 后直接接控件，控件 stretch 1 占满剩余宽度
            if control_widget is not None:
                h.addWidget(control_widget, 1)
        else:
            # 普通行：[label][stretch][控件靠右]
            h.addStretch(1)
            if control_widget is not None:
                h.addWidget(control_widget)


class HintRow(QFrame):
    """只放一段浅灰 hint 文字（mockup `.hint`），无分隔线、内边距更紧凑。"""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName('settingsHintRow')
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 6)
        h.setSpacing(0)
        lbl = QLabel(text)
        lbl.setObjectName('settingsHint')
        h.addWidget(lbl)
        h.addStretch(1)


class HotkeyDisplay(QFrame):
    """[kbd 标签][铅笔编辑按钮]。展示当前热键、点击铅笔进入编辑（占位空槽，
    具体编辑流由 T23 HotkeyManager 接入）。"""

    edit_clicked = Signal()

    def __init__(self, hotkey_text, parent=None):
        super().__init__(parent)
        self.setObjectName('hotkeyDisplay')
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.kbd = QLabel(hotkey_text)
        self.kbd.setObjectName('kbd')
        h.addWidget(self.kbd)
        self.btn_edit = QPushButton()
        self.btn_edit.setObjectName('hotkeyEdit')
        self.btn_edit.setIcon(_svg_icon('pencil.svg', '#94A3B8', size=14))
        self.btn_edit.setIconSize(QSize(14, 14))
        self.btn_edit.setFixedSize(24, 24)
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.clicked.connect(self.edit_clicked.emit)
        h.addWidget(self.btn_edit)

    def set_hotkey(self, text):
        self.kbd.setText(text)


def make_reset_button(text='重置配置'):
    """红边白底红字按钮（mockup .reset-btn），左侧带 rotate-ccw 图标。"""
    btn = QPushButton(' ' + text)
    btn.setObjectName('resetBtn')
    btn.setIcon(_svg_icon('rotate-ccw.svg', '#E5484D', size=14))
    btn.setIconSize(QSize(14, 14))
    btn.setCursor(Qt.PointingHandCursor)
    return btn
