"""
ScreenScanOCRRecognize - 主程序入口
每5秒扫描一次当前屏幕，并进行OCR识别
"""

import os
import time
from datetime import datetime
from scan_screen import scan_screen
from ocr_recognize import recognize_and_print
from cleanup_old_files import start_cleanup_thread


def main():
    """主函数 - 每5秒扫描一次屏幕并进行OCR识别"""
    # 创建输出目录
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("=" * 60)
    print("ScreenScanOCRRecognize - 屏幕扫描OCR识别程序")
    print("每5秒自动扫描一次屏幕并进行OCR识别")
    print(f"截图和OCR结果将保存到: {os.path.abspath(output_dir)}")
    print("自动清理超过1小时的旧文件（每整10分钟执行一次）")
    print("按 Ctrl+C 停止程序")
    print("=" * 60)
    
    # 启动独立的清理线程
    cleanup_thread = start_cleanup_thread(output_dir, max_age_hours=1, interval_minutes=10)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理线程已启动")
    
    try:
        scan_count = 0
        while True:
            scan_count += 1
            print(f"\n开始第 {scan_count} 次扫描...")
            
            # 生成时间戳（用于匹配截图和OCR结果文件名）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 为每次扫描创建独立的文件夹
            scan_folder = os.path.join(output_dir, timestamp)
            
            # 扫描屏幕（保存到独立的扫描文件夹）
            screenshot, timestamp = scan_screen(save_dir=scan_folder, timestamp=timestamp)
            
            # 如果扫描成功，进行OCR识别并保存结果
            if screenshot:
                recognize_and_print(screenshot, save_dir=scan_folder, timestamp=timestamp)
            
            # 等待5秒
            print("\n等待5秒后进行下一次扫描...")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n\n程序已停止，共完成 {scan_count} 次扫描")
        print(f"所有文件已保存到: {os.path.abspath(output_dir)}")
    except Exception as e:
        print(f"\n程序运行出错: {e}")


if __name__ == "__main__":
    main()

