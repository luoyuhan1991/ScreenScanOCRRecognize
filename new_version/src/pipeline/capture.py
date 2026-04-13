import threading

import mss
import numpy as np
from ..config.config import config
from ..utils.logger import logger


class CaptureStage:
    def __init__(self):
        # mss 使用线程本地的 Windows 设备上下文，不能跨线程使用
        self.sct = None
        self._owner_thread = None

    def grab(self, roi=None):
        """
        截取屏幕区域
        Args:
            roi: (x1, y1, x2, y2) 或 None 全屏
        Returns:
            numpy BGR 数组
        """
        tid = threading.current_thread().ident
        if self.sct is None or self._owner_thread != tid:
            # 线程变更（如停止后重新开始），需要重建实例
            if self.sct is not None:
                try:
                    self.sct.close()
                except Exception:
                    pass
            self.sct = mss.mss()
            self._owner_thread = tid

        if roi is not None:
            x1, y1, x2, y2 = roi
            padding = config.get('scan.roi_padding', 10)
            monitor_info = self.sct.monitors[1]
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
            monitor = self.sct.monitors[1]

        img = self.sct.grab(monitor)
        # mss 返回 BGRA，去掉 alpha 得到 BGR
        frame = np.array(img)[:, :, :3].copy()
        return frame

    def close(self):
        if self.sct is not None:
            self.sct.close()
            self.sct = None
