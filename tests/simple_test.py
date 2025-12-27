"""
快速OCR测试脚本
用于快速验证OCR功能是否正常工作
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr_recognize import recognize_text
from PIL import Image, ImageDraw, ImageFont
import numpy as np


def create_test_image():
    """创建一个测试图像"""
    # 创建测试图像
    img = Image.new('RGB', (800, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # 添加测试文本
    test_texts = [
        "这是一个快速OCR测试",
        "Quick OCR Test",
        "测试中文字符识别",
        "Testing Chinese character recognition",
        "1234567890",
        "ABCDEF"
    ]
    
    y = 20
    for text in test_texts:
        draw.text((20, y), text, fill='black')
        y += 30
    
    return img


def main():
    """主函数"""
    print("=" * 60)
    print("快速OCR测试")
    print("=" * 60)
    
    # 创建测试图像
    print("\n[1] 创建测试图像...")
    test_image = create_test_image()
    print(f"测试图像尺寸: {test_image.size}")
    
    # 保存测试图像
    test_dir = "output/test"
    os.makedirs(test_dir, exist_ok=True)
    test_image_path = os.path.join(test_dir, "test_image.png")
    test_image.save(test_image_path)
    print(f"测试图像已保存: {test_image_path}")
    
    # 进行OCR识别
    print("\n[2] 进行OCR识别...")
    start_time = datetime.now()
    
    try:
        result_text = recognize_text(
            test_image,
            languages=['ch_sim', 'en'],
            use_preprocessing=True,
            min_confidence=0.3,
            use_gpu=None  # 自动检测
        )
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"\n[3] 识别结果:")
        print("-" * 60)
        if result_text:
            print(result_text)
        else:
            print("未识别到任何文本")
        print("-" * 60)
        
        print(f"\n识别耗时: {elapsed:.3f}秒")
        
        # 保存识别结果
        result_path = os.path.join(test_dir, "test_result.txt")
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"识别耗时: {elapsed:.3f}秒\n")
            f.write("\n识别结果:\n")
            f.write("-" * 60 + "\n")
            f.write(result_text if result_text else "未识别到任何文本")
            f.write("\n" + "-" * 60 + "\n")
        
        print(f"识别结果已保存: {result_path}")
        
    except Exception as e:
        print(f"\n❌ OCR识别失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
