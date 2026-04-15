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

    @staticmethod
    def _match_ratio(keyword_cf, text_cf):
        """
        计算关键词在文本中的比例匹配分数。
        按顺序查找关键词中每个字符在文本中出现的比例。
        用于容忍 OCR 误识别（如 "张三" OCR 为 "张.三" 仍能匹配）。

        Args:
            keyword_cf: casefold 后的关键词
            text_cf: casefold 后的 OCR 文本
        Returns:
            float: 0.0~1.0
        """
        if not keyword_cf:
            return 1.0
        if not text_cf:
            return 0.0
        pos = 0
        matched = 0
        for c in keyword_cf:
            i = text_cf.find(c, pos)
            if i != -1:
                matched += 1
                pos = i + 1
        return matched / len(keyword_cf)

    def match(self, ocr_results):
        """
        匹配 OCR 结果中的关键词。
        优先使用 Aho-Corasick 精确子串匹配；
        未命中时回退到比例匹配（容忍 OCR 误识别）。

        Args:
            ocr_results: list of dict with 'text' key
        Returns:
            list of dict: [{'keyword': str, 'hint': str, 'ocr_text': str}, ...]
        """
        self._reload_if_changed()

        if not self._keywords or not ocr_results:
            return []

        matches = []
        seen_keywords = set()

        # 提取并预处理 OCR 文本
        ocr_items = []
        for result in ocr_results:
            text = result.get('text', '')
            if text:
                ocr_items.append((text, text.casefold()))

        if not ocr_items:
            return []

        # 第一轮：Aho-Corasick 精确子串匹配
        if self._automaton:
            for text, text_lower in ocr_items:
                for _, info in self._automaton.iter(text_lower):
                    kw = info['original']
                    if kw not in seen_keywords:
                        seen_keywords.add(kw)
                        matches.append({
                            'keyword': kw,
                            'hint': info['hint'],
                            'ocr_text': text
                        })

        # 第二轮：比例匹配（仅对第一轮未命中的关键词）
        ratio_threshold = float(config.get('matching.match_ratio_threshold', 0.75))
        if ratio_threshold < 1.0:
            for kw_lower, info in self._keywords.items():
                kw = info['original']
                if kw in seen_keywords:
                    continue
                for text, text_lower in ocr_items:
                    ratio = self._match_ratio(kw_lower, text_lower)
                    if ratio >= ratio_threshold:
                        seen_keywords.add(kw)
                        matches.append({
                            'keyword': kw,
                            'hint': info['hint'],
                            'ocr_text': text
                        })
                        logger.info(f"比例匹配: '{kw}' (比例={ratio:.0%}, OCR: '{text}')")
                        break

        if matches:
            logger.info(f"匹配到 {len(matches)} 个关键词")

        return matches
