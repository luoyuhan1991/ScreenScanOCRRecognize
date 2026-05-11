"""系统托盘图标。
- 左键单击：显示并激活主窗口
- 右键菜单：显示主窗口 / 退出
- 关闭主窗口时（若 app.minimize_to_tray=True）由 MainWindow.closeEvent 拦截缩进托盘

图标复用 sidebar 的 bullseye scan SVG，运行时渲染成 32x32 PNG 当托盘图标。
"""
from PySide6.QtCore import Qt, QByteArray, QRectF
from PySide6.QtGui import QPainter, QPixmap, QIcon, QAction, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication


_TRAY_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
    stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="8"/>
    <circle cx="12" cy="12" r="3" fill="white" stroke="none"/>
    <line x1="12" y1="2"  x2="12" y2="5"/>
    <line x1="12" y1="19" x2="12" y2="22"/>
    <line x1="2"  y1="12" x2="5"  y2="12"/>
    <line x1="19" y1="12" x2="22" y2="12"/></svg>'''


def _render_tray_icon(size=32):
    """蓝底圆角 + 白色 bullseye。Windows 托盘默认 16/32 两档，渲 32 让缩 16 仍清晰。"""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    # 蓝底圆角矩形（与 sidebar active card 同色）
    p.setBrush(QColor('#2F6FEB'))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
    # 白色 bullseye 居中（占 70% 大小）
    inner = int(size * 0.7)
    off = (size - inner) // 2
    renderer = QSvgRenderer(QByteArray(_TRAY_SVG))
    renderer.render(p, QRectF(off, off, inner, inner))
    p.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    """托盘图标 + 右键菜单 + 左键激活。"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self._main_window = main_window
        self.setIcon(_render_tray_icon(32))
        self.setToolTip('屏幕扫描 OCR 识别系统')

        menu = QMenu()
        act_show = QAction('显示主窗口', menu)
        act_show.triggered.connect(self._on_show)
        menu.addAction(act_show)
        menu.addSeparator()
        act_quit = QAction('退出', menu)
        act_quit.triggered.connect(self._on_quit)
        menu.addAction(act_quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        # 左键单击 / 双击都视为"显示主窗口"
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._on_show()

    def _on_show(self):
        w = self._main_window
        if w.isMinimized():
            w.showNormal()
        else:
            w.show()
        w.raise_()
        w.activateWindow()

    def _on_quit(self):
        # 通知 MainWindow 走真正退出路径，让 closeEvent 不再拦截缩托盘
        if hasattr(self._main_window, 'request_real_quit'):
            self._main_window.request_real_quit()
        QApplication.instance().quit()
