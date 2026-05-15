import os
import sys
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from config.config import config
from pipeline.pipeline import ScanPipeline
from utils.logger import logger, configure_from_config


def main():
    config.load()
    configure_from_config(config)

    # 创建管道
    pipeline = ScanPipeline()

    # ROI 设置：尊重 enable_roi 开关，与 GUI 行为对齐
    if config.get('scan.enable_roi'):
        roi = config.get('scan.roi_rect')
        if roi:
            pipeline.set_roi(tuple(roi))
        else:
            print("scan.enable_roi=True 但 roi_rect 未设置，按全屏扫描")

    print("正在初始化 OCR 模型...")
    pipeline.init()
    print("初始化完成，开始扫描...")

    interval = config.get('scan.interval_seconds')

    try:
        while True:
            start = time.time()
            result = pipeline.scan_once()

            status = (
                "跳过(无变化)" if result.skipped
                else f"{len(result.ocr_results)}行"
            )
            print(
                f"OCR: {status}, "
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
