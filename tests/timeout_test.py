"""
超时测试脚本
测试OCR识别的超时处理功能
"""

import sys
import os
import time
from datetime import datetime
import threading

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr_recognize import recognize_text
from PIL import Image, ImageDraw


def create_large_test_image():
    """创建一个较大的测试图像，可能导致识别时间较长"""
    # 创建较大的图像
    img = Image.new('RGB', (1920, 1080), color='white')
    draw = ImageDraw.Draw(img)
    
    # 添加大量文本
    y = 20
    for i in range(50):
        text = f"测试行 {i+1}: 这是一个超时测试，用于验证OCR识别的超时处理功能。Test line {i+1}: This is a timeout test."
        draw.text((20, y), text, fill='black')
        y += 25
    
    return img


def create_complex_test_image():
    """创建一个复杂的测试图像，包含各种干扰"""
    img = Image.new('RGB', (1280, 720), color='white')
    draw = ImageDraw.Draw(img)
    
    # 添加各种文本和图形
    texts = [
        "正常文本 Normal text",
        "1234567890",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "abcdefghijklmnopqrstuvwxyz",
        "特殊字符: !@#$%^&*()_+-=[]{}|;':\",./<>?",
        "中文测试: 测试超时处理功能",
        "混合文本: Mixed text with 中文 and English",
    ]
    
    y = 20
    for text in texts:
        draw.text((20, y), text, fill='black')
        y += 40
    
    # 添加一些干扰元素
    for i in range(10):
        x = 100 + i * 120
        y = 400
        draw.rectangle([x, y, x+100, y+50], outline='gray', width=2)
        draw.text((x+10, y+15), f"Box {i+1}", fill='black')
    
    return img


def test_with_timeout(image, timeout_seconds, test_name, test_dir):
    """测试带超时的OCR识别"""
    print(f"\n测试: {test_name}")
    print(f"超时设置: {timeout_seconds}秒")
    print("-" * 50)
    
    result = {
        'test_name': test_name,
        'timeout': timeout_seconds,
        'success': False,
        'elapsed': 0,
        'timed_out': False,
        'error': None
    }
    
    # 保存测试图像
    image_filename = f"{test_name.replace(' ', '_')}.png"
    image_path = os.path.join(test_dir, image_filename)
    image.save(image_path)
    print(f"图像已保存: {image_filename}")
    
    # 使用线程进行超时测试
    ocr_result = {'text': None, 'error': None}
    
    def ocr_worker():
        try:
            ocr_result['text'] = recognize_text(
                image,
                languages=['ch_sim', 'en'],
                use_preprocessing=True,
                min_confidence=0.3,
                use_gpu=None
            )
        except Exception as e:
            ocr_result['error'] = str(e)
    
    # 启动OCR线程
    thread = threading.Thread(target=ocr_worker)
    start_time = time.time()
    thread.start()
    
    # 等待线程完成或超时
    thread.join(timeout=timeout_seconds)
    elapsed = time.time() - start_time
    
    if thread.is_alive():
        # 线程仍在运行，超时
        print(f"⚠️  识别超时 (超过{timeout_seconds}秒)")
        result['timed_out'] = True
        result['elapsed'] = elapsed
        
        # 注意：这里我们无法真正终止线程，只能标记为超时
        print("注意：OCR线程仍在后台运行")
    else:
        # 线程已完成
        result['elapsed'] = elapsed
        print(f"识别完成，耗时: {elapsed:.3f}秒")
        
        if ocr_result['error']:
            print(f"❌ 识别失败: {ocr_result['error']}")
            result['error'] = ocr_result['error']
        else:
            print(f"✓ 识别成功")
            result['success'] = True
            
            # 保存识别结果
            result_filename = f"{test_name.replace(' ', '_')}_result.txt"
            result_path = os.path.join(test_dir, result_filename)
            
            with open(result_path, 'w', encoding='utf-8') as f:
                f.write(f"测试名称: {test_name}\n")
                f.write(f"超时设置: {timeout_seconds}秒\n")
                f.write(f"实际耗时: {elapsed:.3f}秒\n")
                f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n识别结果:\n")
                f.write("-" * 50 + "\n")
                f.write(ocr_result['text'] if ocr_result['text'] else "未识别到任何文本")
                f.write("\n" + "-" * 50 + "\n")
            
            print(f"结果已保存: {result_filename}")
    
    return result


def main():
    """主函数"""
    print("=" * 60)
    print("超时测试")
    print("=" * 60)
    
    # 创建测试目录
    test_dir = "output/timeout_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试用例
    test_cases = [
        {
            'image': create_large_test_image(),
            'timeout': 5,
            'name': '大图像_5秒超时'
        },
        {
            'image': create_complex_test_image(),
            'timeout': 3,
            'name': '复杂图像_3秒超时'
        },
        {
            'image': create_large_test_image(),
            'timeout': 10,
            'name': '大图像_10秒超时'
        },
        {
            'image': create_complex_test_image(),
            'timeout': 5,
            'name': '复杂图像_5秒超时'
        },
    ]
    
    # 运行测试
    results = []
    for test_case in test_cases:
        result = test_with_timeout(
            test_case['image'],
            test_case['timeout'],
            test_case['name'],
            test_dir
        )
        results.append(result)
        
        # 等待一下，让之前的OCR线程有时间完成
        time.sleep(1)
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    report_path = os.path.join(test_dir, "test_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("超时测试报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("测试结果汇总:\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'测试名称':<20} {'超时(秒)':<12} {'耗时(秒)':<12} {'状态':<10} {'超时':<10}\n")
        f.write("-" * 60 + "\n")
        
        for result in results:
            status = "成功" if result['success'] else "失败"
            timed_out = "是" if result['timed_out'] else "否"
            f.write(f"{result['test_name']:<20} {result['timeout']:<12} {result['elapsed']:<12.3f} {status:<10} {timed_out:<10}\n")
        
        f.write("-" * 60 + "\n")
        
        # 统计
        success_count = sum(1 for r in results if r['success'])
        timeout_count = sum(1 for r in results if r['timed_out'])
        total_count = len(results)
        avg_time = sum(r['elapsed'] for r in results) / total_count if total_count > 0 else 0
        
        f.write(f"\n统计信息:\n")
        f.write(f"测试总数: {total_count}\n")
        f.write(f"成功数量: {success_count}\n")
        f.write(f"超时数量: {timeout_count}\n")
        f.write(f"失败数量: {total_count - success_count}\n")
        f.write(f"平均耗时: {avg_time:.3f}秒\n")
    
    print(f"测试报告已保存: {report_path}")
    
    # 显示汇总
    print(f"\n{'测试名称':<20} {'超时(秒)':<12} {'耗时(秒)':<12} {'状态':<10} {'超时':<10}")
    print("-" * 70)
    for result in results:
        status = "成功" if result['success'] else "失败"
        timed_out = "是" if result['timed_out'] else "否"
        print(f"{result['test_name']:<20} {result['timeout']:<12} {result['elapsed']:<12.3f} {status:<10} {timed_out:<10}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
