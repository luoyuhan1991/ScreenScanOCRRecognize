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
        self.output_count = 0
        
        # 配置缓存（避免频繁读取）
        self._cache_config()
    
    def _cache_config(self):
        """缓存常用配置"""
        self.output_dir = config.get('files.output_dir', 'output')
        self.scan_interval = config.get('scan.interval_seconds', 5)
        self.roi_padding = config.get('scan.roi_padding', 10)
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
        # 重新读取配置，确保使用最新的配置值
        # 解决GUI勾选框设置后配置不生效的问题
        self._cache_config()
        
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
            self._prepare_save_dir(now)
            second_timestamp = now.strftime("%Y%m%d_%H%M%S")
            result['timestamp'] = second_timestamp
            
            # 2. 截图
            screenshot, _ = scan_screen(
                save_dir=self.output_dir,
                save_file=self.save_screenshot,
                timestamp=second_timestamp,
                roi=self.roi,
                padding=self.roi_padding
            )
            
            if screenshot:
                if self.save_screenshot:
                    result['screenshot_path'] = os.path.join(self.output_dir, f"screenshot_{second_timestamp}.png")
                
                # 3. OCR识别
                if self.ocr_adapter:
                    # 注意：recognize_and_print 内部目前包含了保存文件的逻辑
                    ocr_results = self.ocr_adapter.recognize_and_print(
                        screenshot,
                        config=self.ocr_config,
                        save_dir=self.output_dir,
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
                
                # 每10次扫描清空一次
                self.output_count += 1
                if self.output_count >= 10:
                    self.output_count = 0
                    self._cleanup_old_outputs()
                    
        except Exception as e:
            logger.error(f"扫描流程出错: {e}", exc_info=True)
            result['error'] = str(e)
            
        result['duration'] = time.time() - start_time
        return result

    def _prepare_save_dir(self, now: datetime) -> str:
        """准备保存目录"""
        os.makedirs(self.output_dir, exist_ok=True)
        return self.output_dir

    def _cleanup_old_outputs(self):
        """清理旧输出文件，只保留最新的10组"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            files_to_delete = []
            for f in glob.glob(os.path.join(self.output_dir, "*")):
                if os.path.isfile(f):
                    filename = os.path.basename(f)
                    if filename.startswith("screenshot_") or filename.startswith("ocr_result_"):
                        files_to_delete.append(f)
            
            files_to_delete.sort(key=os.path.getmtime)
            
            if len(files_to_delete) > 10:
                for f in files_to_delete[:-10]:
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
