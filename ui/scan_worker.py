"""扫描后台线程：QThread 子类，跑 ScanPipeline。

线程内：先 pipeline.init()（OCR 加载几秒~十几秒）→ 进入循环
    while not stop:
        result = pipeline.scan_once()
        emit result_ready(ocr_results, matches)  # → Overlay
        write logging.info / warning              # → LogBridge → LogPanel
        wait interval

UI 接：
    worker.status_changed → StatusBar.set_status
    worker.result_ready   → Overlay.update
    worker.start_scan(roi=...)
    worker.stop_scan()
"""
import logging
import time
from PySide6.QtCore import QThread, Signal

from config.config import config
from pipeline.pipeline import ScanPipeline


class ScanWorker(QThread):
    """后台扫描线程。Signal：status_changed(text) / result_ready(ocr_results, matches)"""

    status_changed = Signal(str)
    # ocr_results / matches 都是 list[dict]，用 object 类型让 QObject 跨线程传递更宽松
    result_ready = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pipeline = ScanPipeline()
        self._stop = False
        self._roi = None
        self._initialized = False

    # ---------- 公开 API ----------

    def set_roi(self, roi):
        """run 之前或运行中都可以调；运行中改 ROI 立即生效。"""
        self._roi = roi
        if self._initialized:
            self.pipeline.set_roi(roi)

    def start_scan(self, roi=None):
        """启动扫描线程。若已在跑则忽略（防重复 start 抛 RuntimeError）。"""
        if self.isRunning():
            return
        if roi is not None:
            self._roi = roi
        self._stop = False
        self.start()  # → run()

    def stop_scan(self):
        """请求停止。线程在下一次循环边界退出，不打断当前 OCR。"""
        self._stop = True

    # ---------- QThread.run ----------

    def run(self):
        try:
            self._do_init()
            self._do_loop()
        except Exception as e:
            logging.error(f'扫描线程异常: {e}')
            self.status_changed.emit('已停止')
        # 注意：worker 退出不释放 pipeline。OCRStage 走模块级 (lang, gpu) 单例，
        # 释放后下次启动会重新加载模型（5–15s + 打印 "初始化 PaddleOCR"），且
        # release 调用本身有 gc 耗时。让模型驻留到进程退出，OS 收回内存。
        # 配置变更（语言 / GPU 开关）由 _get_ocr 内部的元组比对触发重建，安全。

    def _do_init(self):
        self.status_changed.emit('初始化中')
        logging.info('正在初始化 OCR 模型与关键词…')
        t0 = time.time()
        self.pipeline.init()
        self._initialized = True
        if self._roi is not None:
            self.pipeline.set_roi(self._roi)
        logging.info(f'OCR 初始化完成（{time.time()-t0:.1f}s）')

    def _do_loop(self):
        self.status_changed.emit('运行中')
        while not self._stop:
            interval = float(config.get('scan.interval_seconds') or 5.0)
            t0 = time.time()
            try:
                result = self.pipeline.scan_once()
            except Exception as e:
                logging.error(f'scan_once 失败: {e}')
                self._sleep_with_check(interval)
                continue

            # 日志：跳过 / 识别行数 / 匹配数 / 耗时
            if result.skipped:
                logging.info(f'帧差跳过（OCR 复用上次结果），耗时 {result.duration*1000:.0f} ms')
            else:
                logging.info(
                    f'OCR {len(result.ocr_results)} 行，'
                    f'命中 {len(result.matches)} 条，'
                    f'耗时 {result.duration*1000:.0f} ms'
                )
            for m in result.matches:
                logging.warning(f'>>> {m.get("keyword","")} → {m.get("hint","")}')

            # Overlay 数据：跳过帧也复用 last result（pipeline 内部已处理）
            self.result_ready.emit(result.ocr_results, result.matches)

            elapsed = time.time() - t0
            self._sleep_with_check(max(0.0, interval - elapsed))

        self.status_changed.emit('已停止')
        logging.info('扫描已停止')

    def _sleep_with_check(self, seconds):
        """分段 sleep，让 stop 信号能在 ≤300ms 内响应。"""
        slept = 0.0
        step = 0.3
        while slept < seconds and not self._stop:
            time.sleep(min(step, seconds - slept))
            slept += step
