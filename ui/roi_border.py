"""ROI 红色边框指示窗：扫描中显示在 ROI 区域上方，让用户能看清扫的是哪一块。

无边框 + always-on-top + 鼠标穿透 + 透明背景，paintEvent 只画 1 圈红框。
"""
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


class ROIBorder(QWidget):
    """覆盖在 ROI 区域上的红框。show_for(rect) 显示，hide_border() 收。"""

    BORDER_WIDTH = 1
    BORDER_COLOR = QColor(229, 72, 77)  # 与 mockup --danger 同色

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hide()

    def show_for(self, rect):
        """rect: (x1, y1, x2, y2) 屏幕绝对像素 / None=全屏不画。"""
        if rect is None:
            self.hide()
            return
        x1, y1, x2, y2 = rect
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        self.setGeometry(QRect(x1, y1, w, h))
        self.show()
        self.raise_()

    def hide_border(self):
        self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        pen = QPen(self.BORDER_COLOR)
        pen.setWidth(self.BORDER_WIDTH)
        pen.setJoinStyle(Qt.MiterJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        # 边框画在内侧，避免 1px 被裁
        bw = self.BORDER_WIDTH
        p.drawRect(bw // 2, bw // 2,
                   self.width() - bw, self.height() - bw)
        p.end()
