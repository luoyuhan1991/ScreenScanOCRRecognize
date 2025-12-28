"""
OCR识别模块
对图片进行OCR文字识别
使用 EasyOCR 库（纯Python实现，无需安装Tesseract）
包含图像预处理优化以提高识别准确率
"""

import os
import time
from datetime import datetime

import cv2
import easyocr
import numpy as np
from PIL import Image

from .config import config
from .logger import logger

# 全局 EasyOCR 阅读器（延迟初始化）
_reader = None
_languages = ['ch_sim', 'en']  # 中文简体和英文
_use_gpu = False  # 是否使用GPU，自动检测

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
        # 转换语言代码为EasyOCR支持的格式
        if isinstance(languages, list):
            # 如果是列表，转换每个语言代码
            languages = [EASYOCR_LANG_MAP.get(lang, lang) for lang in languages]
        elif isinstance(languages, str):
            # 如果是字符串，转换为列表并映射
            languages = [EASYOCR_LANG_MAP.get(languages, languages)]
        else:
            languages = _languages
    
    if use_gpu is None:
        # 从配置读取GPU设置 - 强制使用GPU
        force_gpu = config.get('gpu.force_gpu', True)  # 默认强制使用GPU
        force_cpu = config.get('gpu.force_cpu', False)
        auto_detect = config.get('gpu.auto_detect', False)
        
        if force_cpu:
            new_use_gpu = False
            logger.info("EasyOCR: 强制使用CPU（配置覆盖）")
        elif force_gpu:
            new_use_gpu = True  # 强制使用GPU
            logger.info("EasyOCR: 强制使用GPU")
            # 验证GPU是否可用
            try:
                import torch
                if torch.cuda.is_available():
                    logger.info(f"检测到GPU: {torch.cuda.get_device_name(0)}")
                else:
                    logger.warning("强制使用GPU但未检测到可用GPU，将尝试使用GPU（可能失败）")
            except ImportError:
                logger.warning("无法导入torch，无法验证GPU状态")
        elif auto_detect:
            # 自动检测GPU
            try:
                import torch
                new_use_gpu = torch.cuda.is_available()
                logger.debug(f"torch.cuda.is_available() = {new_use_gpu}")
                if new_use_gpu:
                    logger.info(f"检测到GPU: {torch.cuda.get_device_name(0)}")
                else:
                    logger.info("未检测到GPU，使用CPU")
            except ImportError:
                new_use_gpu = False
        else:
            new_use_gpu = True  # 默认强制使用GPU
            logger.info("EasyOCR: 强制使用GPU（默认）")
    else:
        new_use_gpu = bool(use_gpu)
        if new_use_gpu:
            logger.info("EasyOCR: 使用传入的GPU设置（启用）")
    
    # 检查是否需要重新初始化
    # 1. reader为None（首次初始化）
    # 2. 强制重新初始化
    # 3. GPU状态发生变化（从CPU变成GPU）
    need_reinit = (_reader is None or 
                   force_reinit or 
                   (new_use_gpu and not _use_gpu))
    
    _use_gpu = new_use_gpu
    
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


def preprocess_image(image, enable_clahe=True, enable_sharpen=True, fast_mode=False):
    """
    图像预处理，提高OCR识别准确率
    
    Args:
        image: PIL.Image对象
        enable_clahe: 是否启用CLAHE对比度增强
        enable_sharpen: 是否启用锐化处理
        fast_mode: 快速模式（跳过部分处理）
    
    Returns:
        numpy.ndarray: 预处理后的图像数组
    """
    try:
        # 转换为RGB（如果不是）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 快速模式：直接返回RGB数组，跳过所有预处理
        if fast_mode:
            return img_array
        
        # 转换为OpenCV格式 (BGR)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 转换为灰度图
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # 增强对比度（使用CLAHE - 自适应直方图均衡化）
        if enable_clahe:
            clahe_clip_limit = config.get('ocr.preprocessing.clahe_clip_limit', 3.0)
            clahe_tile_size = config.get('ocr.preprocessing.clahe_tile_size', 8)
            clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=(clahe_tile_size, clahe_tile_size))
            enhanced = clahe.apply(gray)
        else:
            enhanced = gray
        
        # 添加锐化处理，提高文字边缘清晰度
        if enable_sharpen:
            kernel = np.array([[-1, -1, -1],
                              [-1,  9, -1],
                              [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
        else:
            sharpened = enhanced
        
        # 转换回RGB格式（EasyOCR需要RGB）
        result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
        
        return result
    except Exception as e:
        # 如果预处理失败，返回原始图像
        logger.warning(f"图像预处理失败，使用原始图像: {e}")
        return np.array(image.convert('RGB'))


def optimize_image_resolution(image, min_width=640, max_width=2560, fast_mode=False):
    """
    优化图像分辨率，找到最佳识别尺寸
    
    Args:
        image: PIL.Image对象
        min_width (int): 最小宽度，默认640（降低以避免过度放大小图像）
        max_width (int): 最大宽度，默认2560
        fast_mode (bool): 快速模式，使用更快的重采样算法
    
    Returns:
        PIL.Image: 优化后的图像
    """
    try:
        width, height = image.size
        
        # 如果宽度在合理范围内，不处理
        if min_width <= width <= max_width:
            return image
        
        # 计算缩放比例
        if width < min_width:
            # 放大图像
            scale = min_width / width
        else:
            # 缩小图像
            scale = max_width / width
        
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # 根据模式选择重采样算法
        if fast_mode:
            # 快速模式：使用BILINEAR（速度更快）
            resample = Image.Resampling.BILINEAR
        else:
            # 质量模式：使用LANCZOS（质量更高但速度较慢）
            resample = Image.Resampling.LANCZOS
        
        optimized = image.resize((new_width, new_height), resample)
        
        return optimized
    except Exception as e:
        logger.warning(f"图像分辨率优化失败，使用原始图像: {e}")
        return image


def postprocess_text(text):
    """
    后处理文本，修复常见的OCR错误
    （当前版本保留方法结构，暂不实现具体逻辑）
    
    Args:
        text (str): 原始OCR识别文本
    
    Returns:
        str: 后处理后的文本
    """
    # 保留方法结构，暂不实现具体后处理逻辑
    # 未来可以根据需要添加文本纠错、格式化等功能
    return text


def recognize_text(image, languages=None, use_preprocessing=True, 
                   min_confidence=0.15, use_gpu=None, roi=None):
    """
    对图片进行OCR文字识别
    
    Args:
        image: PIL.Image对象或图片文件路径
        languages (list): OCR语言列表，默认为 ['ch_sim', 'en']
        use_preprocessing (bool): 是否使用图像预处理，默认为True
        min_confidence (float): 最小置信度阈值，默认为0.15（降低以提高识别率）
        use_gpu (bool): 是否使用GPU，默认为None（自动检测）
        roi (tuple): 感兴趣区域 (x1, y1, x2, y2)，默认为None（全图）
    
    Returns:
        str: 识别出的文字内容，如果出错返回空字符串
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
        logger.debug(f"languages: {languages}, use_preprocessing: {use_preprocessing}")
        logger.debug(f"min_confidence: {min_confidence}, use_gpu: {use_gpu}, roi: {roi}")
        
        # 应用ROI裁剪
        if roi is not None:
            x1, y1, x2, y2 = roi
            image = image.crop((x1, y1, x2, y2))
        
        # 获取快速模式设置
        fast_mode = config.get('ocr.preprocessing.fast_mode', False)
        min_width = config.get('ocr.preprocessing.min_width', 640)
        max_width = config.get('ocr.preprocessing.max_width', 2560)
        
        # 优化图像分辨率
        image = optimize_image_resolution(image, min_width=min_width, 
                                        max_width=max_width, fast_mode=fast_mode)
        
        # 获取预处理配置
        enable_clahe = config.get('ocr.preprocessing.enable_clahe', True)
        enable_sharpen = config.get('ocr.preprocessing.enable_sharpen', True)
        fast_mode = config.get('ocr.preprocessing.fast_mode', False)
        
        # 图像预处理
        if use_preprocessing:
            img_array = preprocess_image(image, enable_clahe=enable_clahe, 
                                       enable_sharpen=enable_sharpen, 
                                       fast_mode=fast_mode)
        else:
            # 将 PIL Image 转换为 numpy 数组
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
        text_items = []
        for (bbox, text, confidence) in results:
            if confidence >= min_confidence:
                # 计算文本的Y坐标（用于排序）
                y_coord = np.mean([point[1] for point in bbox])
                text_items.append((y_coord, text, confidence))
                
        # 按Y坐标排序（从上到下）
        text_items.sort(key=lambda x: x[0])
        
        # 提取文字内容
        text_lines = [item[1] for item in text_items]
        
        # 合并所有文字行
        text = '\n'.join(text_lines)
        text = text.strip()
        
        # 后处理文本（当前版本不执行具体逻辑）
        text = postprocess_text(text)
        
        # 将耗时信息附加到返回值（通过全局变量传递，因为返回值是字符串）
        # 这里我们通过修改函数签名来传递耗时
        return text, ocr_duration
        
    except Exception as e:
        logger.error(f"OCR识别时出错: {e}", exc_info=True)
        return "", 0.0


def recognize_and_print(image, languages=None, save_dir="output", 
                       timestamp=None, use_gpu=None, roi=None):
    """
    对图片进行OCR识别并保存结果到文件
    
    Args:
        image: PIL.Image对象或图片文件路径
        languages (list): OCR语言列表，默认为 ['ch_sim', 'en']
        save_dir (str): 保存目录，默认为 "output"
        timestamp (str): 时间戳，用于生成文件名。如果为None，则自动生成
        use_gpu (bool): 是否使用GPU，默认为None（自动检测）
        roi (tuple): 感兴趣区域 (x1, y1, x2, y2)，默认为None（全图）
    
    Returns:
        str: 识别出的文字内容
    """
    # 获取配置中的最小置信度阈值
    min_confidence = config.get('ocr.min_confidence', 0.3)
    
    text, ocr_duration = recognize_text(image, languages, use_preprocessing=True, 
                         min_confidence=min_confidence, use_gpu=use_gpu, roi=roi)
    
    # 记录识别时间（不输出识别结果内容）
    if text:
        logger.info(f"OCR识别完成，已识别到文字内容，耗时: {ocr_duration:.3f}秒")
    else:
        logger.info(f"OCR识别完成，未识别到文字内容，耗时: {ocr_duration:.3f}秒")
    
    # 保存到文件
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建输出目录
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 保存OCR结果到文本文件
    # 判断是否在按分钟模式下：save_dir的父目录是output，且save_dir是分钟文件夹（格式：YYYYMMDD_HHMM）
    save_dir_basename = os.path.basename(save_dir)
    # 分钟文件夹格式：YYYYMMDD_HHMM（13个字符，包含下划线）
    # 例如：20251229_0145（下划线在第9位，索引8）
    is_minute_mode = (len(save_dir_basename) == 13 and 
                     save_dir_basename[8] == '_' and 
                     save_dir_basename[:8].isdigit() and 
                     save_dir_basename[9:].isdigit())
    
    if is_minute_mode:
        # 按分钟模式：使用固定的ocr_result.txt文件名
        txt_filename = os.path.join(save_dir, "ocr_result.txt")
    else:
        # 其他模式：使用带时间戳的文件名
        txt_filename = os.path.join(save_dir, f"ocr_result_{timestamp}.txt")
    try:
        with open(txt_filename, 'w', encoding='utf-8') as f:
            # 在文件开头显示耗时信息（更明显）
            f.write(f"OCR耗时: {ocr_duration:.3f}秒\n")
            f.write(f"OCR识别结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if roi:
                f.write(f"ROI区域: {roi}\n")
            f.write("="*60 + "\n\n")
            
            # 写入识别内容
            if text:
                f.write(text)
            else:
                f.write("未识别到文字内容")
            f.write("\n")
            
            # 统计信息
            f.write(f"\n--- 识别统计 ---\n")
            f.write(f"OCR耗时: {ocr_duration:.3f}秒\n")
            if roi:
                f.write(f"ROI区域: {roi}\n")
        logger.info(f"OCR结果已保存: {txt_filename}")
    except Exception as e:
        logger.error(f"保存OCR结果时出错: {e}", exc_info=True)
    
    return text


if __name__ == "__main__":
    """直接运行此脚本时，测试OCR功能"""
    print("OCR识别模块测试")
    print("请提供图片路径进行测试")







