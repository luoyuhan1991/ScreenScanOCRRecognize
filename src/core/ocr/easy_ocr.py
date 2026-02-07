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
        if _reader is None:
            init_reader(languages, use_gpu)
        
        if isinstance(image, str):
            image = Image.open(image)
        
        if roi is not None:
            x1, y1, x2, y2 = roi
            image = image.crop((x1, y1, x2, y2))
        
        img_array = np.array(image)
        
        default_canvas_size = config.get('ocr.easyocr.canvas_size', 1920)
        default_mag_ratio = config.get('ocr.easyocr.mag_ratio', 1.5)
        dynamic_params = config.get('ocr.easyocr.dynamic_params', True)
        
        if dynamic_params:
            width, height = image.size
            if width > 1920 or height > 1080:
                canvas_size = min(default_canvas_size, 1280)
                mag_ratio = min(default_mag_ratio, 1.0)
            elif width > 1280 or height > 720:
                canvas_size = default_canvas_size
                mag_ratio = default_mag_ratio
            else:
                canvas_size = min(default_canvas_size, 1280)
                mag_ratio = default_mag_ratio
        else:
            canvas_size = default_canvas_size
            mag_ratio = default_mag_ratio
        
        logger.debug(f"开始OCR识别，图像尺寸: {img_array.shape}")
        
        start_time = time.time()
        results = _reader.readtext(
            img_array,
            detail=1,
            paragraph=False,
            width_ths=0.5,
            height_ths=0.5,
            contrast_ths=0.2,
            adjust_contrast=0.5,
            text_threshold=0.4,
            low_text=0.2,
            link_threshold=0.2,
            canvas_size=canvas_size,
            mag_ratio=mag_ratio
        )
        ocr_duration = time.time() - start_time
        logger.debug(f"OCR识别完成，结果类型: {type(results)}, 结果长度: {len(results)}, 耗时: {ocr_duration:.3f}秒")
        
        text_items: List[Dict[str, Any]] = []
        for (bbox, text, confidence) in results:
            if confidence >= min_confidence:
                y_coord = np.mean([point[1] for point in bbox])
                bbox_list = bbox.tolist() if hasattr(bbox, 'tolist') else list(bbox)
                text_items.append({
                    'text': text,
                    'confidence': float(confidence),
                    'bbox': bbox_list
                })
                
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
        logger.info(f"提取识别结果，共 {len(text_items)} 行")
    else:
        logger.info("未识别到任何文本")
    
    print_ocr_results(text_items)
    
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
    
    try:
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if roi:
                f.write(f"ROI区域: {roi}\n")
            f.write("="*60 + "\n\n")
            
            for item in text_items:
                text = item['text']
                confidence = item['confidence']
                f.write(f"[置信度: {confidence:.2f}] {text}\n")

            total_chars = sum(len(item['text']) for item in text_items)
            avg_confidence = sum(item['confidence'] for item in text_items) / len(text_items) if text_items else 0

            f.write(f"\n--- 识别统计 ---\n")
            f.write(f"总字符数: {total_chars}\n")
            f.write(f"平均置信度: {avg_confidence:.2f}\n")
            f.write(f"OCR耗时: {ocr_duration:.3f}秒\n")
        logger.info(f"OCR结果已保存到: {txt_filename}")
    except Exception as e:
        logger.error(f"保存OCR结果时出错: {e}", exc_info=True)
    
    return text_items


def print_ocr_results(results):
    """打印OCR结果到控制台"""
    if not results:
        logger.info("未识别到任何文本")
        return

    logger.info("OCR识别结果:")
    logger.info("-" * 50)

    for i, item in enumerate(results, 1):
        text = item['text']
        confidence = item['confidence']
        logger.info(f"{i:2d}. [置信度: {confidence:.2f}] {text}")

    logger.info("-" * 50)

    total_chars = sum(len(item['text']) for item in results)
    avg_confidence = sum(item['confidence'] for item in results) / len(results) if results else 0

    logger.info(f"总计: {len(results)} 个文本块, {total_chars} 个字符")
    logger.info(f"平均置信度: {avg_confidence:.2f}")


if __name__ == "__main__":
    """直接运行此脚本时，测试OCR功能"""
    print("OCR识别模块测试")
    print("请提供图片路径进行测试")







