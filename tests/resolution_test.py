"""
分辨率测试脚本
测试不同分辨率下的OCR识别效果
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr_recognize import recognize_text
from PIL import Image, ImageDraw
import numpy as np


def create_test_image(width, height):
    """创建指定尺寸的测试图像"""
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 根据图像大小调整字体大小和位置
    font_size = max(12, min(width // 40, height // 10))
    
    # 添加测试文本
    test_texts = [
        "分辨率测试",
        f"Resolution: {width}x{height}",
        "OCR识别测试",
        "1234567890",
        "ABCDEF"
    ]
    
    y = max(10, height // 20)
    for text in test_texts:
        draw.text((max(10, width // 20), y), text, fill='black')
        y += font_size + 5
    
    return img


def test_resolution(width, height, test_dir):
    """测试指定分辨率"""
    print(f"\n测试分辨率: {width}x{height}")
    print("-" * 50)
    
    # 创建测试图像
    test_image = create_test_image(width, height)
    print(f"图像尺寸: {test_image.size}")
    
    # 保存测试图像
    image_filename = f"test_{width}x{height}.png"
    image_path = os.path.join(test_dir, image_filename)
    test_image.save(image_path)
    print(f"图像已保存: {image_filename}")
    
    # 进行OCR识别
    start_time = datetime.now()
    
    try:
        result_text = recognize_text(
            test_image,
            languages=['ch_sim', 'en'],
            use_preprocessing=True,
            min_confidence=0.3,
            use_gpu=None
        )
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"识别耗时: {elapsed:.3f}秒")
        
        # 保存识别结果
        result_filename = f"result_{width}x{height}.txt"
        result_path = os.path.join(test_dir, result_filename)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(f"分辨率: {width}x{height}\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"识别耗时: {elapsed:.3f}秒\n")
            f.write("\n识别结果:\n")
            f.write("-" * 50 + "\n")
            f.write(result_text if result_text else "未识别到任何文本")
            f.write("\n" + "-" * 50 + "\n")
        
        print(f"结果已保存: {result_filename}")
        
        return {
            'width': width,
            'height': height,
            'elapsed': elapsed,
            'success': True,
            'result_length': len(result_text) if result_text else 0
        }
        
    except Exception as e:
        print(f"❌ 识别失败: {e}")
        return {
            'width': width,
            'height': height,
            'elapsed': 0,
            'success': False,
            'error': str(e)
        }


def main():
    """主函数"""
    print("=" * 60)
    print("分辨率测试")
    print("=" * 60)
    
    # 测试分辨率列表
    test_resolutions = [
        (640, 480),    # 标准VGA
        (800, 600),    # SVGA
        (1024, 768),   # XGA
        (1280, 720),   # HD 720p
        (1920, 1080),  # Full HD
        (2560, 1440),  # 2K
        (3840, 2160),  # 4K
    ]
    
    # 创建测试目录
    test_dir = "output/resolution_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试结果
    results = []
    
    # 依次测试每个分辨率
    for width, height in test_resolutions:
        result = test_resolution(width, height, test_dir)
        results.append(result)
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    report_path = os.path.join(test_dir, "test_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("分辨率测试报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("测试结果汇总:\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'分辨率':<15} {'耗时(秒)':<12} {'状态':<10} {'结果长度':<10}\n")
        f.write("-" * 60 + "\n")
        
        for result in results:
            status = "成功" if result['success'] else "失败"
            result_len = result.get('result_length', 0)
            f.write(f"{result['width']}x{result['height']:<10} {result['elapsed']:<12.3f} {status:<10} {result_len:<10}\n")
        
        f.write("-" * 60 + "\n")
        
        # 统计
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        avg_time = sum(r['elapsed'] for r in results if r['success']) / success_count if success_count > 0 else 0
        
        f.write(f"\n统计信息:\n")
        f.write(f"测试总数: {total_count}\n")
        f.write(f"成功数量: {success_count}\n")
        f.write(f"失败数量: {total_count - success_count}\n")
        f.write(f"平均耗时: {avg_time:.3f}秒\n")
    
    print(f"测试报告已保存: {report_path}")
    
    # 显示汇总
    print(f"\n{'分辨率':<15} {'耗时(秒)':<12} {'状态':<10}")
    print("-" * 40)
    for result in results:
        status = "成功" if result['success'] else "失败"
        print(f"{result['width']}x{result['height']:<10} {result['elapsed']:<12.3f} {status:<10}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
