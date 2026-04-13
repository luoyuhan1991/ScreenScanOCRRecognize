import time
import cv2
import numpy as np
from ..config.config import config
from ..utils.logger import logger

_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR, __version__ as paddle_version
        major = int(paddle_version.split('.')[0])
        lang = config.get('ocr.language', 'ch')
        use_gpu = config.get('gpu.enabled', True)
        device = 'gpu' if use_gpu else 'cpu'

        logger.info(f"初始化 PaddleOCR: lang={lang}, device={device}")
        if major >= 3:
            _ocr_instance = PaddleOCR(
                lang=lang, device=device, enable_mkldnn=False
            )
        else:
            _ocr_instance = PaddleOCR(
                lang=lang, use_gpu=use_gpu,
                use_angle_cls=True, enable_mkldnn=False
            )
        logger.info("PaddleOCR 初始化完成")
    return _ocr_instance


class OCRStage:
    def __init__(self):
        self._ocr = None

    def init(self):
        """预初始化 OCR 模型"""
        self._ocr = _get_ocr()

    def recognize(self, frame_bgr):
        """
        OCR 识别
        Args:
            frame_bgr: numpy BGR 数组
        Returns:
            list of dict: [{'text': str, 'confidence': float, 'bbox': list}, ...]
        """
        if self._ocr is None:
            self._ocr = _get_ocr()

        # 可选图像反色
        if config.get('ocr.enable_image_invert', False):
            frame_bgr = cv2.bitwise_not(frame_bgr)

        start = time.time()
        result = self._ocr.ocr(frame_bgr)
        duration = time.time() - start
        logger.debug(f"OCR 耗时: {duration:.3f}s")

        # 提取结果
        texts = []
        min_conf = config.get('ocr.min_confidence', 0.3)

        if result and len(result) > 0:
            ocr_result = result[0]
            if isinstance(ocr_result, dict):
                # PaddleOCR 3.x 格式
                rec_texts = ocr_result.get('rec_texts', [])
                rec_scores = ocr_result.get('rec_scores', [])
                rec_polys = ocr_result.get('rec_polys', [])
                for i, text in enumerate(rec_texts):
                    conf = float(rec_scores[i]) if i < len(rec_scores) else 1.0
                    if conf >= min_conf:
                        texts.append({
                            'text': text,
                            'confidence': conf,
                            'bbox': (
                                rec_polys[i].tolist()
                                if i < len(rec_polys) else None
                            )
                        })
            elif isinstance(ocr_result, list):
                # PaddleOCR 2.x 格式
                for line in ocr_result:
                    if line and len(line) >= 2:
                        text = line[1][0]
                        conf = float(line[1][1])
                        if conf >= min_conf:
                            texts.append({
                                'text': text,
                                'confidence': conf,
                                'bbox': line[0]
                            })

        logger.info(f"OCR 识别 {len(texts)} 行, 耗时 {duration:.3f}s")
        return texts

    def release(self):
        global _ocr_instance
        _ocr_instance = None
        self._ocr = None
        import gc
        gc.collect()
