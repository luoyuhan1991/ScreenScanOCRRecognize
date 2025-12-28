"""
ScreenScanOCRRecognize - 屏幕扫描OCR识别
"""

__version__ = '1.0.0'

from .config import config
from .logger import logger, setup_logger

__all__ = ['config', 'logger', 'setup_logger', '__version__']

