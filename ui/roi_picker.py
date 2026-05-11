"""ROIPicker：全屏半透明遮罩 + 鼠标拖拽框选屏幕矩形。

调用方式：
    rect = ROIPicker().pick()    # 阻塞，回主屏坐标 (x1, y1, x2, y2) 或 None

设计要点
- 单屏：用 primaryScreen().geometry() 占满主屏，跨屏拖拽暂不处理。
- 透明遮罩：paintEvent 先填半透明黑，再用 CompositionMode_Clear 把选中矩形抠回透明，
  最后画蓝边 + 像素尺寸标签。WA_TranslucentBackground 让窗口本身是透明的，paint 自定。
- 阻塞返回：内部跑 QEventLoop，避免调用方写 Signal+回调。
- 取消手势：Esc / 右键 / 拖出尺寸 < 8px 都视作取消（最后这条防误点）。
"""

from PySide6.QtCore import Qt, QEventLoop, QPoint, QRect
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ROIPicker(QWidget):
    _MIN_SIZE = 8           # 矩形短边小于此值视作误点，整个 pick() 当取消处理
    _MASK_RGBA = (0, 0, 0, 110)
    _BORDER_COLOR = '#2F6FEB'
    _TAG_BG_RGBA = (0, 0, 0, 200)
    _TAG_TEXT = '#FFFFFF'

    def __init__(self):
        super().__init__()
        # Frameless + 置顶 + Tool（不占任务栏图标）
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        screen_geo = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        self._screen_offset = screen_geo.topLeft()  # 局部 → 屏幕坐标的偏移

        self._origin = None   # 拖拽起点（widget 局部）
        self._end = None      # 当前点（拖拽中或松开后）
        self._result = None   # 最终 (x1,y1,x2,y2) 或 None
        self._loop = None

    def pick(self):
        """阻塞调用：弹窗 → 返回 (x1,y1,x2,y2) 或 None。"""
        self.show()
        self.activateWindow()
        self.setFocus()
        self._loop = QEventLoop()
        self._loop.exec()
        return self._result

    # ---------- 绘制 ----------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        # 1. 半透明遮罩盖全屏
        p.fillRect(self.rect(), QColor(*self._MASK_RGBA))
        if not (self._origin and self._end):
            return

        r = QRect(self._origin, self._end).normalized()

        # 2. 把选中区抠回透明（CompositionMode_Clear）
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(r, Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # 3. 蓝色边框
        pen = QPen(QColor(self._BORDER_COLOR))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(r)

        # 4. 像素尺寸标签（黑底白字，挂在右下外侧；越界则改挂内侧）
        text = f'{r.width()} × {r.height()}'
        tag_w, tag_h = 80, 22
        tx = r.right() + 8
        ty = r.bottom() + 8
        if tx + tag_w > self.width():
            tx = r.right() - tag_w
        if ty + tag_h > self.height():
            ty = r.bottom() - tag_h - 4
        p.fillRect(tx, ty, tag_w, tag_h, QColor(*self._TAG_BG_RGBA))
        p.setPen(QColor(self._TAG_TEXT))
        p.drawText(tx, ty, tag_w, tag_h, Qt.AlignCenter, text)

    # ---------- 鼠标 ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.position().toPoint()
            self._end = self._origin
            self.update()
        elif event.button() == Qt.RightButton:
            self._cancel()

    def mouseMoveEvent(self, event):
        if self._origin is not None:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._origin is None:
            return
        self._end = event.position().toPoint()
        r = QRect(self._origin, self._end).normalized()
        if r.width() < self._MIN_SIZE or r.height() < self._MIN_SIZE:
            # 误点：直接取消
            self._cancel()
            return
        # widget 局部坐标 → 屏幕绝对坐标
        x1 = r.x() + self._screen_offset.x()
        y1 = r.y() + self._screen_offset.y()
        x2 = x1 + r.width()
        y2 = y1 + r.height()
        self._result = (x1, y1, x2, y2)
        self._finish()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._cancel()

    # ---------- 内部 ----------

    def _cancel(self):
        self._result = None
        self._finish()

    def _finish(self):
        self.hide()
        if self._loop is not None:
            self._loop.quit()
