"""
OCR识别模块
对图片进行OCR文字识别
使用 EasyOCR 库（纯Python实现，无需安装Tesseract）
包含图像预处理优化以提高识别准确率
"""

import os
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import numpy as np
import cv2


# 全局 EasyOCR 阅读器（延迟初始化）
_reader = None
_languages = ['ch_sim', 'en']  # 中文简体和英文


def init_reader(languages=None):
    """
    初始化 EasyOCR 阅读器
    
    Args:
        languages (list): 语言列表，默认为 ['ch_sim', 'en']
    
    Returns:
        easyocr.Reader: OCR阅读器对象
    """
    global _reader, _languages
    
    if languages is None:
        languages = _languages
    
    if _reader is None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在初始化 EasyOCR（首次运行会下载模型，请稍候）...")
        try:
            _reader = easyocr.Reader(languages, gpu=False)  # gpu=False 使用CPU
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] EasyOCR 初始化完成")
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
        
        # 应用自适应阈值二值化（提高文字对比度）
        # 使用自适应阈值可以更好地处理不同光照条件
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 降噪处理
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        # 轻微锐化（增强文字边缘）
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        # 转换回RGB格式（EasyOCR需要RGB）
        result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
        
        return result
    except Exception as e:
        # 如果预处理失败，返回原始图像
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 图像预处理失败，使用原始图像: {e}")
        return np.array(image.convert('RGB'))


def postprocess_text(text):
    """
    后处理文本，修复常见的OCR错误
    
    Args:
        text (str): 原始OCR识别文本
    
    Returns:
        str: 后处理后的文本
    """
    if not text:
        return text
    
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 修复常见的OCR错误
        # 修复常见的字符混淆
        replacements = {
            'rn': 'm',  # rn 经常被误识别为 m
            'vv': 'w',  # vv 经常被误识别为 w
            'ii': 'n',  # ii 经常被误识别为 n
        }
        
        # 修复文件名扩展名（.py, .txt等）
        if line.endswith('py') and not line.endswith('.py'):
            line = line[:-2] + '.py'
        elif line.endswith('txt') and not line.endswith('.txt'):
            line = line[:-3] + '.txt'
        elif line.endswith('png') and not line.endswith('.png'):
            line = line[:-3] + '.png'
        
        # 修复常见单词
        common_fixes = {
            'Vaw': 'View',
            'Seiection': 'Selection',
            'Terminai': 'Terminal',
        }
        
        for wrong, correct in common_fixes.items():
            if wrong in line:
                line = line.replace(wrong, correct)
        
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)


def recognize_text(image, languages=None, use_preprocessing=True, min_confidence=0.3):
    """
    对图片进行OCR文字识别
    
    Args:
        image: PIL.Image对象或图片文件路径
        languages (list): OCR语言列表，默认为 ['ch_sim', 'en']
        use_preprocessing (bool): 是否使用图像预处理，默认为True
        min_confidence (float): 最小置信度阈值，默认为0.3（降低阈值以获取更多结果）
    
    Returns:
        str: 识别出的文字内容，如果出错返回空字符串
    """
    global _reader
    
    try:
        # 初始化阅读器（如果尚未初始化）
        if _reader is None:
            init_reader(languages)
        
        # 如果传入的是文件路径，则打开图片
        if isinstance(image, str):
            image = Image.open(image)
        
        # 图像预处理
        if use_preprocessing:
            img_array = preprocess_image(image)
        else:
            # 将 PIL Image 转换为 numpy 数组
            img_array = np.array(image)
        
        # 进行OCR识别，使用更详细的参数
        results = _reader.readtext(
            img_array,
            detail=1,  # 返回详细信息（边界框、置信度）
            paragraph=False,  # 不自动合并段落
            width_ths=0.7,  # 宽度阈值，用于合并文本
            height_ths=0.7   # 高度阈值，用于合并文本
        )
        
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
        
        # 后处理文本，修复常见错误
        text = postprocess_text(text)
        
        return text
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OCR识别时出错: {e}")
        return ""


def recognize_and_print(image, languages=None, save_dir="output", timestamp=None):
    """
    对图片进行OCR识别并打印结果，同时保存到文件
    
    Args:
        image: PIL.Image对象或图片文件路径
        languages (list): OCR语言列表，默认为 ['ch_sim', 'en']
        save_dir (str): 保存目录，默认为 "output"
        timestamp (str): 时间戳，用于生成文件名。如果为None，则自动生成
    
    Returns:
        str: 识别出的文字内容
    """
    text = recognize_text(image, languages)
    
    # 打印结果
    if text:
        print(f"\n{'='*60}")
        print("OCR识别结果:")
        print('-'*60)
        print(text)
        print('='*60)
    else:
        print("\nOCR识别结果: 未识别到文字内容")
    
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
