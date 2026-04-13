import cv2
import numpy as np
from ..config.config import config
from ..utils.logger import logger


class DiffGate:
    def __init__(self):
        self._prev_gray = None
        self._thumb_size = (160, 120)

    def should_skip(self, frame_bgr):
        """
        比较当前帧与上一帧，返回 True 表示画面没变应跳过
        Args:
            frame_bgr: numpy BGR 数组
        Returns:
            bool
        """
        threshold = config.get('scan.diff_threshold', 5.0)

        # 缩放为灰度缩略图
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        thumb = cv2.resize(gray, self._thumb_size, interpolation=cv2.INTER_AREA)

        if self._prev_gray is None:
            self._prev_gray = thumb
            return False

        # 均方差
        diff = np.mean(
            (thumb.astype(np.float32) - self._prev_gray.astype(np.float32)) ** 2
        )
        self._prev_gray = thumb

        if diff < threshold:
            logger.debug(f"帧差 {diff:.2f} < {threshold}，跳过 OCR")
            return True

        logger.debug(f"帧差 {diff:.2f} >= {threshold}，执行 OCR")
        return False

    def reset(self):
        self._prev_gray = None
