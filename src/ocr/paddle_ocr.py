
"""
PaddleOCR 模块 - 屏幕扫描OCR识别程序的OCR引擎
使用 PaddleOCR 替代 EasyOCR，提供更高的识别准确率
"""

import glob
import os
import time
from datetime import datetime

import cv2
import numpy as np
from paddleocr import PaddleOCR

from ..config.config import config
from ..utils.logger import logger

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

    # 处理语言参数（只支持字符串）
    # PaddleOCR只支持单个语言字符串，不支持多语言组合
    # 使用OCRConfig中的语言映射（统一管理）
    from ..ocr.ocr_adapter import OCRConfig
    
    if languages is None:
        ocr_lang = 'ch'  # 默认中文
    elif isinstance(languages, str):
        # 使用统一的语言映射
        ocr_lang = OCRConfig.PADDLE_LANG_MAP.get(languages, languages)
        # 如果映射后不在有效值中，使用默认值
        if ocr_lang not in OCRConfig.PADDLE_LANG_MAP.values():
            ocr_lang = 'ch'
    else:
        # 如果不是字符串，转换为字符串（兼容处理）
        ocr_lang = str(languages) if languages else 'ch'
        logger.warning(f"PaddleOCR期望字符串类型语言参数，收到: {type(languages)}，已转换")

    logger.debug(f"初始化PaddleOCR，语言: {ocr_lang}")

    # GPU配置处理（适配器模式已通过OCRConfig统一处理，这里保留简化逻辑以兼容直接调用）
    if use_gpu is None:
        # 从配置读取GPU设置（简化版，完整逻辑在OCRConfig中）
        force_cpu = config.get('gpu.force_cpu', False)
        force_gpu = config.get('gpu.force_gpu', True)
        auto_detect = config.get('gpu.auto_detect', False)
        
        if force_cpu:
            use_gpu = False
        elif force_gpu:
            use_gpu = True
        elif auto_detect:
            try:
                import paddle
                use_gpu = paddle.is_compiled_with_cuda()
            except ImportError:
                use_gpu = False
        else:
            use_gpu = True  # 默认使用GPU
        logger.info(f"PaddleOCR GPU设置: {'启用' if use_gpu else '禁用'}")
    else:
        use_gpu = bool(use_gpu)
        if use_gpu:
            logger.info("PaddleOCR: 使用传入的GPU设置（启用）")
    
    # 确定设备类型（新版本PaddleOCR使用device参数替代use_gpu）
    device = 'gpu' if use_gpu else 'cpu'
    logger.info(f"PaddleOCR GPU设置: {'启用' if use_gpu else '禁用'} (device={device})")

    # 创建PaddleOCR实例
    # 注意：新版本PaddleOCR（3.0+）使用device参数替代use_gpu
    # use_angle_cls在新版本中可能已弃用，先尝试不使用该参数
    try:
        # 优先使用新版本参数（3.0+）
        ocr = PaddleOCR(
            lang=ocr_lang,         # 语言设置
            device=device,         # 设备类型：'gpu' 或 'cpu'（新版本）
            enable_mkldnn=False,  # Intel CPU优化（Windows上可能有问题，先关闭）
        )
        logger.debug("使用PaddleOCR新版本参数（device）")
    except (TypeError, ValueError) as e:
        # 如果device参数不支持，尝试添加use_angle_cls（兼容2.x版本）
        try:
            logger.warning("PaddleOCR版本可能较旧，尝试使用use_angle_cls参数")
            ocr = PaddleOCR(
                lang=ocr_lang,
                device=device,
                use_angle_cls=True,  # 角度分类（2.x版本）
                enable_mkldnn=False,
            )
        except (TypeError, ValueError):
            # 如果还是失败，尝试使用use_gpu（兼容更旧版本）
            logger.warning("尝试使用use_gpu参数（兼容旧版本）")
            ocr = PaddleOCR(
                lang=ocr_lang,
                use_gpu=use_gpu,    # 旧版本参数
                use_angle_cls=True,
                enable_mkldnn=False,
            )

    # 缓存实例和配置
    _ocr_instance = ocr
    _ocr_config = current_config

    return ocr


def recognize_and_print(image, languages=None, save_dir="output",
                        timestamp=None, use_gpu=None, roi=None, save_result=True):
    """
    使用PaddleOCR进行文字识别并保存结果

    Args:
        image: PIL图像对象或numpy数组
        languages: 语言选项
        save_dir: 保存目录
        timestamp: 时间戳
        use_gpu: 是否使用GPU
        roi: ROI区域信息
        save_result: 是否保存OCR结果文件

    Returns:
        list: 识别结果列表
    """
    # 确保保存目录存在
    if save_result:
        os.makedirs(save_dir, exist_ok=True)

    # 初始化OCR（使用缓存的实例）
    ocr = init_reader(languages, use_gpu)

    # 将PIL图像转换为numpy数组
    if hasattr(image, 'convert'):  # PIL Image
        # 先转换为RGB（确保颜色通道正确）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    else:
        img_array = image

    # 应用ROI裁剪（如果提供）
    # 注意：如果image已经是裁剪后的图像，roi可能为None或不需要再次应用
    if roi is not None:
        x1, y1, x2, y2 = roi
        # 确保ROI坐标在图像范围内
        h, w = img_array.shape[:2]
        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
        x2 = max(x1, min(x2, w))
        y2 = max(y1, min(y2, h))
        if x2 > x1 and y2 > y1:
            img_array = img_array[y1:y2, x1:x2]
            logger.debug(f"应用ROI裁剪: ({x1}, {y1}, {x2}, {y2})")
        else:
            logger.warning(f"ROI坐标无效，跳过裁剪: ({x1}, {y1}, {x2}, {y2})")

    # 图像取反处理：将黑底白字转换为白底黑字
    img_array_inverted = cv2.bitwise_not(img_array)
    logger.debug(f"图像取反处理完成，图像尺寸: {img_array_inverted.shape}")

    # 保存处理后的图像（根据配置决定是否保存）
    # 如果 save_result 为 False，则不保存处理后的图像
    save_processed_image = config.get('ocr.save_processed_image', True)
    if save_processed_image and save_result:
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 删除旧的processed_*.png文件（只保留最新一张）
        processed_pattern = os.path.join(save_dir, "processed_*.png")
        old_processed_files = glob.glob(processed_pattern)
        if old_processed_files:
            try:
                for old_file in old_processed_files:
                    os.remove(old_file)
                logger.debug(f"已删除 {len(old_processed_files)} 张旧的处理后图像")
            except Exception as e:
                logger.warning(f"删除旧的处理后图像失败: {e}")
        
        # 生成处理后图像的文件名
        processed_filename = os.path.join(save_dir, f"processed_{timestamp}.png")
        try:
            cv2.imwrite(processed_filename, img_array_inverted)
            logger.info(f"处理后的图像已保存: {processed_filename}")
        except Exception as e:
            logger.warning(f"保存处理后图像失败: {e}")

    try:
        logger.debug(f"开始OCR识别，图像尺寸: {img_array_inverted.shape}")
        # 记录开始时间
        start_time = time.time()
        # 执行OCR识别（使用处理后的图像）
        result = ocr.ocr(img_array_inverted)
        # 计算耗时
        ocr_duration = time.time() - start_time
        logger.debug(f"OCR识别完成，结果类型: {type(result)}, 结果长度: {len(result) if result else 0}, 耗时: {ocr_duration:.3f}秒")

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
            logger.info(f"提取识别结果，共 {len(extracted_text)} 行")
        else:
            logger.info("未识别到任何文本")

        # 保存识别结果（传入耗时信息）
        if save_result:
            save_ocr_results(extracted_text, save_dir, timestamp, roi, ocr_duration)

        # 打印识别结果
        print_ocr_results(extracted_text)

        return extracted_text

    except Exception as e:
        logger.error(f"PaddleOCR识别出错: {e}", exc_info=True)
        return []


def save_ocr_results(results, save_dir, timestamp, roi=None, ocr_duration=None):
    """保存OCR结果到文件"""
    if not results:
        # 即使没有识别到文本也保存空结果文件
        result_file = os.path.join(save_dir, "ocr_result.txt")
        with open(result_file, 'w', encoding='utf-8') as f:
            # 在文件开头显示基本信息
            f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if roi:
                f.write(f"ROI区域: {roi}\n")
            f.write("="*60 + "\n\n")
            f.write("未识别到任何文本\n")
            if ocr_duration is not None:
                f.write(f"\nOCR耗时: {ocr_duration:.3f}秒\n")
        logger.info(f"OCR结果已保存到: {result_file}")
        return

    # 生成结果文件名
    result_file = os.path.join(save_dir, "ocr_result.txt")

    # 写入识别结果
    with open(result_file, 'w', encoding='utf-8') as f:
        # 在文件开头显示基本信息
        f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if roi:
            f.write(f"ROI区域: {roi}\n")
        f.write("="*60 + "\n\n")
        
        # 写入识别结果
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
        if ocr_duration is not None:
            f.write(f"OCR耗时: {ocr_duration:.3f}秒\n")


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

    # 显示统计信息
    total_chars = sum(len(item['text']) for item in results)
    avg_confidence = sum(item['confidence'] for item in results) / len(results) if results else 0

    logger.info(f"总计: {len(results)} 个文本块, {total_chars} 个字符")
    logger.info(f"平均置信度: {avg_confidence:.2f}")