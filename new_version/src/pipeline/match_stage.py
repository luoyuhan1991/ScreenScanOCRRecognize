import os
import ahocorasick
from ..config.config import config
from ..utils.logger import logger


class MatchStage:
    def __init__(self):
        self._automaton = None
        self._keywords = {}       # {keyword_lower: {'original': str, 'hint': str}}
        self._file_path = None
        self._file_mtime = None

    def load(self, banlist_file=None):
        """加载关键词并构建自动机"""
        if banlist_file is None:
            banlist_file = config.get('matching.banlist_file', 'docs/banlist.txt')

        # 如果是相对路径，相对于 new_version 根目录解析
        if not os.path.isabs(banlist_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            banlist_file = os.path.join(base_dir, banlist_file)

        self._file_path = os.path.abspath(banlist_file)
        self._keywords = {}

        if not os.path.exists(self._file_path):
            logger.warning(f"关键词文件不存在: {self._file_path}")
            self._automaton = None
            return

        self._file_mtime = os.path.getmtime(self._file_path)

        with open(self._file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 1)
                keyword = parts[0]
                hint = parts[1].strip().lstrip(':').strip() if len(parts) > 1 else ''
                # 兼容冒号分隔
                if not hint and ':' in keyword:
                    k, h = keyword.split(':', 1)
                    keyword, hint = k.strip(), h.strip()
                if keyword:
                    self._keywords[keyword.casefold()] = {
                        'original': keyword,
                        'hint': hint
                    }

        # 构建 Aho-Corasick 自动机
        self._automaton = ahocorasick.Automaton()
        for kw_lower, info in self._keywords.items():
            self._automaton.add_word(kw_lower, info)
        if self._keywords:
            self._automaton.make_automaton()
        else:
            self._automaton = None

        logger.info(f"加载 {len(self._keywords)} 个关键词，自动机已构建")

    def _reload_if_changed(self):
        """文件变更时重新加载"""
        if self._file_path is None:
            self.load()
            return
        if not os.path.exists(self._file_path):
            return
        try:
            mtime = os.path.getmtime(self._file_path)
        except Exception:
            return
        if mtime != self._file_mtime:
            logger.info("关键词文件已变更，重新加载")
            self.load(self._file_path)

    def match(self, ocr_results):
        """
        匹配 OCR 结果中的关键词
        Args:
            ocr_results: list of dict with 'text' key
        Returns:
            list of dict: [{'keyword': str, 'hint': str, 'ocr_text': str}, ...]
        """
        self._reload_if_changed()

        if not self._automaton or not ocr_results:
            return []

        matches = []
        seen_keywords = set()

        for result in ocr_results:
            text = result.get('text', '')
            if not text:
                continue
            text_lower = text.casefold()

            for _, info in self._automaton.iter(text_lower):
                kw = info['original']
                if kw not in seen_keywords:
                    seen_keywords.add(kw)
                    matches.append({
                        'keyword': kw,
                        'hint': info['hint'],
                        'ocr_text': text
                    })

        if matches:
            logger.info(f"匹配到 {len(matches)} 个关键词")

        return matches
