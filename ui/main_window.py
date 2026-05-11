import logging

from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QSystemTrayIcon

from src.config.config import config
from .widgets.sidebar import Sidebar
from .pages.scan_page import ScanPage
from .pages.settings_page import SettingsPage
from .pages.about_page import AboutPage
from .log_bridge import LogBridge
from .tray import TrayIcon


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('屏幕扫描 OCR 识别系统')
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
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

    def request_real_quit(self):
        """托盘 → 退出菜单调用，让随后的 closeEvent 不再拦截缩托盘。"""
        self._real_quit = True

    def closeEvent(self, event):
        """关闭按钮：若 app.minimize_to_tray=True 且托盘可用，则缩进托盘不退出。"""
        if (
            not self._real_quit
            and self.tray is not None
            and bool(config.get('app.minimize_to_tray'))
        ):
            event.ignore()
            self.hide()
        else:
            super().closeEvent(event)
