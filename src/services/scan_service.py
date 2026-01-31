"""
扫描服务模块
封装扫描、OCR识别、匹配和结果保存的核心逻辑
"""

import glob
import os
import threading
import time
from datetime import datetime
from typing import Optional, Dict, List, Any

from ..config.config import config
from ..ocr.ocr_adapter import OCRConfig, OCRFactory, OCRAdapter
from ..utils.cleanup_old_files import cleanup_old_folders_by_count
from ..utils.logger import logger
from ..utils.scan_screen import scan_screen
from ..utils.text_matcher import _get_cached_matcher


class ScanService:
    """
    扫描服务类
    负责协调截图、OCR识别、结果匹配和文件保存
    """
    
    def __init__(self):
        self.ocr_adapter: Optional[OCRAdapter] = None
        self.ocr_config: Optional[OCRConfig] = None
        self.roi = None
        self.is_running = False
        self._stop_event = threading.Event()
        
        # 运行时状态
        self.scan_count = 0
        self.last_scan_time = None
        self.current_minute_folder = None
        self.current_minute = None
        
        # 配置缓存（避免频繁读取）
        self._cache_config()
    
    def _cache_config(self):
        """缓存常用配置"""
        self.output_dir = config.get('files.output_dir', 'output')
        self.scan_interval = config.get('scan.interval_seconds', 5)
        self.roi_padding = config.get('scan.roi_padding', 10)
        self.folder_mode = config.get('files.folder_mode', 'minute')
        self.max_folders = config.get('files.max_folders', 10)
        self.enable_matching = config.get('matching.enabled', True)
        self.banlist_file = config.get('files.banlist_file', 'docs/banlist.txt')
        self.display_duration = config.get('matching.display_duration', 3)
        self.display_position = config.get('matching.position', 'center')
        self.display_font_size = config.get('matching.font_size', 30)
        
        # 新增配置：是否保存文件（默认开启以保持兼容性）
        self.save_screenshot = config.get('files.save_screenshot', True)
        self.save_ocr_result = config.get('files.save_ocr_result', True)
    
    def init_ocr(self, engine_choice: str = 'paddle', languages: List[str] = None, use_gpu: bool = None):
        """
        初始化OCR引擎
        
        Args:
            engine_choice: 'paddle' 或 'easy'
            languages: 语言列表
            use_gpu: 是否使用GPU
        """
        if languages is None:
            languages = config.get('ocr.languages', ['ch', 'en'])
            
        # 创建OCR配置
        self.ocr_config = OCRConfig(
            languages=languages,
            use_gpu=use_gpu,
            engine=engine_choice
        )
        
        # 创建适配器
        ocr_type = '1' if engine_choice == 'paddle' else '2'
        self.ocr_adapter = OCRFactory.create(ocr_type)
        
        # 初始化模型
        logger.info(f"正在初始化 {self.ocr_adapter.engine_name} 模型...")
        self.ocr_adapter.init_reader(self.ocr_config)
        logger.info(f"{self.ocr_adapter.engine_name} 模型初始化完成")
    
    def release_resources(self):
        """释放资源（OCR模型等）"""
        if self.ocr_adapter:
            try:
                self.ocr_adapter.release()
                self.ocr_adapter = None
                import gc
                gc.collect()
                logger.info("OCR资源已释放")
            except Exception as e:
                logger.warning(f"释放OCR资源失败: {e}")

    def set_roi(self, roi):
        """设置ROI区域"""
        self.roi = roi
        
    def scan_once(self) -> Dict[str, Any]:
        """
        执行一次完整的扫描流程
        
        Returns:
            dict: 包含扫描结果的字典
        """
        result = {
            'success': False,
            'timestamp': None,
            'ocr_text': [],
            'matches': [],
            'duration': 0,
            'screenshot_path': None
        }
        
        start_time = time.time()
        
        try:
            # 1. 准备保存目录
            now = datetime.now()
            save_dir = self._prepare_save_dir(now)
            second_timestamp = now.strftime("%Y%m%d_%H%M%S")
            result['timestamp'] = second_timestamp
            
            # 2. 截图
            # 如果不保存截图文件，scan_screen 仍然会返回 PIL Image 对象
            screenshot, _ = scan_screen(
                save_dir=save_dir,
                save_file=self.save_screenshot,
                timestamp=second_timestamp,
                roi=self.roi,
                padding=self.roi_padding
            )
            
            if screenshot:
                # 清理旧截图（仅在按分钟模式且保存文件时）
                if self.folder_mode == 'minute' and self.save_screenshot:
                    self._cleanup_old_screenshots(save_dir, second_timestamp)
                
                if self.save_screenshot:
                    result['screenshot_path'] = os.path.join(save_dir, f"screenshot_{second_timestamp}.png")
                
                # 3. OCR识别
                if self.ocr_adapter:
                    # 注意：recognize_and_print 内部目前包含了保存文件的逻辑
                    # 这是一个设计上的耦合，暂时保留，后续可以重构 ocr_adapter 拆分识别和保存
                    ocr_results = self.ocr_adapter.recognize_and_print(
                        screenshot,
                        config=self.ocr_config,
                        save_dir=save_dir,
                        timestamp=second_timestamp,
                        roi=None, # 截图已裁剪
                        save_result=self.save_ocr_result
                    )
                    
                    # 统一结果格式
                    ocr_list = self._normalize_ocr_results(ocr_results)
                    result['ocr_text'] = ocr_list
                    
                    # 4. 关键词匹配
                    if self.enable_matching and ocr_list:
                        # 使用缓存的匹配器进行匹配
                        matcher = _get_cached_matcher(self.banlist_file)
                        matches = matcher.match(ocr_list)
                        result['matches'] = matches
                        
                result['success'] = True
                
        except Exception as e:
            logger.error(f"扫描流程出错: {e}", exc_info=True)
            result['error'] = str(e)
            
        result['duration'] = time.time() - start_time
        return result

    def _prepare_save_dir(self, now: datetime) -> str:
        """准备保存目录"""
        if self.folder_mode == 'minute':
            minute_timestamp = now.strftime("%Y%m%d_%H%M")
            
            if self.current_minute != minute_timestamp:
                self.current_minute = minute_timestamp
                self.current_minute_folder = os.path.join(self.output_dir, self.current_minute)
                
                if not os.path.exists(self.current_minute_folder):
                    os.makedirs(self.current_minute_folder, exist_ok=True)
                    # 清理旧文件夹
                    cleanup_old_folders_by_count(self.output_dir, max_folders=self.max_folders)
            
            return self.current_minute_folder
        else:
            second_timestamp = now.strftime("%Y%m%d_%H%M%S")
            save_dir = os.path.join(self.output_dir, second_timestamp)
            os.makedirs(save_dir, exist_ok=True)
            return save_dir

    def _cleanup_old_screenshots(self, save_dir, current_timestamp):
        """清理当前文件夹中的旧截图"""
        try:
            pattern = os.path.join(save_dir, "screenshot_*.png")
            current_file = os.path.join(save_dir, f"screenshot_{current_timestamp}.png")
            for f in glob.glob(pattern):
                if f != current_file:
                    try:
                        os.remove(f)
                    except OSError:
                        pass
        except Exception:
            pass

    def _normalize_ocr_results(self, results) -> List[Dict[str, Any]]:
        """统一OCR结果格式为列表"""
        if isinstance(results, str):
            return [{'text': line.strip()} for line in results.split('\n') if line.strip()]
        elif isinstance(results, list):
            return results
        return [{'text': str(results)}] if results else []
