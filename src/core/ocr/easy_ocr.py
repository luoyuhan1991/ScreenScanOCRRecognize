"""
OCR识别模块
对图片进行OCR文字识别
使用 EasyOCR 库（纯Python实现，无需安装Tesseract）
包含图像预处理优化以提高识别准确率
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple

import easyocr
import numpy as np
from PIL import Image

from ...config.config import config
from ...utils.logger import logger

_reader = None
_languages = ['ch_sim', 'en']
_use_gpu = False

# EasyOCR语言代码映射（将通用代码转换为EasyOCR支持的代码）
EASYOCR_LANG_MAP = {
    'ch': 'ch_sim',        # 中文 -> 简体中文
    'chinese': 'ch_sim',   # 中文 -> 简体中文
    'ch_sim': 'ch_sim',    # 简体中文
    'ch_tra': 'ch_tra',    # 繁体中文
    'en': 'en',            # 英文
    'english': 'en',       # 英文
    'french': 'fr',        # 法语
    'german': 'de',        # 德语
    'korean': 'ko',        # 韩语
    'japan': 'ja',         # 日语
    'japanese': 'ja',      # 日语
}


def init_reader(languages=None, use_gpu=None, force_reinit=False):
    """
    初始化 EasyOCR 阅读器
    
    Args:
        languages (list): 语言列表，默认为 ['ch_sim', 'en']
        use_gpu (bool): 是否使用GPU，默认为None（自动检测）
        force_reinit (bool): 是否强制重新初始化，默认为False
    
    Returns:
        easyocr.Reader: OCR阅读器对象
    """
    global _reader, _languages, _use_gpu
    
    if languages is None:
        languages = _languages
    else:
        if isinstance(languages, list):
            languages = [EASYOCR_LANG_MAP.get(lang, lang) for lang in languages]
        elif isinstance(languages, str):
            languages = [EASYOCR_LANG_MAP.get(languages, languages)]
        else:
            languages = _languages
    
    # 处理GPU设置
    new_use_gpu = bool(use_gpu) if use_gpu is not None else _use_gpu
    
    # 检查是否需要重新初始化
    need_reinit = (_reader is None or 
                   force_reinit or 
                   (new_use_gpu != _use_gpu) or
                   (languages != _languages))
    
    _use_gpu = new_use_gpu
    _languages = languages
    
    if need_reinit:
        logger.info("正在初始化 EasyOCR（首次运行会下载模型，请稍候）...")
        logger.info(f"GPU加速: {'启用' if _use_gpu else '未启用（使用CPU）'}")
        try:
            _reader = easyocr.Reader(languages, gpu=_use_gpu)
            logger.info("EasyOCR 初始化完成")
            if _use_gpu:
                import torch
                logger.info(f"确认使用设备: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
        except Exception as e:
            logger.error(f"EasyOCR 初始化失败: {e}", exc_info=True)
            raise
    
    return _reader


def recognize_text(image, languages=None, 
                   min_confidence=0.15, use_gpu=None, roi=None):
    """
    对图片进行OCR文字识别
    
    Args:
        image: PIL.Image对象或图片文件路径
        languages (list): OCR语言列表，默认为 ['ch_sim', 'en']
        min_confidence (float): 最小置信度阈值，默认为0.15
        use_gpu (bool): 是否使用GPU，默认为None（自动检测）
        roi (tuple): 感兴趣区域 (x1, y1, x2, y2)，默认为None（全图）
    
    Returns:
        Tuple[List[Dict[str, Any]], float]: (识别结果列表, 耗时)
            - 识别结果列表：每个元素包含 text, confidence, bbox
            - 耗时：OCR识别耗时（秒）
    """
    global _reader
    
    try:
        # 初始化阅读器（如果尚未初始化）
        if _reader is None:
            init_reader(languages, use_gpu)
        
        # 如果传入的是文件路径，则打开图片
        if isinstance(image, str):
            image = Image.open(image)
        
        # 调试信息
        logger.debug(f"图像类型: {type(image)}, 尺寸: {image.size}")
        logger.debug(f"languages: {languages}, min_confidence: {min_confidence}, use_gpu: {use_gpu}, roi: {roi}")
        
        # 应用ROI裁剪
        if roi is not None:
            x1, y1, x2, y2 = roi
            image = image.crop((x1, y1, x2, y2))
        
        # 直接使用原始图像，不进行预处理
        img_array = np.array(image)
        
        # 获取EasyOCR性能参数（支持动态调整）
        default_canvas_size = config.get('ocr.easyocr.canvas_size', 1920)
        default_mag_ratio = config.get('ocr.easyocr.mag_ratio', 1.5)
        dynamic_params = config.get('ocr.easyocr.dynamic_params', True)
        
        # 根据图像尺寸动态调整参数
        if dynamic_params:
            width, height = image.size
            # 对于大图像，降低canvas_size和mag_ratio以提升速度
            if width > 1920 or height > 1080:
                canvas_size = min(default_canvas_size, 1280)
                mag_ratio = min(default_mag_ratio, 1.0)
            elif width > 1280 or height > 720:
                canvas_size = default_canvas_size
                mag_ratio = default_mag_ratio
            else:
                # 小图像可以使用更小的参数
                canvas_size = min(default_canvas_size, 1280)
                mag_ratio = default_mag_ratio
        else:
            canvas_size = default_canvas_size
            mag_ratio = default_mag_ratio
        
        logger.debug(f"EasyOCR参数: canvas_size={canvas_size}, mag_ratio={mag_ratio}")
        
        # 进行OCR识别，使用优化后的参数
        logger.debug("开始OCR识别...")
        start_time = time.time()
        results = _reader.readtext(
            img_array,
            detail=1,  # 返回详细信息（边界框、置信度）
            paragraph=False,  # 不自动合并段落
            width_ths=0.5,  # 宽度阈值，提高以增加合并
            height_ths=0.5,  # 高度阈值，提高以增加合并
            contrast_ths=0.2,  # 对比度阈值，降低
            adjust_contrast=0.5,  # 对比度调整
            text_threshold=0.4,  # 文本阈值，降低
            low_text=0.2,  # 低文本阈值，降低
            link_threshold=0.2,  # 链接阈值，降低
            canvas_size=canvas_size,  # 动态调整的画布大小
            mag_ratio=mag_ratio  # 动态调整的放大比例
        )
        ocr_duration = time.time() - start_time
        logger.debug(f"OCR识别完成，共识别到 {len(results)} 个结果，耗时: {ocr_duration:.3f}秒")
        
        # 提取所有识别到的文字，按位置排序
        text_items: List[Dict[str, Any]] = []
        for (bbox, text, confidence) in results:
            if confidence >= min_confidence:
                y_coord = np.mean([point[1] for point in bbox])
                text_items.append({
                    'text': text,
                    'confidence': float(confidence),
                    'bbox': bbox.tolist()
                })
                
        # 按Y坐标排序（从上到下）
        text_items.sort(key=lambda x: x['bbox'][0][1])
        
        return text_items, ocr_duration
        
    except Exception as e:
        logger.error(f"OCR识别时出错: {e}", exc_info=True)
        return "", 0.0


def recognize_and_print(image, languages=None, save_dir="output", 
                       timestamp=None, use_gpu=None, roi=None, save_result=True):
    """
    对图片进行OCR识别并保存结果到文件
    
    Args:
        image: PIL.Image对象或图片文件路径
        languages (list): OCR语言列表，默认为 ['ch_sim', 'en']
        save_dir (str): 保存目录，默认为 "output"
        timestamp (str): 时间戳，用于生成文件名。如果为None，则自动生成
        use_gpu (bool): 是否使用GPU，默认为None（自动检测）
        roi (tuple): 感兴趣区域 (x1, y1, x2, y2)，默认为None（全图）
        save_result (bool): 是否保存OCR结果文件
    
    Returns:
        List[Dict[str, Any]]: 识别结果列表，每个元素包含 text, confidence, bbox
    """
    min_confidence = config.get('ocr.min_confidence', 0.3)
    
    text_items, ocr_duration = recognize_text(image, languages, 
                         min_confidence=min_confidence, use_gpu=use_gpu, roi=roi)
    
    if text_items:
        logger.info(f"OCR识别完成，已识别到 {len(text_items)} 个文本区域，耗时: {ocr_duration:.3f}秒")
    else:
        logger.info(f"OCR识别完成，未识别到文字内容，耗时: {ocr_duration:.3f}秒")
    
    if not save_result:
        return text_items
        
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    save_dir_basename = os.path.basename(save_dir)
    is_minute_mode = (len(save_dir_basename) == 13 and 
                     save_dir_basename[8] == '_' and 
                     save_dir_basename[:8].isdigit() and 
                     save_dir_basename[9:].isdigit())
    
    if is_minute_mode:
        txt_filename = os.path.join(save_dir, "ocr_result.txt")
    else:
        txt_filename = os.path.join(save_dir, f"ocr_result_{timestamp}.txt")
    
    text_lines = [item['text'] for item in text_items]
    text_content = '\n'.join(text_lines)
    
    try:
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"OCR耗时: {ocr_duration:.3f}秒\n")
            f.write(f"OCR识别结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if roi:
                f.write(f"ROI区域: {roi}\n")
            f.write("="*60 + "\n\n")
            
            if text_content:
                f.write(text_content)
            else:
                f.write("未识别到文字内容")
            f.write("\n")
            
            f.write(f"\n--- 识别统计 ---\n")
            f.write(f"识别到 {len(text_items)} 个文本区域\n")
            f.write(f"OCR耗时: {ocr_duration:.3f}秒\n")
            if roi:
                f.write(f"ROI区域: {roi}\n")
        logger.info(f"OCR结果已保存: {txt_filename}")
    except Exception as e:
        logger.error(f"保存OCR结果时出错: {e}", exc_info=True)
    
    return text_items


if __name__ == "__main__":
    """直接运行此脚本时，测试OCR功能"""
    print("OCR识别模块测试")
    print("请提供图片路径进行测试")







