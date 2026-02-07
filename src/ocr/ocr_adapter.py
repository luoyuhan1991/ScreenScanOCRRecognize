"""
OCR统一模块
提供统一的OCR配置类
封装不同OCR引擎的实现差异，统一参数管理
"""

from typing import Optional, List, Dict, Any, Union

from ..config.config import config
from ..utils.logger import logger


# ============================================================================
# OCR配置类
# ============================================================================

class OCRConfig:
    """
    统一的OCR配置类
    
    负责：
    1. 统一管理OCR参数（语言、GPU等）
    2. 提供转换为不同OCR引擎格式的方法
    3. 处理语言代码映射
    """
    
    # PaddleOCR语言代码映射
    PADDLE_LANG_MAP = {
        'ch': 'ch',
        'chinese': 'ch',
        'en': 'en',
        'english': 'en',
        'french': 'french',
        'german': 'german',
        'korean': 'korean',
        'japan': 'japan',
        'japanese': 'japan',
    }
    
    # EasyOCR语言代码映射
    EASYOCR_LANG_MAP = {
        'ch': 'ch_sim',
        'chinese': 'ch_sim',
        'ch_sim': 'ch_sim',
        'ch_tra': 'ch_tra',
        'en': 'en',
        'english': 'en',
        'french': 'fr',
        'german': 'de',
        'korean': 'ko',
        'japan': 'ja',
        'japanese': 'ja',
    }
    
    def __init__(
        self,
        languages: Optional[Union[str, List[str]]] = None,
        use_gpu: Optional[bool] = None,
        engine: str = 'paddle'
    ):
        """
        初始化OCR配置
        
        Args:
            languages: 语言列表或字符串，如 ['ch', 'en'] 或 'ch'
            use_gpu: 是否使用GPU（None表示从配置文件读取）
            engine: OCR引擎类型，'paddle' 或 'easy'
        """
        self.engine = engine
        
        # 处理语言参数（统一转换为列表格式）
        if languages is None:
            languages = config.get('ocr.languages', ['ch', 'en'])
        
        if isinstance(languages, str):
            self.languages = [languages]
        elif isinstance(languages, list):
            self.languages = languages
        else:
            self.languages = ['ch', 'en']  # 默认值
        
        # 处理GPU配置
        self.use_gpu = self._resolve_gpu_setting(use_gpu)
        
        logger.debug(f"OCRConfig初始化: engine={engine}, languages={self.languages}, use_gpu={self.use_gpu}")
    
    def _resolve_gpu_setting(self, use_gpu: Optional[bool]) -> bool:
        """
        解析GPU设置
        
        优先级：
        1. 传入的 use_gpu 参数
        2. 配置文件中的 force_cpu / force_gpu / auto_detect
        
        Args:
            use_gpu: 传入的GPU设置
            
        Returns:
            bool: 是否使用GPU
        """
        if use_gpu is not None:
            return bool(use_gpu)
        
        # 从配置读取GPU设置
        force_cpu = config.get('gpu.force_cpu', False)
        force_gpu = config.get('gpu.force_gpu', True)
        auto_detect = config.get('gpu.auto_detect', False)
        
        if force_cpu:
            return False
        elif force_gpu:
            return True
        elif auto_detect:
            # 自动检测GPU
            try:
                if self.engine == 'paddle':
                    import paddle
                    return paddle.is_compiled_with_cuda()
                else:  # easy
                    import torch
                    return torch.cuda.is_available()
            except ImportError:
                return False
        else:
            # 默认强制使用GPU
            return True
    
    def get_paddle_params(self) -> Dict[str, Any]:
        """
        转换为PaddleOCR参数格式
        
        PaddleOCR要求：
        - lang: 单个字符串（不支持多语言组合）
        - device: 'gpu' 或 'cpu'
        
        Returns:
            dict: PaddleOCR参数字典
        """
        # PaddleOCR只支持单个语言，优先选择中文，否则使用第一个
        if 'ch' in self.languages:
            lang_code = 'ch'
        else:
            lang_code = self.languages[0] if self.languages else 'ch'
        
        # 映射语言代码
        lang_code = self.PADDLE_LANG_MAP.get(lang_code, lang_code)
        
        if len(self.languages) > 1:
            logger.info(f"PaddleOCR只支持单个语言，已选择: {lang_code}（配置中的其他语言将被忽略）")
        
        return {
            'lang': lang_code,
            'device': 'gpu' if self.use_gpu else 'cpu'
        }
    
    def get_easy_params(self) -> Dict[str, Any]:
        """
        转换为EasyOCR参数格式
        
        EasyOCR要求：
        - languages: 语言列表
        - gpu: bool
        
        Returns:
            dict: EasyOCR参数字典
        """
        # 转换所有语言代码为EasyOCR格式
        easy_languages = []
        for lang in self.languages:
            easy_lang = self.EASYOCR_LANG_MAP.get(lang, lang)
            if easy_lang not in easy_languages:
                easy_languages.append(easy_lang)
        
        return {
            'languages': easy_languages,
            'gpu': self.use_gpu
        }
    
    def __repr__(self) -> str:
        """返回配置的字符串表示"""
        return f"OCRConfig(engine={self.engine}, languages={self.languages}, use_gpu={self.use_gpu})"

