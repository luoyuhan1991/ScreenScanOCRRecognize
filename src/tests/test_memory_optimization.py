"""
内存优化测试脚本
用于测试内存优化对内存占用的影响
"""

import gc
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PIL import ImageGrab
from src.config.config import config
from src.utils.mem_monitor import get_working_set_mb


def test_memory_optimization():
    """
    测试内存优化效果
    """
    print("=" * 60)
    print("内存优化测试")
    print("=" * 60)

    pid = __import__('os').getpid()

    # 测试 1: 内存监控性能
    print("\n测试 1: 内存监控性能")
    print("-" * 60)

    # 测试多次调用的性能
    iterations = 100
    start_time = time.time()

    for i in range(iterations):
        mem_mb = get_working_set_mb(pid)

    elapsed = time.time() - start_time
    avg_time = elapsed / iterations * 1000  # 转换为毫秒

    print(f"调用次数: {iterations}")
    print(f"总耗时: {elapsed:.3f}秒")
    print(f"平均耗时: {avg_time:.3f}毫秒/次")
    print(f"当前内存: {mem_mb:.1f} MB")

    # 测试 2: 截图对象内存占用
    print("\n测试 2: 截图对象内存占用")
    print("-" * 60)

    # 获取初始内存
    gc.collect()
    time.sleep(0.5)
    initial_mem = get_working_set_mb(pid)
    print(f"初始内存: {initial_mem:.1f} MB")

    # 创建多个截图对象（不释放）
    print("\n创建 10 个截图对象（不释放）...")
    screenshots = []
    for i in range(10):
        screenshot = ImageGrab.grab()
        screenshots.append(screenshot)
        time.sleep(0.1)

    time.sleep(0.5)
    after_create_mem = get_working_set_mb(pid)
    print(f"创建后内存: {after_create_mem:.1f} MB")
    print(f"内存增长: {after_create_mem - initial_mem:.1f} MB")

    # 显式释放截图对象
    print("\n显式释放截图对象...")
    for screenshot in screenshots:
        try:
            screenshot.close()
        except Exception:
            pass
    screenshots.clear()

    gc.collect()
    time.sleep(0.5)
    after_release_mem = get_working_set_mb(pid)
    print(f"释放后内存: {after_release_mem:.1f} MB")
    print(f"内存回收: {after_create_mem - after_release_mem:.1f} MB")

    # 测试 3: 日志队列内存占用
    print("\n测试 3: 日志队列内存占用")
    print("-" * 60)

    import queue

    gc.collect()
    time.sleep(0.5)
    initial_mem = get_working_set_mb(pid)
    print(f"初始内存: {initial_mem:.1f} MB")

    # 创建大量日志消息
    print("\n创建 10000 条日志消息...")
    log_queue = queue.Queue(maxsize=10000)
    for i in range(10000):
        log_queue.put(f"这是一条测试日志消息 {i} " * 10)

    time.sleep(0.5)
    after_fill_mem = get_working_set_mb(pid)
    print(f"填充后内存: {after_fill_mem:.1f} MB")
    print(f"内存增长: {after_fill_mem - initial_mem:.1f} MB")
    print(f"队列大小: {log_queue.qsize()}")

    # 清理一半日志
    print("\n清理 5000 条旧日志...")
    for _ in range(5000):
        try:
            log_queue.get_nowait()
        except queue.Empty:
            break

    gc.collect()
    time.sleep(0.5)
    after_cleanup_mem = get_working_set_mb(pid)
    print(f"清理后内存: {after_cleanup_mem:.1f} MB")
    print(f"内存回收: {after_fill_mem - after_cleanup_mem:.1f} MB")
    print(f"队列大小: {log_queue.qsize()}")

    # 测试 4: 配置优化效果
    print("\n测试 4: 配置优化效果")
    print("-" * 60)

    print("\n当前配置:")
    print(f"  内存监控间隔: {config.get('performance.memory_monitor_interval_ms', 5000)} ms")
    print(f"  日志队列大小: {config.get('performance.max_log_queue_size', 1000)}")
    print(f"  清理阈值: {config.get('performance.log_queue_cleanup_threshold', 800)}")
    print(f"  显式清理截图: {config.get('performance.explicit_image_cleanup', True)}")

    # 计算优化效果
    print("\n优化效果估算:")

    # 内存监控优化
    old_interval = 2000  # 旧的间隔（毫秒）
    new_interval = config.get('performance.memory_monitor_interval_ms', 5000)
    monitor_reduction = (old_interval - new_interval) / old_interval * 100
    print(f"  内存监控调用频率: {monitor_reduction:+.1f}%")

    # 日志队列优化
    old_queue_size = 2000
    new_queue_size = config.get('performance.max_log_queue_size', 1000)
    queue_reduction = (old_queue_size - new_queue_size) / old_queue_size * 100
    print(f"  日志队列内存: {queue_reduction:+.1f}%")

    # 截图内存优化（假设每张截图 30MB）
    screenshot_mem_per_scan = 30  # MB
    print(f"  每次扫描节省内存: ~{screenshot_mem_per_scan:.0f} MB（显式释放截图）")

    print("\n测试完成！")


if __name__ == "__main__":
    test_memory_optimization()
