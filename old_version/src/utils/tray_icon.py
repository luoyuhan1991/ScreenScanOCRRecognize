"""
任务栏托盘图标
常见交互：左键显示/隐藏主窗口，右键菜单「显示主窗口」「退出」，最小化/关闭时缩到托盘。
"""

import logging
import threading

logger = logging.getLogger(__name__)


def _make_icon_image():
    """生成 64x64 托盘图标（PIL），雷达扫描风格，契合“屏幕扫描”"""
    try:
        from PIL import Image, ImageDraw
        w, h = 64, 64
        cx, cy = w // 2, h // 2
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 深色圆底（雷达屏）
        r_outer = min(cx, cy) - 2
        draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=(20, 28, 36), outline=(0, 180, 120))
        # 同心圆（距离环）
        for i in range(1, 4):
            r = r_outer * i // 4
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 200, 140), width=1)
        # 十字线
        draw.line([cx, cy - r_outer, cx, cy + r_outer], fill=(0, 200, 140), width=1)
        draw.line([cx - r_outer, cy, cx + r_outer, cy], fill=(0, 200, 140), width=1)
        # 雷达 sweep 扇形（约 90 度，从上方顺时针）
        draw.pieslice([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], start=0, end=90, fill=(0, 180, 120, 100), outline=(0, 220, 160))
        # 中心点
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(0, 255, 170))
        return img
    except Exception as e:
        logger.debug("生成托盘图标失败，使用简单图标: %s", e)
        try:
            from PIL import Image
            img = Image.new("RGBA", (64, 64), (0, 120, 80))
            return img
        except Exception:
            return None


def setup_tray(root, on_show, on_quit, tooltip="屏幕扫描OCR识别"):
    """
    创建并启动托盘图标（在后台线程运行）。
    左键或菜单「显示主窗口」调用 on_show，菜单「退出」调用 on_quit。

    Args:
        root: Tk 根窗口（on_show/on_quit 会通过 root.after(0, ...) 在主线程执行）
        on_show: 无参可调用对象，显示主窗口
        on_quit: 无参可调用对象，退出应用（需自行停止托盘并销毁窗口）
    Returns:
        tray 控制对象，有 .stop() 方法；若 pystray 不可用则返回 None
    """
    try:
        import pystray
    except ImportError:
        logger.warning("未安装 pystray，托盘图标不可用。可执行: pip install pystray")
        return None

    def run_on_main(fn):
        try:
            root.after(0, fn)
        except Exception:
            pass

    def show():
        run_on_main(on_show)

    def quit_app():
        run_on_main(on_quit)

    image = _make_icon_image()
    if image is None:
        return None

    menu = pystray.Menu(
        pystray.MenuItem("显示主窗口", show, default=True),
        pystray.MenuItem("退出", quit_app),
    )
    icon = pystray.Icon("screen_scan_ocr", image, tooltip, menu=menu)

    def run_icon():
        try:
            icon.run()
        except Exception as e:
            logger.debug("托盘图标线程结束: %s", e)

    thread = threading.Thread(target=run_icon, daemon=True)
    thread.start()

    class TrayController:
        def stop(self):
            try:
                icon.stop()
            except Exception:
                pass

    return TrayController()
