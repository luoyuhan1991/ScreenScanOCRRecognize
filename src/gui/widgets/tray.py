"""
系统托盘图标（基于 pystray）。

setup_tray 失败（无 pystray / 无 PIL）时返回 None；调用方应优雅处理。
"""

import os
import sys
import threading

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.utils.logger import logger


def make_tray_icon_image():
    """生成 64x64 托盘图标。失败返回 None。"""
    try:
        from PIL import Image, ImageDraw
        w, h = 64, 64
        cx, cy = w // 2, h // 2
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r_outer = min(cx, cy) - 2
        draw.ellipse(
            [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
            fill=(20, 28, 36), outline=(0, 180, 120)
        )
        for i in range(1, 4):
            r = r_outer * i // 4
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                outline=(0, 200, 140), width=1
            )
        draw.line([cx, cy - r_outer, cx, cy + r_outer], fill=(0, 200, 140), width=1)
        draw.line([cx - r_outer, cy, cx + r_outer, cy], fill=(0, 200, 140), width=1)
        draw.pieslice(
            [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
            start=0, end=90,
            fill=(0, 180, 120, 100), outline=(0, 220, 160)
        )
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(0, 255, 170))
        return img
    except Exception:
        try:
            from PIL import Image
            return Image.new("RGBA", (64, 64), (0, 120, 80))
        except Exception:
            return None


class _TrayCtrl:
    """对外暴露的极小接口；只提供 stop()。"""
    def __init__(self, icon):
        self._icon = icon

    def stop(self):
        try:
            self._icon.stop()
        except Exception:
            pass


def setup_tray(root, on_show, on_quit, tooltip="屏幕扫描OCR识别"):
    """创建并启动系统托盘图标，返回控制对象或 None。"""
    try:
        import pystray
    except ImportError:
        logger.warning("未安装 pystray，托盘图标不可用")
        return None

    def _run_on_main(fn):
        try:
            root.after(0, fn)
        except Exception:
            pass

    image = make_tray_icon_image()
    if image is None:
        return None

    menu = pystray.Menu(
        pystray.MenuItem("显示主窗口", lambda: _run_on_main(on_show), default=True),
        pystray.MenuItem("退出", lambda: _run_on_main(on_quit)),
    )
    icon = pystray.Icon("screen_scan_ocr", image, tooltip, menu=menu)

    threading.Thread(target=icon.run, daemon=True).start()
    return _TrayCtrl(icon)


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.title("Tray demo")
    root.geometry("300x200")

    def show():
        root.deiconify()
        root.lift()

    def quit_():
        if tray:
            tray.stop()
        root.destroy()

    tray = setup_tray(root, on_show=show, on_quit=quit_, tooltip="Demo Tray")

    msg = "托盘已启动" if tray else "pystray 不可用，托盘未启动"
    tk.Label(root, text=msg).pack(pady=20)
    tk.Label(root, text="关窗口 → 主窗口隐藏到托盘\n右键托盘 → 选择「退出」").pack()

    if tray:
        root.protocol("WM_DELETE_WINDOW", lambda: root.withdraw())

    root.mainloop()
