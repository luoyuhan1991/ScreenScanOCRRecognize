"""把 logging.Handler 的输出桥到 PySide6 Signal。
worker QThread 也可以通过它发送日志（间接经由 logging.getLogger）。"""

import logging

from PySide6.QtCore import QObject, Signal


class LogBridge(QObject, logging.Handler):
    record_emitted = Signal(str, str)  # (level_name, formatted_message)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        fmt = logging.Formatter(
            '%(asctime)s.%(msecs)03d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        self.setFormatter(fmt)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.record_emitted.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)
