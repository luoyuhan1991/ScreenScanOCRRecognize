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
        # mockup 比例 1fr : 1.05fr，给 config 设最小宽度并通过 stretch 控制最终比例
        self.config_panel.setMinimumWidth(380)

        self.log_panel = LogPanel()

        self.status_bar = StatusBar()
        self.status_bar.setFixedHeight(40)

        layout.addWidget(self.config_panel, 0, 0)
        layout.addWidget(self.log_panel, 0, 1)
        layout.addWidget(self.status_bar, 1, 0, 1, 2)
        # 配置 vs 日志 = 1 : 1.05（mockup 一致）
        layout.setColumnStretch(0, 100)
        layout.setColumnStretch(1, 105)
        layout.setRowStretch(0, 1)
