import mss
import numpy as np
from ..config.config import config
from ..utils.logger import logger


class CaptureStage:
    def __init__(self):
        pass

    def grab(self, roi=None):
        """
        截取屏幕区域
        Args:
            roi: (x1, y1, x2, y2) 或 None 全屏
        Returns:
            numpy BGR 数组
        """
        # mss 在 Windows 上使用线程本地的设备上下文（srcdc），
        # 不能跨线程复用实例，每次用 context manager 确保安全
        with mss.mss() as sct:
            if roi is not None:
                x1, y1, x2, y2 = roi
                padding = config.get('scan.roi_padding', 10)
                monitor_info = sct.monitors[1]
                sw, sh = monitor_info['width'], monitor_info['height']
                x1 = max(0, x1 - padding)
                y1 = max(0, y1 - padding)
                x2 = min(sw, x2 + padding)
                y2 = min(sh, y2 + padding)
                monitor = {
                    "left": x1, "top": y1,
                    "width": x2 - x1, "height": y2 - y1
                }
            else:
                monitor = sct.monitors[1]

            img = sct.grab(monitor)
            # mss 返回 BGRA，去掉 alpha 得到 BGR
            frame = np.array(img)[:, :, :3].copy()
            return frame

    def close(self):
        pass
