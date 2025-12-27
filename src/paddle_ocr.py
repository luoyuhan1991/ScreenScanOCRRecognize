
"""
PaddleOCR 模块 - 屏幕扫描OCR识别程序的OCR引擎
使用 PaddleOCR 替代 EasyOCR，提供更高的识别准确率
"""

import cv2
import numpy as np
from paddleocr import PaddleOCR
import os
from datetime import datetime
import logging

# 全局OCR实例缓存
_ocr_instance = None
_ocr_config = None


def init_reader(languages=None, use_gpu=None, force_reinit=False):
    """
    初始化PaddleOCR识别器

    Args:
        languages: 语言选项 ('ch', 'en', 'chinese', 'english' 等)
        use_gpu: 是否使用GPU (True/False/None)
        force_reinit: 是否强制重新初始化

    Returns:
        PaddleOCR实例
    """
    global _ocr_instance, _ocr_config

    # 检查是否需要重新初始化
    current_config = (languages, use_gpu)
    if not force_reinit and _ocr_instance is not None and _ocr_config == current_config:
        return _ocr_instance

    # 语言映射
    lang_map = {
        'ch': 'ch',        # 中文
        'en': 'en',        # 英文
        'chinese': 'ch',   # 中文
        'english': 'en',   # 英文
        'french': 'french', # 法语
        'german': 'german', # 德语
        'korean': 'korean', # 韩语
        'japan': 'japan'    # 日语
    }

    # 确定语言参数，默认使用中文
    if languages is None or languages not in lang_map:
        ocr_lang = 'ch'  # 默认中文
    else:
        ocr_lang = lang_map[languages]

    print(f"[DEBUG] 初始化PaddleOCR，语言: {ocr_lang}")

    # 创建PaddleOCR实例
    ocr = PaddleOCR(
        lang=ocr_lang,         # 语言设置
    )

    # 缓存实例和配置
    _ocr_instance = ocr
    _ocr_config = current_config

    return ocr


def recognize_and_print(image, languages=None, save_dir="output",
                        timestamp=None, use_gpu=None, roi=None):
    """
    使用PaddleOCR进行文字识别并保存结果

    Args:
        image: PIL图像对象或numpy数组
        languages: 语言选项
        save_dir: 保存目录
        timestamp: 时间戳
        use_gpu: 是否使用GPU
        roi: ROI区域信息

    Returns:
        list: 识别结果列表
    """
    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)

    # 初始化OCR（使用缓存的实例）
    ocr = init_reader(languages, use_gpu)

    # 将PIL图像转换为numpy数组（如果需要）
    if hasattr(image, 'convert'):  # PIL Image
        img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    else:
        img_array = image

    try:
        print(f"[DEBUG] 开始OCR识别...")
        print(f"[DEBUG] 图像尺寸: {img_array.shape}")
        # 执行OCR识别（使用ocr方法）
        result = ocr.ocr(img_array)
        print(f"[DEBUG] OCR识别完成，结果类型: {type(result)}")
        print(f"[DEBUG] OCR结果长度: {len(result) if result else 0}")
        if result and len(result) > 0:
            print(f"[DEBUG] result[0] 类型: {type(result[0])}")
            print(f"[DEBUG] result[0] 内容: {result[0]}")

        # 提取识别结果
        extracted_text = []
        if result and len(result) > 0:
            # PaddleOCR 3.x 返回格式: [OCRResult对象]
            # OCRResult 是一个字典，包含 rec_texts, rec_scores, rec_polys 等键
            ocr_result = result[0]
            
            if isinstance(ocr_result, dict):
                # 新版本格式
                texts = ocr_result.get('rec_texts', [])
                scores = ocr_result.get('rec_scores', [])
                polys = ocr_result.get('rec_polys', [])
                
                for i, text in enumerate(texts):
                    text_item = {
                        'text': text,
                        'confidence': float(scores[i]) if i < len(scores) else 1.0,
                        'bbox': polys[i].tolist() if i < len(polys) else None
                    }
                    extracted_text.append(text_item)
            elif isinstance(ocr_result, list) and len(ocr_result) > 0:
                # 旧版本格式兼容
                for line in ocr_result:
                    if line and len(line) >= 2:
                        text = line[1][0]
                        confidence = line[1][1]
                        text_item = {
                            'text': text,
                            'confidence': confidence,
                            'bbox': line[0]
                        }
                        extracted_text.append(text_item)

        if extracted_text:
            print(f"[DEBUG] 提取识别结果，共 {len(extracted_text)} 行")
        else:
            print(f"[DEBUG] 未识别到任何文本")

        # 保存识别结果
        save_ocr_results(extracted_text, save_dir, timestamp, roi)

        # 打印识别结果
        print_ocr_results(extracted_text)

        return extracted_text

    except Exception as e:
        logging.error(f"PaddleOCR识别出错: {e}")
        return []


def save_ocr_results(results, save_dir, timestamp, roi=None):
    """保存OCR结果到文件"""
    if not results:
        # 即使没有识别到文本也保存空结果文件
        result_file = os.path.join(save_dir, "ocr_result.txt")
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("未识别到任何文本\n")
            f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if roi:
                f.write(f"ROI区域: {roi}\n")
        print(f"OCR结果已保存到: {result_file}")
        return

    # 生成结果文件名
    result_file = os.path.join(save_dir, "ocr_result.txt")

    # 写入识别结果
    with open(result_file, 'w', encoding='utf-8') as f:
        for item in results:
            text = item['text']
            confidence = item['confidence']
            f.write(f"[置信度: {confidence:.2f}] {text}\n")

        # 添加统计信息
        total_chars = sum(len(item['text']) for item in results)
        avg_confidence = sum(item['confidence'] for item in results) / len(results) if results else 0

        f.write(f"\n--- 识别统计 ---\n")
        f.write(f"总字符数: {total_chars}\n")
        f.write(f"平均置信度: {avg_confidence:.2f}\n")
        f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if roi:
            f.write(f"ROI区域: {roi}\n")

    print(f"OCR结果已保存到: {result_file}")


def print_ocr_results(results):
    """打印OCR结果到控制台"""
    if not results:
        print("未识别到任何文本")
        return

    print(f"\nOCR识别结果:")
    print("-" * 50)

    for i, item in enumerate(results, 1):
        text = item['text']
        confidence = item['confidence']
        print(f"{i:2d}. [置信度: {confidence:.2f}] {text}")

    print("-" * 50)

    # 显示统计信息
    total_chars = sum(len(item['text']) for item in results)
    avg_confidence = sum(item['confidence'] for item in results) / len(results) if results else 0

    print(f"总计: {len(results)} 个文本块, {total_chars} 个字符")
    print(f"平均置信度: {avg_confidence:.2f}")


def batch_recognize(images, languages=None, save_dir="output",
                    use_gpu=None):
    """
    批量识别多张图像

    Args:
        images: 图像列表
        languages: 语言选项
        save_dir: 保存目录
        use_gpu: 是否使用GPU

    Returns:
        list: 识别结果列表
    """
    ocr = init_reader(languages, use_gpu)
    results = []

    for i, image in enumerate(images):
        result = recognize_single_image(ocr, image)
        results.append(result)

    return results


def recognize_single_image(ocr, image):
    """
    使用已初始化的OCR识别单张图像

    Args:
        ocr: 已初始化的PaddleOCR实例
        image: 图像

    Returns:
        list: 识别结果
    """
    # 将PIL图像转换为numpy数组（如果需要）
    if hasattr(image, 'convert'):  # PIL Image
        img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    else:
        img_array = image

    # 执行OCR识别（使用ocr方法）
    result = ocr.ocr(img_array)

    # 提取识别结果
    extracted_text = []
    if result and len(result) > 0:
        # PaddleOCR 3.x 返回格式: [OCRResult对象]
        # OCRResult 是一个字典，包含 rec_texts, rec_scores, rec_polys 等键
        ocr_result = result[0]
        
        if isinstance(ocr_result, dict):
            # 新版本格式
            texts = ocr_result.get('rec_texts', [])
            scores = ocr_result.get('rec_scores', [])
            polys = ocr_result.get('rec_polys', [])
            
            for i, text in enumerate(texts):
                text_item = {
                    'text': text,
                    'confidence': float(scores[i]) if i < len(scores) else 1.0,
                    'bbox': polys[i].tolist() if i < len(polys) else None
                }
                extracted_text.append(text_item)
        elif isinstance(ocr_result, list) and len(ocr_result) > 0:
            # 旧版本格式兼容
            for line in ocr_result:
                if line and len(line) >= 2:
                    text = line[1][0]
                    confidence = line[1][1]
                    text_item = {
                        'text': text,
                        'confidence': confidence,
                        'bbox': line[0]
                    }
                    extracted_text.append(text_item)

    return extracted_text