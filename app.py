"""PySide6 入口。原 tkinter 实现已重命名为 app.py.tk_backup（迁移完成后删除）。"""

import os
import sys

from PySide6.QtWidgets import QApplication

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.config import config
from ui.main_window import MainWindow


def main():
    config.load()
    app = QApplication(sys.argv)
    qss_path = os.path.join(PROJECT_ROOT, 'ui', 'styles', 'light.qss')
    with open(qss_path, encoding='utf-8') as f:
        app.setStyleSheet(f.read())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
