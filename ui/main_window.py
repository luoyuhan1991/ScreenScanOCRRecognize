import logging
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QSystemTrayIcon,
)

from config.config import config
from utils.hotkey import HotkeyManager
from .log_bridge import LogBridge
from .overlay import Overlay
from .pages.about_page import AboutPage
from .pages.scan_page import ScanPage
from .pages.settings_page import SettingsPage
from .roi_border import ROIBorder
from .scan_worker import ScanWorker
from .tray import TrayIcon
from .widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    # 热键回调跑在 keyboard 库的线程里，靠 Signal 跨线程转主线程（queued connection）
    _hotkey_start_requested = Signal()
    _hotkey_stop_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('屏幕扫描 OCR 识别系统')
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        outer_v = QVBoxLayout(central)
        outer_v.setContentsMargins(0, 0, 0, 0)
        outer_v.setSpacing(0)

        # 原生标题栏在浅色主题下为白色，与白色工作区融合。在标题栏正下方画一条
        # 1px 灰横线作为视觉分隔（颜色/粗细与 sidebar 右侧那条竖线统一）。
        title_sep = QFrame()
        title_sep.setObjectName('titleBarSeparator')
        title_sep.setFixedHeight(1)
        outer_v.addWidget(title_sep)

        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(64)  # 与 mockup 一致
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.scan_page = ScanPage()
        self.settings_page = SettingsPage()
        self.about_page = AboutPage()
        self.stack.addWidget(self.scan_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.about_page)
        layout.addWidget(self.stack, 1)

        outer_v.addWidget(body, 1)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        # 日志：logging.getLogger -> LogBridge -> LogPanel
        self.log_bridge = LogBridge()
        logging.getLogger().addHandler(self.log_bridge)
        logging.getLogger().setLevel(logging.INFO)
        self.log_bridge.record_emitted.connect(self.scan_page.log_panel.append)

        # 系统托盘（仅在系统支持时启用，否则关闭按钮就走原生退出）
        self._real_quit = False
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = TrayIcon(self)
            self.tray.show()

        # 屏幕浮窗（命中提示用）
        self.overlay = Overlay(config=config)
        # ROI 红框指示窗（扫描中显示在 ROI 区域上方）
        self.roi_border = ROIBorder()

        # 后台扫描线程
        self.worker = ScanWorker(self)
        self.worker.status_changed.connect(self._on_status_changed)
        self.worker.result_ready.connect(self.overlay.update)
        # 配置面板的启停按钮 → worker
        self.scan_page.config_panel.start_clicked.connect(self._on_start)
        self.scan_page.config_panel.stop_clicked.connect(self._on_stop)

        # 全局热键：Ctrl+Alt+1 开扫 / Ctrl+Alt+2 停扫。回调在库自己线程里跑，
        # 通过 Signal queued connection 中转到 Qt 主线程，避免直接跨线程操作 widget。
        self._hotkey_start_requested.connect(self._on_start)
        self._hotkey_stop_requested.connect(self._on_stop)
        self.hotkey = HotkeyManager()
        self.hotkey.register('ctrl+alt+1', self._hotkey_start_requested.emit, '开始扫描')
        self.hotkey.register('ctrl+alt+2', self._hotkey_stop_requested.emit, '停止扫描')

        # startup_mode='auto'：UI 渲染稳定后自动开扫（延 200ms 让事件循环先转一圈）
        if (config.get('app.startup_mode') or 'paused') == 'auto':
            QTimer.singleShot(200, self._on_start)

    # ---------- 扫描启停 ----------

    def _resolve_roi(self):
        """根据 config 决定本次启动用的 ROI。enable_roi=False → None（全屏）。"""
        if not bool(config.get('scan.enable_roi')):
            return None
        roi = config.get('scan.roi_rect')
        if isinstance(roi, list) and len(roi) == 4:
            return tuple(roi)
        return None

    def _on_start(self):
        if self.worker.isRunning():
            return
        roi = self._resolve_roi()
        self.overlay.clear_session()  # 新一轮扫描，清掉上一轮累计
        self.roi_border.show_for(roi)  # ROI 红框（roi=None 则不画）
        self.worker.start_scan(roi=roi)

    def _on_stop(self):
        self.worker.stop_scan()
        self.overlay.hide()
        self.roi_border.hide_border()

    def _on_status_changed(self, text):
        """worker 三态：'初始化中'/'运行中'/'已停止'。
        - 初始化中 / 运行中：start 禁、stop 启
        - 已停止：start 启、stop 禁
        - 状态栏文字也跟着切（颜色由 StatusBar 内 _STATUS_COLOR 表决定）"""
        self.scan_page.status_bar.set_status(text)
        running = text in ('初始化中', '运行中')
        self.scan_page.config_panel.set_running(running)

    def request_real_quit(self):
        """托盘 → 退出菜单调用，让随后的 closeEvent 不再拦截缩托盘。"""
        self._real_quit = True

    def closeEvent(self, event):
        """关闭按钮：若 app.minimize_to_tray=True 且托盘可用，则缩进托盘不退出。
        真正退出路径上清理 worker + 热键 + overlay。"""
        if (
            not self._real_quit
            and self.tray is not None
            and bool(config.get('app.minimize_to_tray'))
        ):
            event.ignore()
            self.hide()
            return
        # 真正退出
        try:
            self.hotkey.unregister_all()
        except Exception:
            pass
        try:
            if self.worker.isRunning():
                self.worker.stop_scan()
                self.worker.wait(2000)  # 给 worker 最多 2s 收尾
        except Exception:
            pass
        try:
            self.overlay.destroy()
        except Exception:
            pass
        try:
            self.roi_border.hide_border()
        except Exception:
            pass
        super().closeEvent(event)
