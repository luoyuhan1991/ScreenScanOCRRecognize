"""
ROI 交互选择：截屏 + 半透明全屏窗 + 拖拽矩形。

返回 (x1, y1, x2, y2) 或 None（用户按 ESC 取消时）。
"""

import os
import sys
import tkinter as tk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.utils.logger import logger


def select_roi_interactive(parent=None):
    """截屏后显示半透明全屏窗口，让用户拖选 ROI 矩形。

    Args:
        parent: tkinter 根窗口；非 None 时用 Toplevel + wait_window
                None 时独立 Tk + mainloop

    Returns:
        (x1, y1, x2, y2) 或 None
    """
    try:
        from PIL import ImageGrab, ImageTk
    except ImportError:
        logger.error("PIL 未安装，无法交互选择 ROI")
        return None

    screenshot = ImageGrab.grab()
    width, height = screenshot.size

    if parent is not None:
        win = tk.Toplevel(parent)
        use_wait = True
    else:
        win = tk.Tk()
        use_wait = False

    win.title("选择ROI区域 (按住拖动, ESC取消)")
    win.geometry(f"{width}x{height}")
    win.attributes('-fullscreen', True)
    win.attributes('-topmost', True)
    win.attributes('-alpha', 0.5)

    photo = ImageTk.PhotoImage(screenshot)
    canvas = tk.Canvas(win, width=width, height=height, cursor='crosshair')
    canvas.pack(fill='both', expand=True)
    canvas.photo = photo  # prevent GC
    canvas.create_image(0, 0, image=photo, anchor='nw')

    data = {'start': None, 'end': None, 'rect': None, 'done': False}

    def on_down(e):
        data['start'] = (e.x, e.y)
        data['end'] = None
        data['done'] = False

    def on_drag(e):
        if data['start']:
            data['end'] = (e.x, e.y)
            if data['rect']:
                canvas.delete(data['rect'])
            x1, y1 = data['start']
            data['rect'] = canvas.create_rectangle(
                x1, y1, e.x, e.y, outline='red', width=2
            )

    def on_up(e):
        if data['start']:
            data['end'] = (e.x, e.y)
            data['done'] = True
            win.destroy()

    def on_key(e):
        if e.keysym == 'Escape':
            data['done'] = False
            win.destroy()

    canvas.bind('<Button-1>', on_down)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_up)
    win.bind('<Key>', on_key)
    canvas.focus_set()

    if use_wait:
        win.wait_window()
    else:
        win.mainloop()

    try:
        screenshot.close()
    except Exception:
        pass

    if data['done'] and data['start'] and data['end']:
        x1, y1 = data['start']
        x2, y2 = data['end']
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        return (x1, y1, x2, y2)
    return None


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("将出现半透明全屏窗，拖选一个矩形或按 ESC 取消...")
    result = select_roi_interactive()
    if result:
        print(f"选择的 ROI: {result}")
    else:
        print("取消")
