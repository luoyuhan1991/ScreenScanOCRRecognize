"""
OCR统一模块
提供统一的OCR配置、适配器和工厂
封装不同OCR引擎的实现差异，统一参数管理
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from PIL import Image

from .config import config
from .logger import logger


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


# ============================================================================
# OCR适配器基类和实现
# ============================================================================


class OCRAdapter(ABC):
    """
    OCR适配器基类
    
    定义统一的OCR接口，子类实现具体引擎的适配逻辑
    """
    
    @abstractmethod
    def init_reader(self, config: OCRConfig, force_reinit: bool = False):
        """
        初始化OCR阅读器
        
        Args:
            config: OCR配置对象
            force_reinit: 是否强制重新初始化
        """
        pass
    
    @abstractmethod
    def recognize_and_print(
        self,
        image: Union[Image.Image, str],
        config: OCRConfig,
        save_dir: str = "output",
        timestamp: Optional[str] = None,
        roi: Optional[tuple] = None
    ) -> Any:
        """
        对图片进行OCR识别并保存结果
        
        Args:
            image: PIL图像对象或图片文件路径
            config: OCR配置对象
            save_dir: 保存目录
            timestamp: 时间戳，用于生成文件名
            roi: 感兴趣区域 (x1, y1, x2, y2)
            
        Returns:
            识别结果（格式可能因引擎而异）
        """
        pass
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """返回OCR引擎名称"""
        pass


class PaddleOCRAdapter(OCRAdapter):
    """PaddleOCR适配器"""
    
    def __init__(self):
        self._reader = None
        self._current_config_key = None
    
    @property
    def engine_name(self) -> str:
        return "PaddleOCR"
    
    def _get_config_key(self, config: OCRConfig) -> tuple:
        """生成配置键用于比较"""
        params = config.get_paddle_params()
        return (params['lang'], config.use_gpu)
    
    def init_reader(self, config: OCRConfig, force_reinit: bool = False):
        """初始化PaddleOCR阅读器"""
        from . import paddle_ocr
        
        config_key = self._get_config_key(config)
        
        # 检查是否需要重新初始化
        if not force_reinit and self._reader is not None and self._current_config_key == config_key:
            return self._reader
        
        # 获取PaddleOCR参数
        params = config.get_paddle_params()
        
        # 调用paddle_ocr模块的init_reader
        self._reader = paddle_ocr.init_reader(
            languages=params['lang'],
            use_gpu=config.use_gpu,
            force_reinit=force_reinit
        )
        
        self._current_config_key = config_key
        logger.debug(f"PaddleOCRAdapter初始化完成: {params}")
    
    def recognize_and_print(
        self,
        image: Union[Image.Image, str],
        config: OCRConfig,
        save_dir: str = "output",
        timestamp: Optional[str] = None,
        roi: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """使用PaddleOCR进行识别"""
        from . import paddle_ocr
        
        # 确保已初始化
        config_key = self._get_config_key(config)
        if self._reader is None or self._current_config_key != config_key:
            self.init_reader(config)
        
        # 获取PaddleOCR参数
        params = config.get_paddle_params()
        
        # 调用paddle_ocr模块的recognize_and_print
        return paddle_ocr.recognize_and_print(
            image=image,
            languages=params['lang'],
            save_dir=save_dir,
            timestamp=timestamp,
            use_gpu=config.use_gpu,
            roi=roi
        )


class EasyOCRAdapter(OCRAdapter):
    """EasyOCR适配器"""
    
    def __init__(self):
        self._reader = None
        self._current_config_key = None
    
    @property
    def engine_name(self) -> str:
        return "EasyOCR"
    
    def _get_config_key(self, config: OCRConfig) -> tuple:
        """生成配置键用于比较"""
        params = config.get_easy_params()
        # 将列表转换为元组以便比较
        return (tuple(params['languages']), params['gpu'])
    
    def init_reader(self, config: OCRConfig, force_reinit: bool = False):
        """初始化EasyOCR阅读器"""
        from . import easy_ocr
        
        config_key = self._get_config_key(config)
        
        # 检查是否需要重新初始化
        if not force_reinit and self._reader is not None and self._current_config_key == config_key:
            return self._reader
        
        # 获取EasyOCR参数
        params = config.get_easy_params()
        
        # 调用easy_ocr模块的init_reader
        self._reader = easy_ocr.init_reader(
            languages=params['languages'],
            use_gpu=params['gpu'],
            force_reinit=force_reinit
        )
        
        self._current_config_key = config_key
        logger.debug(f"EasyOCRAdapter初始化完成: {params}")
    
    def recognize_and_print(
        self,
        image: Union[Image.Image, str],
        config: OCRConfig,
        save_dir: str = "output",
        timestamp: Optional[str] = None,
        roi: Optional[tuple] = None
    ) -> str:
        """使用EasyOCR进行识别"""
        from . import easy_ocr
        
        # 确保已初始化
        config_key = self._get_config_key(config)
        if self._reader is None or self._current_config_key != config_key:
            self.init_reader(config)
        
        # 获取EasyOCR参数
        params = config.get_easy_params()
        
        # 调用easy_ocr模块的recognize_and_print
        return easy_ocr.recognize_and_print(
            image=image,
            languages=params['languages'],
            save_dir=save_dir,
            timestamp=timestamp,
            use_gpu=params['gpu'],
            roi=roi
        )


# ============================================================================
# OCR工厂类
# ============================================================================

class OCRFactory:
    """OCR适配器工厂类"""
    
    @staticmethod
    def create(ocr_choice: Optional[str] = None) -> 'OCRAdapter':
        """
        创建OCR适配器
        
        Args:
            ocr_choice: OCR引擎选择
                - '1' 或 'paddle': PaddleOCR
                - '2' 或 'easy': EasyOCR
                - None: 从配置文件读取默认引擎
        
        Returns:
            OCRAdapter: OCR适配器实例
        
        Raises:
            ValueError: 如果ocr_choice无效
        """
        # 如果没有指定，从配置文件读取
        if ocr_choice is None:
            default_engine = config.get('ocr.default_engine', 'paddle')
            ocr_choice = '1' if default_engine == 'paddle' else '2'
        
        # 标准化选择值
        ocr_choice = str(ocr_choice).lower().strip()
        
        if ocr_choice in ('1', 'paddle', 'paddleocr'):
            logger.info("创建 PaddleOCR 适配器")
            return PaddleOCRAdapter()
        elif ocr_choice in ('2', 'easy', 'easyocr'):
            logger.info("创建 EasyOCR 适配器")
            return EasyOCRAdapter()
        else:
            raise ValueError(f"无效的OCR引擎选择: {ocr_choice}。支持: '1'/'paddle' 或 '2'/'easy'")
    
    @staticmethod
    def get_engine_name(ocr_choice: Optional[str] = None) -> str:
        """
        获取OCR引擎名称（无需创建实例）
        
        Args:
            ocr_choice: OCR引擎选择
        
        Returns:
            str: OCR引擎名称
        """
        if ocr_choice is None:
            default_engine = config.get('ocr.default_engine', 'paddle')
            ocr_choice = '1' if default_engine == 'paddle' else '2'
        
        ocr_choice = str(ocr_choice).lower().strip()
        
        if ocr_choice in ('1', 'paddle', 'paddleocr'):
            return "PaddleOCR"
        elif ocr_choice in ('2', 'easy', 'easyocr'):
            return "EasyOCR"
        else:
            return "Unknown"

