import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from src.config.config import config
from src.pipeline.pipeline import ScanPipeline
from src.utils.logger import logger, configure_from_config


def main():
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    config.load(config_path)
    configure_from_config(config)

    # 创建管道
    pipeline = ScanPipeline()

    # ROI 设置
    roi_str = config.get('scan.roi')
    if roi_str:
        pipeline.set_roi(tuple(roi_str))

    print("正在初始化 OCR 模型...")
    pipeline.init()
    print("初始化完成，开始扫描...")

    interval = config.get('scan.interval_seconds')
    scan_count = 0

    try:
        while True:
            start = time.time()
            result = pipeline.scan_once()
            scan_count += 1

            status = (
                "跳过(无变化)" if result.skipped
                else f"{len(result.ocr_results)}行"
            )
            print(
                f"[#{scan_count}] OCR: {status}, "
                f"匹配: {len(result.matches)}, "
                f"耗时: {result.duration:.3f}s"
            )

            if result.matches:
                for m in result.matches:
                    print(f"  >>> 匹配: {m['keyword']} | {m['hint']}")

            # 等待下次扫描
            elapsed = time.time() - start
            wait = max(0, interval - elapsed)
            time.sleep(wait)
    except KeyboardInterrupt:
        print("\n扫描已停止")
    finally:
        pipeline.release()


if __name__ == '__main__':
    main()
