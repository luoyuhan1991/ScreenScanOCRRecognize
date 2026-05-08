"""
扫描时 ROI 区域的红色边框可视化（独立顶层窗，置顶、点击穿透）。

show(roi) 创建窗口，hide() 销毁。同时只能有一个边框窗存活。
"""

import os
import sys
import tkinter as tk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.utils.logger import logger


class RoiBorder:
    def __init__(self, parent_root, padding=10):
        self._parent = parent_root
        self._padding = padding
        self._win = None

    def show(self, roi):
        """显示 ROI 边框。roi=None 时按全屏画。"""
        self.hide()  # 幂等：先关旧的
        try:
            import ctypes
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)

            if roi:
                x1, y1, x2, y2 = roi
                x1 = max(0, x1 - self._padding)
                y1 = max(0, y1 - self._padding)
                x2 = min(sw, x2 + self._padding)
                y2 = min(sh, y2 + self._padding)
            else:
                x1, y1, x2, y2 = 0, 0, sw, sh

            w, h = x2 - x1, y2 - y1
            if w <= 0 or h <= 0:
                return

            win = tk.Toplevel(self._parent)
            win.withdraw()
            win.overrideredirect(True)
            win.attributes('-topmost', True)
            win.attributes('-transparentcolor', 'black')
            win.geometry(f'{w}x{h}+{x1}+{y1}')
            win.config(bg='black')

            c = tk.Canvas(win, width=w, height=h, bg='black',
                          highlightthickness=0, bd=0)
            c.pack(fill=tk.BOTH, expand=True)
            c.create_rectangle(1, 1, w - 1, h - 1,
                               outline='#ff3333', width=3, fill='')

            win.deiconify()
            self._win = win
        except Exception as e:
            logger.debug(f"ROI 边框显示失败: {e}")

    def hide(self):
        try:
            if self._win:
                self._win.destroy()
                self._win = None
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    root.title("RoiBorder demo")
    root.geometry("400x200+100+100")

    border = RoiBorder(root, padding=10)
    tk.Button(root, text="显示边框 (300,300)→(800,600)",
              command=lambda: border.show((300, 300, 800, 600))).pack(pady=8)
    tk.Button(root, text="显示全屏边框 (roi=None)",
              command=lambda: border.show(None)).pack(pady=8)
    tk.Button(root, text="隐藏", command=border.hide).pack(pady=8)

    root.mainloop()
