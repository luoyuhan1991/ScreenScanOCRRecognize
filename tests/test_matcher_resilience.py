"""验证 matcher.load() 在 IO 失败时保留旧关键词。"""

import os
import sys
import tempfile
import unittest.mock as mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.matcher import SubstringMatcher


def test_load_failure_preserves_old_keywords():
    """文件打开失败时，已加载的关键词不应被清空。"""
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write('hello 提示一\nworld 提示二\n')
        path = f.name
    try:
        m = SubstringMatcher(banlist_file=path)
        m.load()
        assert len(m.keywords) == 2, f'初次加载应有 2 条，实际 {len(m.keywords)}'

        # 模拟 open() 失败（如记事本独占 PermissionError）
        with mock.patch('builtins.open', side_effect=PermissionError('locked')):
            # 改 mtime 强制 reload_if_changed 触发
            os.utime(path, (1, 1))
            m.match([{'text': 'hello world'}])

        assert len(m.keywords) == 2, (
            f'load 失败后关键词被清空：{m.keywords}'
        )
    finally:
        os.unlink(path)


if __name__ == '__main__':
    test_load_failure_preserves_old_keywords()
    print('PASS')
