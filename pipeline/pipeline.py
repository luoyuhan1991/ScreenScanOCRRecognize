import os
import time

from config.config import config, DEFAULT_BANLIST_FILE, PROJECT_ROOT
from utils.logger import logger, MATCH_LEVEL
from .capture import CaptureStage
from .diff_gate import DiffGate
from .matcher import SubstringMatcher
from .ocr_stage import OCRStage


class ScanResult:
    def __init__(self, ocr_results=None, matches=None, skipped=False, duration=0):
        self.ocr_results = ocr_results or []
        self.matches = matches or []
        self.skipped = skipped
        self.duration = duration


class ScanPipeline:
    def __init__(self):
        self.capture = CaptureStage()
        self.diff_gate = DiffGate()
        self.ocr = OCRStage()
        self.matcher = SubstringMatcher(logger=logger)
        self._last_result = ScanResult()
        self._roi = None

    def init(self):
        """初始化 OCR 模型和关键词"""
        self.ocr.init()
        banlist_file = config.get('files.banlist_file', DEFAULT_BANLIST_FILE)
        if not os.path.isabs(banlist_file):
            banlist_file = os.path.join(PROJECT_ROOT, banlist_file)
        self.matcher.load(banlist_file)

    def set_roi(self, roi):
        self._roi = roi
        self.diff_gate.reset()

    def scan_once(self):
        """执行一次扫描"""
        start = time.time()

        frame = self.capture.grab(roi=self._roi)

        if self.diff_gate.should_skip(frame):
            # 复用上次结果，仅更新 skipped 和 duration
            result = ScanResult(
                ocr_results=self._last_result.ocr_results,
                matches=self._last_result.matches,
                skipped=True,
                duration=time.time() - start
            )
        else:
            ocr_results = self.ocr.recognize(frame)
            matches = self.matcher.match(ocr_results)
            self._last_result = ScanResult(
                ocr_results=ocr_results,
                matches=matches,
                skipped=False,
                duration=time.time() - start
            )
            result = self._last_result

        # 每轮都打印本次 OCR 文本：命中行 MATCH 级别（红），其余 INFO（绿）。
        # 帧差跳过时打印的是上次缓存的内容，保证用户每个 interval 都能在日志看到 OCR 结果。
        self._log_ocr_lines(result.ocr_results, result.matches, result.skipped)
        return result

    @staticmethod
    def _log_ocr_lines(ocr_results, matches, skipped):
        if not ocr_results:
            return
        matched_texts = {m.get('ocr_text', '') for m in matches}
        tags_by_text = {}
        for m in matches:
            t = m.get('ocr_text', '')
            kw = m.get('keyword', '')
            hint = m.get('hint', '')
            tags_by_text.setdefault(t, []).append(f"{kw}({hint})" if hint else kw)
        prefix = "OCR(缓存)" if skipped else "OCR"
        for r in ocr_results:
            text = r.get('text', '') if isinstance(r, dict) else ''
            if not text:
                continue
            if text in matched_texts:
                tags = ' '.join(tags_by_text.get(text, []))
                logger.log(MATCH_LEVEL, f"{prefix} | {text}  ← {tags}")
            else:
                logger.info(f"{prefix} | {text}")

    def release(self):
        self.capture.close()
        self.ocr.release()
