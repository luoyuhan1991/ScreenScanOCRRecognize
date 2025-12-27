"""
OCR识别模块
对图片进行OCR文字识别
使用 EasyOCR 库（纯Python实现，无需安装Tesseract）
包含图像预处理优化以提高识别准确率
"""

import os
from datetime import datetime
from PIL import Image, ImageEnhance
import easyocr
import numpy as np
import cv2


# 全局 EasyOCR 阅读器（延迟初始化）
_reader = None
_languages = ['ch_sim', 'en']  # 中文简体和英文
_use_gpu = False  # 是否使用GPU，自动检测


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
    
    if use_gpu is None:
        # 自动检测GPU - 直接使用 PyTorch 的检测结果
        import torch
        new_use_gpu = torch.cuda.is_available()
        print(f"[调试] torch.cuda.is_available() = {new_use_gpu}")
        if new_use_gpu:
            print(f"[调试] GPU设备: {torch.cuda.get_device_name(0)}")
    else:
        new_use_gpu = use_gpu
        print(f"[调试] 使用指定的GPU设置: {new_use_gpu}")
    
    # 检查是否需要重新初始化
    # 1. reader为None（首次初始化）
    # 2. 强制重新初始化
    # 3. GPU状态发生变化（从CPU变成GPU）
    need_reinit = (_reader is None or 
                   force_reinit or 
                   (new_use_gpu and not _use_gpu))
    
    _use_gpu = new_use_gpu
    
    if need_reinit:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在初始化 EasyOCR（首次运行会下载模型，请稍候）...")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] GPU加速: {'启用' if _use_gpu else '未启用（使用CPU）'}")
        try:
            _reader = easyocr.Reader(languages, gpu=_use_gpu)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] EasyOCR 初始化完成")
            if _use_gpu:
                import torch
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 确认使用设备: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] EasyOCR 初始化失败: {e}")
            raise
    
    return _reader


def preprocess_image(image):
    """
    图像预处理，提高OCR识别准确率
    
    Args:
        image: PIL.Image对象
    
    Returns:
        numpy.ndarray: 预处理后的图像数组
    """
    try:
        # 转换为RGB（如果不是）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 转换为OpenCV格式 (BGR)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 转换为灰度图
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # 增强对比度（使用CLAHE - 自适应直方图均衡化）
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 添加锐化处理，提高文字边缘清晰度
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # 转换回RGB格式（EasyOCR需要RGB）
        result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
        
        return result
    except Exception as e:
        # 如果预处理失败，返回原始图像
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 图像预处理失败，使用原始图像: {e}")
        return np.array(image.convert('RGB'))


def optimize_image_resolution(image, min_width=640, max_width=2560):
    """
    优化图像分辨率，找到最佳识别尺寸
    
    Args:
        image: PIL.Image对象
        min_width (int): 最小宽度，默认640（降低以避免过度放大小图像）
        max_width (int): 最大宽度，默认2560
    
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
        
        # 使用高质量的重采样方法
        optimized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return optimized
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 图像分辨率优化失败，使用原始图像: {e}")
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
        print(f"[调试] 图像类型: {type(image)}, 尺寸: {image.size}")
        print(f"[调试] languages: {languages}, use_preprocessing: {use_preprocessing}")
        print(f"[调试] min_confidence: {min_confidence}, use_gpu: {use_gpu}, roi: {roi}")
        
        # 应用ROI裁剪
        if roi is not None:
            x1, y1, x2, y2 = roi
            image = image.crop((x1, y1, x2, y2))
        
        # 优化图像分辨率
        image = optimize_image_resolution(image)
        
        # 图像预处理
        if use_preprocessing:
            img_array = preprocess_image(image)
        else:
            # 将 PIL Image 转换为 numpy 数组
            img_array = np.array(image)
        
        # 进行OCR识别，使用优化后的参数
        print(f"[调试] 开始OCR识别...")
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
            canvas_size=2560,  # 画布大小
            mag_ratio=2.0  # 放大比例
        )
        print(f"[调试] OCR识别完成，共识别到 {len(results)} 个结果")
        
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
        
        return text
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OCR识别时出错: {e}")
        return ""


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
    text = recognize_text(image, languages, use_preprocessing=True, 
                         min_confidence=0.3, use_gpu=use_gpu, roi=roi)
    
    # 记录识别时间（不输出识别结果内容）
    if text:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OCR识别完成，已识别到文字内容")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OCR识别完成，未识别到文字内容")
    
    # 保存到文件
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建输出目录
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 保存OCR结果到文本文件
    # 如果save_dir已经是时间戳文件夹，则直接使用ocr_result.txt
    if os.path.basename(save_dir) == timestamp:
        txt_filename = os.path.join(save_dir, "ocr_result.txt")
    else:
        txt_filename = os.path.join(save_dir, f"ocr_result_{timestamp}.txt")
    try:
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"OCR识别结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n")
            if text:
                f.write(text)
            else:
                f.write("未识别到文字内容")
            f.write("\n")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OCR结果已保存: {txt_filename}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 保存OCR结果时出错: {e}")
    
    return text


if __name__ == "__main__":
    """直接运行此脚本时，测试OCR功能"""
    print("OCR识别模块测试")
    print("请提供图片路径进行测试")








