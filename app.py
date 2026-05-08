"""
ScreenScanOCRRecognize — GUI 主程序入口。

实际逻辑在 src/gui/main_window.py 的 MainWindow 类。本入口只负责
建 Tk root + MainWindow 实例 + mainloop。
"""

import os
import sys
import tkinter as tk

# 项目根入 sys.path（src/config/config.py 也会做这一步，但放这里更显式）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.main_window import MainWindow


def main():
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
