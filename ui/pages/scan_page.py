from PySide6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QLabel, QFrame
)

from ui.widgets.config_panel import ConfigPanel
from ui.widgets.log_panel import LogPanel
from ui.widgets.status_bar import StatusBar


class ScanPage(QWidget):
    """三区域：左 = config_panel；右 = log_panel；底栏跨两列 = status_bar。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.config_panel = ConfigPanel()
        # 左侧配置区固定 360px，右侧日志区吃完剩余空间
        self.config_panel.setFixedWidth(360)

        self.log_panel = LogPanel()

        self.status_bar = StatusBar()
        self.status_bar.setFixedHeight(40)

        layout.addWidget(self.config_panel, 0, 0)
        layout.addWidget(self.log_panel, 0, 1)
        layout.addWidget(self.status_bar, 1, 0, 1, 2)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 1)
