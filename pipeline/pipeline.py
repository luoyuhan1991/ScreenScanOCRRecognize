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
            return result

        ocr_results = self.ocr.recognize(frame)
        matches = self.matcher.match(ocr_results)

        # 把本轮每一行 OCR 文本写入日志：命中行用 MATCH 级别（红），其余 INFO（绿）。
        matched_texts = {m.get('ocr_text', '') for m in matches}
        hints_by_text = {}
        for m in matches:
            hints_by_text.setdefault(m.get('ocr_text', ''), []).append(
                f"{m.get('keyword', '')}({m.get('hint', '')})"
                if m.get('hint') else m.get('keyword', '')
            )
        for r in ocr_results:
            text = r.get('text', '') if isinstance(r, dict) else ''
            if not text:
                continue
            if text in matched_texts:
                tags = ' '.join(hints_by_text.get(text, []))
                logger.log(MATCH_LEVEL, f"OCR | {text}  ← {tags}")
            else:
                logger.info(f"OCR | {text}")

        self._last_result = ScanResult(
            ocr_results=ocr_results,
            matches=matches,
            skipped=False,
            duration=time.time() - start
        )
        return self._last_result

    def release(self):
        self.capture.close()
        self.ocr.release()
