"""capture.grab() 在 enable_roi=False 时应忽略传入的 roi 参数，回退全屏。
不实际截屏，mock mss 的 grab 调用，验证 monitor 字典即可。"""

import os
import sys
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.config.config import config
from src.pipeline.capture import CaptureStage


def _mock_sct():
    import numpy as np
    sct = MagicMock()
    sct.monitors = [None, {'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]
    # 直接返回 ndarray；np.array(ndarray) 可走，[:, :, :3].copy() 也可走
    sct.grab = MagicMock(return_value=np.zeros((10, 10, 4), dtype=np.uint8))
    return sct


def test_enable_roi_false_forces_fullscreen():
    config.load()
    config.set('scan.enable_roi', False)
    cap = CaptureStage()
    with patch('src.pipeline.capture.mss.mss', return_value=_mock_sct()):
        cap.grab(roi=(100, 100, 500, 500))
    monitor = cap.sct.grab.call_args[0][0]
    assert monitor == cap.sct.monitors[1], f'未回退全屏，实际 monitor={monitor}'


def test_enable_roi_true_uses_roi():
    config.load()
    config.set('scan.enable_roi', True)
    cap = CaptureStage()
    with patch('src.pipeline.capture.mss.mss', return_value=_mock_sct()):
        cap.grab(roi=(100, 100, 500, 500))
    monitor = cap.sct.grab.call_args[0][0]
    # ROI 在 capture.py 里有 padding 外扩（默认 10 像素）
    assert monitor['width'] == 400 + 2 * 10, f'未应用 ROI（含 padding），实际 monitor={monitor}'


if __name__ == '__main__':
    test_enable_roi_false_forces_fullscreen()
    test_enable_roi_true_uses_roi()
    print('PASS')
