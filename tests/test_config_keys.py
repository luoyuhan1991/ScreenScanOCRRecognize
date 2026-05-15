"""验证 ROI key 重命名后 defaults 里没有旧 key 'roi'，新 key 'roi_rect' 存在。"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.defaults import DEFAULT_CONFIG


def test_roi_renamed():
    scan = DEFAULT_CONFIG['scan']
    assert 'roi' not in scan, "旧 key 'roi' 仍存在，重命名未完成"
    assert 'roi_rect' in scan, "新 key 'roi_rect' 不存在"
    assert scan['roi_rect'] == [1136, 250, 1858, 850]


def test_enable_roi_intact():
    assert DEFAULT_CONFIG['scan']['enable_roi'] is True


def test_app_block_exists():
    from config.defaults import DEFAULT_CONFIG, APP_VERSION
    assert APP_VERSION == '1.0.0'
    assert DEFAULT_CONFIG['app']['minimize_to_tray'] is True
    assert DEFAULT_CONFIG['app']['startup_mode'] in ('paused', 'auto')


if __name__ == '__main__':
    test_roi_renamed()
    test_enable_roi_intact()
    test_app_block_exists()
    print('PASS')
