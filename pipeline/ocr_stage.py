import cv2
import numpy as np
import time

from config.config import config
from utils.logger import logger

_ocr_instance = None
_ocr_init_config = None  # (lang, gpu_enabled) 初始化时的配置


def _get_ocr():
    global _ocr_instance, _ocr_init_config
    lang = config.get('ocr.language')
    use_gpu = config.get('gpu.enabled')
    current_config = (lang, use_gpu)

    if _ocr_instance is not None and _ocr_init_config == current_config:
        return _ocr_instance

    # 配置变更或首次初始化
    from paddleocr import PaddleOCR, __version__ as paddle_version
    major = int(paddle_version.split('.')[0])
    device = 'gpu' if use_gpu else 'cpu'

    logger.info(f"初始化 PaddleOCR: lang={lang}, device={device}")
    if major >= 3:
        # 屏幕截图始终正向，禁用文档方向/矫正模型以避免 PP-LCNet padding bug 并提速
        _ocr_instance = PaddleOCR(
            lang=lang, device=device, enable_mkldnn=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    else:
        _ocr_instance = PaddleOCR(
            lang=lang, use_gpu=use_gpu,
            use_angle_cls=True, enable_mkldnn=False
        )
    _ocr_init_config = current_config
    logger.info("PaddleOCR 初始化完成")
    return _ocr_instance


class OCRStage:
    def __init__(self):
        # 模型走模块级单例 _ocr_instance，不缓存实例字段，避免配置切换后引用不同步。
        pass

    def init(self):
        """预初始化 OCR 模型（让 5-15s 加载发生在 scan 循环之前）"""
        _get_ocr()

    def recognize(self, frame_bgr):
        """
        OCR 识别。每次取最新模型实例，配置变更自动生效。
        Args:
            frame_bgr: numpy BGR 数组
        Returns:
            list of dict: [{'text': str, 'confidence': float, 'bbox': list}, ...]
        """
        ocr = _get_ocr()

        # 可选图像反色
        if config.get('ocr.enable_image_invert'):
            frame_bgr = cv2.bitwise_not(frame_bgr)

        start = time.time()
        result = ocr.ocr(frame_bgr)
        duration = time.time() - start
        logger.debug(f"OCR 耗时: {duration:.3f}s")

        # 提取结果
        texts = []
        min_conf = config.get('ocr.min_confidence')

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
        global _ocr_instance, _ocr_init_config
        _ocr_instance = None
        _ocr_init_config = None
        import gc
        gc.collect()
