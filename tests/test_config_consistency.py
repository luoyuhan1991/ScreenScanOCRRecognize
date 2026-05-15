"""验证 defaults 内部一致：roi_rect None ↔ last_roi_choice '__reselect__'。"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config.defaults import DEFAULT_CONFIG


def test_roi_rect_and_choice_consistent():
    scan = DEFAULT_CONFIG['scan']
    rect = scan['roi_rect']
    choice = scan['last_roi_choice']
    if rect is None:
        assert choice == '__reselect__', (
            f"roi_rect=None 时 last_roi_choice 应为 '__reselect__'，实际 {choice}"
        )
    else:
        assert choice != '__reselect__', (
            f"roi_rect 有具体值时 last_roi_choice 不应为 '__reselect__'"
        )


if __name__ == '__main__':
    test_roi_rect_and_choice_consistent()
    print('PASS')
