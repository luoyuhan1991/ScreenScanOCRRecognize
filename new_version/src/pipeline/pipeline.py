import time
from ..config.config import config
from ..utils.logger import logger
from .capture import CaptureStage
from .diff_gate import DiffGate
from .ocr_stage import OCRStage
from .match_stage import MatchStage


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
        self.matcher = MatchStage()
        self._last_result = ScanResult()
        self._roi = None

    def init(self):
        """初始化 OCR 模型和关键词"""
        self.ocr.init()
        self.matcher.load()

    def set_roi(self, roi):
        self._roi = roi

    def scan_once(self):
        """执行一次扫描"""
        start = time.time()

        frame = self.capture.grab(roi=self._roi)

        if self.diff_gate.should_skip(frame):
            self._last_result = ScanResult(
                skipped=True, duration=time.time() - start
            )
            return self._last_result

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
