"""
ScreenScanOCRRecognize - 主程序入口
每5秒扫描一次当前屏幕，并进行OCR识别
支持ROI选择、GPU加速等优化功能
"""

import os
import sys
import time
from datetime import datetime
from src.scan_screen import scan_screen, select_roi_interactive
from src.ocr_recognize import recognize_and_print
from scripts.cleanup_old_files import start_cleanup_thread


def parse_command_line_args():
    """
    解析命令行参数
    
    Returns:
        tuple: (roi_choice, gpu_choice, lang_choice) 或 None（如果没有提供参数）
    """
    if len(sys.argv) < 2:
        return None
    
    # 格式: python main.py [roi_choice] [gpu_choice] [lang_choice]
    # 示例: python main.py 1 1 1  (全屏、自动GPU、中英文)
    # 示例: python main.py 2 1 1  (选择ROI、自动GPU、中英文)
    
    try:
        roi_choice = sys.argv[1] if len(sys.argv) > 1 else None
        gpu_choice = sys.argv[2] if len(sys.argv) > 2 else None
        lang_choice = sys.argv[3] if len(sys.argv) > 3 else None
        
        print(f"[命令行模式] ROI选项: {roi_choice}, GPU选项: {gpu_choice}, 语言选项: {lang_choice}")
        return (roi_choice, gpu_choice, lang_choice)
    except Exception as e:
        print(f"解析命令行参数失败: {e}，将使用交互式输入")
        return None


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
    
    # 配置选项
    print("\n[配置选项]")
    
    # 检查是否使用命令行参数
    cmd_args = parse_command_line_args()
    
    if cmd_args:
        # 使用命令行参数
        roi_choice, gpu_choice, lang_choice = cmd_args
    else:
        # 交互式输入
        # 询问是否使用ROI
        print("\n是否要选择ROI（感兴趣区域）？")
        print("1. 全屏扫描（默认）")
        print("2. 选择ROI区域")
        roi_choice = input("请输入选项 (1/2，直接回车默认1): ").strip()
        
    roi = None
    if roi_choice == '2':
        roi = select_roi_interactive()
        if roi is None:
            print("ROI选择取消，使用全屏扫描")
        else:
            print(f"已设置ROI区域: {roi}")
    
    # 询问是否使用GPU
    print("\n是否使用GPU加速？")
    print("1. 自动检测（默认）")
    print("2. 强制使用GPU")
    print("3. 强制使用CPU")
    
    if cmd_args and gpu_choice:
        # 使用命令行参数
        print(f"已选择选项: {gpu_choice}")
    else:
        gpu_choice = input("请输入选项 (1/2/3，直接回车默认1): ").strip()
    
    use_gpu = None  # 默认自动检测
    if gpu_choice == '2':
        use_gpu = True
        print("已设置为强制使用GPU")
    elif gpu_choice == '3':
        use_gpu = False
        print("已设置为强制使用CPU")
    else:
        print("将自动检测GPU可用性")
    
    # 询问语言设置
    print("\nOCR语言设置：")
    print("1. 中文简体 + 英文（默认）")
    print("2. 仅中文简体")
    print("3. 仅英文")
    print("4. 自定义语言（用逗号分隔，如: ch_sim,en,ja）")
    
    if cmd_args and lang_choice:
        # 使用命令行参数
        print(f"已选择选项: {lang_choice}")
    else:
        lang_choice = input("请输入选项 (1/2/3/4，直接回车默认1): ").strip()
    
    languages = None
    if lang_choice == '2':
        languages = ['ch_sim']
        print("已设置为仅识别中文简体")
    elif lang_choice == '3':
        languages = ['en']
        print("已设置为仅识别英文")
    elif lang_choice == '4':
        if cmd_args:
            # 命令行模式：从参数中读取自定义语言
            if len(sys.argv) > 4:
                custom_lang = sys.argv[4]
                languages = [lang.strip() for lang in custom_lang.split(',')]
                print(f"已设置为自定义语言: {languages}")
            else:
                print("未提供自定义语言，使用默认语言")
        else:
            # 交互式模式
            custom_lang = input("请输入语言代码（用逗号分隔）: ").strip()
            languages = [lang.strip() for lang in custom_lang.split(',')]
            print(f"已设置为自定义语言: {languages}")
    else:
        print("将使用默认语言：中文简体 + 英文")
    
    print("\n" + "=" * 60)
    print("配置完成，开始扫描...")
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
            
            # 扫描屏幕（保存到独立的扫描文件夹，支持ROI）
            screenshot, timestamp = scan_screen(
                save_dir=scan_folder, 
                timestamp=timestamp,
                roi=roi
            )
            
            # 如果扫描成功，进行OCR识别并保存结果
            if screenshot:
                recognize_and_print(
                    screenshot, 
                    languages=languages,
                    save_dir=scan_folder, 
                    timestamp=timestamp,
                    use_gpu=use_gpu,
                    roi=roi
                )
            
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




