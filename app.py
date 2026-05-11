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
    icon_dir = os.path.join(PROJECT_ROOT, 'ui', 'icons').replace('\\', '/')
    with open(qss_path, encoding='utf-8') as f:
        # QSS 中用 {ICON_DIR}/xxx.svg 引用，运行时替换成绝对路径（跨工作目录稳定）
        app.setStyleSheet(f.read().replace('{ICON_DIR}', icon_dir))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
