"""
OCR 性能测试脚本
用于测试图像取反优化对 OCR 识别速度的影响
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PIL import ImageGrab
from src.config.config import config
from src.core.ocr.paddle_ocr import recognize_and_print


def test_ocr_performance(test_rounds=5):
    """
    测试 OCR 性能

    Args:
        test_rounds: 测试轮数
    """
    print("=" * 60)
    print("OCR 性能测试")
    print("=" * 60)

    # 捕获屏幕截图作为测试图像
    print("\n正在捕获测试图像...")
    screenshot = ImageGrab.grab()

    # 测试配置
    test_configs = [
        {
            'name': '关闭图像取反（优化后）',
            'enable_invert': False,
            'auto_detect': False
        },
        {
            'name': '启用图像取反（原始）',
            'enable_invert': True,
            'auto_detect': False
        },
        {
            'name': '自动检测取反',
            'enable_invert': False,
            'auto_detect': True
        }
    ]

    results = {}

    for test_config in test_configs:
        print(f"\n{'='*60}")
        print(f"测试配置: {test_config['name']}")
        print(f"{'='*60}")

        # 设置配置
        config.set('ocr.enable_image_invert', test_config['enable_invert'])
        config.set('ocr.auto_detect_invert', test_config['auto_detect'])
        config.set('ocr.save_processed_image', False)  # 不保存处理后的图像

        times = []

        for i in range(test_rounds):
            print(f"\n第 {i+1}/{test_rounds} 轮测试...")

            start_time = time.time()

            # 执行 OCR 识别
            ocr_results = recognize_and_print(
                screenshot,
                save_dir="output/test",
                save_result=False  # 不保存结果文件
            )

            elapsed_time = time.time() - start_time
            times.append(elapsed_time)

            print(f"识别耗时: {elapsed_time:.3f}秒")
            print(f"识别结果数: {len(ocr_results) if ocr_results else 0}")

        # 计算统计数据
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        results[test_config['name']] = {
            'avg': avg_time,
            'min': min_time,
            'max': max_time,
            'times': times
        }

        print(f"\n统计结果:")
        print(f"  平均耗时: {avg_time:.3f}秒")
        print(f"  最快耗时: {min_time:.3f}秒")
        print(f"  最慢耗时: {max_time:.3f}秒")

    # 输出对比结果
    print(f"\n{'='*60}")
    print("性能对比总结")
    print(f"{'='*60}")

    baseline_name = '启用图像取反（原始）'
    baseline_time = results[baseline_name]['avg']

    print(f"\n基准配置: {baseline_name}")
    print(f"基准平均耗时: {baseline_time:.3f}秒\n")

    for name, data in results.items():
        if name == baseline_name:
            continue

        avg_time = data['avg']
        improvement = (baseline_time - avg_time) / baseline_time * 100

        print(f"{name}:")
        print(f"  平均耗时: {avg_time:.3f}秒")
        print(f"  性能提升: {improvement:+.1f}%")
        print(f"  时间节省: {baseline_time - avg_time:.3f}秒\n")

    # 恢复原始配置
    config.set('ocr.enable_image_invert', False)
    config.set('ocr.auto_detect_invert', False)
    config.set('ocr.save_processed_image', True)

    print("测试完成！")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='OCR 性能测试')
    parser.add_argument('-r', '--rounds', type=int, default=5, help='测试轮数（默认: 5）')

    args = parser.parse_args()

    test_ocr_performance(test_rounds=args.rounds)
