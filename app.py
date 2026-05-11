"""PySide6 GUI 入口。tkinter 旧实现已在 PySide6 迁移完成后删除。"""

import os
import sys

from PySide6.QtWidgets import QApplication

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.config import config
from ui.main_window import MainWindow
from ui.tray import make_app_icon


def _set_windows_app_user_model_id():
    # Windows 按 AppUserModelID 给任务栏分组；不设的话 pythonw 启动会被归到 Python 解释器下、
    # 任务栏显示蟒蛇图标。必须在创建任何窗口前调用。
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'luoyuhan.screenscanocrrecognize.gui.1'
        )
    except Exception:
        pass


def main():
    _set_windows_app_user_model_id()
    config.load()
    app = QApplication(sys.argv)
    app.setWindowIcon(make_app_icon(256))
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
