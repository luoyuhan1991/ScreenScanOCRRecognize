"""
关键词子串匹配（基于 Aho-Corasick 自动机）。
两个版本共享：根目录主版本与 new_version 都从这里 import。
"""

import ahocorasick
import os
import threading


def _is_kept(cp: int) -> bool:
    """匹配时只保留：英文字母、阿拉伯数字、中文（CJK 基本区 + 扩展 A）。"""
    return (
        (0x30 <= cp <= 0x39)         # 0-9
        or (0x61 <= cp <= 0x7A)      # a-z（casefold 后大写已转小写）
        or (0x4E00 <= cp <= 0x9FFF)  # CJK Unified Ideographs
        or (0x3400 <= cp <= 0x4DBF)  # CJK Extension A
    )


def _normalize(s: str) -> str:
    """匹配用归一化：casefold + 只保留中文/英文字母/数字，其余字符全部忽略。"""
    if not s:
        return ""
    folded = s.casefold()
    return ''.join(c for c in folded if _is_kept(ord(c)))


def parse_keyword_line(line: str):
    """
    解析关键词行（优先空白分隔）：
    - 第一段为关键词，其后整段为提示词；中间用任意空白分隔。
    - 若整行无第二段但含英文冒号「:」，按「关键词:提示词」兼容旧格式（仅切第一个冒号）。
    返回: (keyword, hint)
    """
    raw = (line or "").strip()
    if not raw:
        return "", ""

    parts = raw.split(None, 1)
    keyword = parts[0]
    if len(parts) > 1:
        hint = parts[1].strip().lstrip(":").strip()
        return keyword, hint

    if ":" in keyword:
        k, h = keyword.split(":", 1)
        return k.strip(), h.strip()
    return keyword, ""


def keyword_in_text(text: str, keyword: str) -> bool:
    """子串匹配，casefold 不区分大小写，并忽略标点/空白。空字符串视为不匹配。"""
    if not keyword or not text:
        return False
    nk = _normalize(keyword)
    if not nk:
        return False
    return nk in _normalize(text)


class SubstringMatcher:
    """
    Aho-Corasick 多模式子串匹配器。

    用法:
        m = SubstringMatcher(banlist_file="config/banlist.txt", logger=logger)
        m.load()
        matches = m.match(ocr_results)  # [{'keyword','hint','ocr_text'}, ...]
    """

    def __init__(self, banlist_file=None, logger=None):
        self._banlist_file = banlist_file
        self._logger = logger
        self._automaton = None
        self._keywords = {}  # {normalized_keyword: {'original': str, 'hint': str}}
        self._file_mtime = None

    @property
    def banlist_file(self):
        return self._banlist_file

    @property
    def keywords(self):
        return [info['original'] for info in self._keywords.values()]

    def get_hint(self, keyword: str) -> str:
        info = self._keywords.get(_normalize(keyword))
        return info['hint'] if info else ""

    def load(self, banlist_file=None):
        """加载关键词文件并构建自动机。banlist_file 不传则使用构造时路径。"""
        if banlist_file is not None:
            self._banlist_file = banlist_file
        path = self._banlist_file
        self._keywords = {}
        self._automaton = None
        self._file_mtime = None

        if not path:
            self._log('warning', "未提供关键词文件路径")
            return

        path = os.path.abspath(path)
        self._banlist_file = path

        if not os.path.exists(path):
            self._log('warning', f"关键词文件不存在: {path}")
            return

        try:
            self._file_mtime = os.path.getmtime(path)
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    keyword, hint = parse_keyword_line(line)
                    if not keyword:
                        continue
                    norm = _normalize(keyword)
                    if not norm:
                        continue
                    self._keywords[norm] = {
                        'original': keyword,
                        'hint': hint,
                    }
        except Exception as e:
            self._log('error', f"加载关键词文件失败: {e}")
            return

        if self._keywords:
            automaton = ahocorasick.Automaton()
            for kw_norm, info in self._keywords.items():
                automaton.add_word(kw_norm, info)
            automaton.make_automaton()
            self._automaton = automaton

        self._log('info', f"已加载 {len(self._keywords)} 个关键词")

    def reload_if_changed(self):
        """文件 mtime 变更时重新加载（不存在时保留旧关键词，避免误清空）。"""
        if not self._banlist_file:
            return
        if not os.path.exists(self._banlist_file):
            return
        try:
            mtime = os.path.getmtime(self._banlist_file)
        except Exception:
            return
        if self._file_mtime is None or mtime != self._file_mtime:
            self._log('info', "关键词文件已变更，重新加载")
            self.load()

    def match(self, ocr_results):
        """
        对 OCR 结果执行子串匹配。

        Args:
            ocr_results: list of dict，每个含 'text' 字段。
        Returns:
            list of dict: [{'keyword','hint','ocr_text'}, ...]，每个关键词最多出现一次。
        """
        self.reload_if_changed()

        if not self._automaton or not ocr_results:
            return []

        matches = []
        seen = set()

        for result in ocr_results:
            text = result.get('text', '') if isinstance(result, dict) else ''
            if not text:
                continue
            text_norm = _normalize(text)
            if not text_norm:
                continue
            for _, info in self._automaton.iter(text_norm):
                kw = info['original']
                if kw in seen:
                    continue
                seen.add(kw)
                matches.append({
                    'keyword': kw,
                    'hint': info['hint'],
                    'ocr_text': text,
                })

        if matches:
            self._log('info', f"匹配到 {len(matches)} 个关键词")
        return matches

    def _log(self, level, msg):
        if self._logger is None:
            return
        getattr(self._logger, level, lambda *_: None)(msg)


_cache = {}
_cache_lock = threading.Lock()


def get_cached_matcher(banlist_file: str, logger=None) -> SubstringMatcher:
    """按文件绝对路径缓存 SubstringMatcher 单例；返回前会触发 reload_if_changed。"""
    path = os.path.abspath(banlist_file)
    with _cache_lock:
        m = _cache.get(path)
        if m is None:
            m = SubstringMatcher(banlist_file=path, logger=logger)
            m.load()
            _cache[path] = m
    m.reload_if_changed()
    return m
