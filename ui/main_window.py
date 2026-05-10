import logging

from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget

from .widgets.sidebar import Sidebar
from .pages.scan_page import ScanPage
from .pages.settings_page import SettingsPage
from .pages.about_page import AboutPage
from .log_bridge import LogBridge


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
