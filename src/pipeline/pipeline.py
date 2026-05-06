import os
import time
from ..config.config import config, DEFAULT_BANLIST_FILE, PROJECT_ROOT
from ..utils.logger import logger
from .capture import CaptureStage
from .diff_gate import DiffGate
from .ocr_stage import OCRStage
from shared.matcher import SubstringMatcher


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
