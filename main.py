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
from src.cleanup_old_files import start_cleanup_thread


def parse_command_line_args():
    """
    解析命令行参数
    
    Returns:
        tuple: (roi_choice, gpu_choice, lang_choice, ocr_choice, match_choice, banlist_file) 或 None（如果没有提供参数）
    """
    if len(sys.argv) < 2:
        return None
    
    # 格式: python main.py [roi_choice] [gpu_choice] [lang_choice] [ocr_choice] [match_choice] [banlist_file]
    # 示例: python main.py 1 1 1 1 1  (全屏、自动GPU、中英文、paddle、启用匹配，使用默认banlist)
    # 示例: python main.py 2 1 1 2 0 custom.txt  (选择ROI、自动GPU、中英文、easy、禁用匹配，使用custom.txt)
    
    try:
        roi_choice = sys.argv[1] if len(sys.argv) > 1 else None
        gpu_choice = sys.argv[2] if len(sys.argv) > 2 else None
        lang_choice = sys.argv[3] if len(sys.argv) > 3 else None
        ocr_choice = sys.argv[4] if len(sys.argv) > 4 else None
        match_choice = sys.argv[5] if len(sys.argv) > 5 else None
        banlist_file = sys.argv[6] if len(sys.argv) > 6 else None
        
        print(f"[命令行模式] ROI选项: {roi_choice}, GPU选项: {gpu_choice}, 语言选项: {lang_choice}, OCR选项: {ocr_choice}, 匹配选项: {match_choice}, Banlist文件: {banlist_file or '默认'}")
        return (roi_choice, gpu_choice, lang_choice, ocr_choice, match_choice, banlist_file)
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
        roi_choice, gpu_choice, lang_choice, ocr_choice, match_choice, banlist_file = cmd_args
    else:
        # 交互式输入
        # 询问是否使用ROI
        print("\n是否要选择ROI（感兴趣区域）？")
        print("1. 全屏扫描（默认）")
        print("2. 选择ROI区域")
        roi_choice = input("请输入选项 (1/2，直接回车默认1): ").strip()
        
        # 询问使用哪种OCR实现
        print("\n选择OCR实现：")
        print("1. PaddleOCR（默认，推荐）")
        print("2. EasyOCR")
        ocr_choice = input("请输入选项 (1/2，直接回车默认1): ").strip()
        
        # 询问是否启用文字匹配
        print("\n是否启用文字匹配功能？")
        print("1. 启用（默认）")
        print("2. 禁用")
        match_choice = input("请输入选项 (1/2，直接回车默认1): ").strip()
        
        # 如果启用匹配，询问是否使用自定义banlist文件
        banlist_file = None
        if match_choice != '2':
            print("\n是否使用自定义关键词文件？")
            print(f"1. 使用默认文件 docs/banlist.txt（默认）")
            print("2. 使用自定义文件")
            custom_file_choice = input("请输入选项 (1/2，直接回车默认1): ").strip()
            if custom_file_choice == '2':
                banlist_file = input("请输入关键词文件路径: ").strip()
                if not banlist_file:
                    print("未输入文件路径，将使用默认文件")
                    banlist_file = None
    
    roi = None
    if roi_choice == '2':
        roi = select_roi_interactive()
        if roi is None:
            print("ROI选择取消，使用全屏扫描")
        else:
            print(f"已设置ROI区域: {roi}")
    
    # 选择OCR实现
    ocr_choice = ocr_choice if ocr_choice else '1'
    if ocr_choice == '2':
        print("\n使用 EasyOCR")
        from src.easy_ocr import recognize_and_print, init_reader
        ocr_name = "EasyOCR"
    else:
        print("\n使用 PaddleOCR（默认）")
        from src.paddle_ocr import recognize_and_print, init_reader
        ocr_name = "PaddleOCR"
    
    # 文字匹配功能选择
    match_choice = match_choice if match_choice else '1'
    enable_matching = match_choice == '1'
    if enable_matching:
        print("\n启用文字匹配功能")
    else:
        print("\n禁用文字匹配功能")
    
    # 使用默认设置：自动检测GPU、中文简体+英文
    use_gpu = None  # 自动检测GPU
    languages = None  # 默认中文简体 + 英文
    
    # 设置默认的banlist文件
    if banlist_file is None:
        banlist_file = "docs/banlist.txt"
    
    print("\n[默认设置]")
    print(f"OCR引擎: {ocr_name}")
    print("GPU加速: 自动检测")
    print("OCR语言: 中文简体 + 英文")
    if match_choice != '2':
        print(f"关键词匹配文件: {banlist_file}")
    
    print("\n" + "=" * 60)
    print("配置完成，开始扫描...")
    print("=" * 60)
    
    # 预先初始化OCR，确保GPU被正确检测和使用
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在预加载{ocr_name}模型...")
    init_reader(languages=languages, use_gpu=use_gpu, force_reinit=True)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {ocr_name}模型加载完成\n")
    
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
                roi=roi,
                padding=10
            )
            
            # 如果扫描成功，进行OCR识别并保存结果
            if screenshot:
                ocr_results = recognize_and_print(
                    screenshot, 
                    languages=languages,
                    save_dir=scan_folder, 
                    timestamp=timestamp,
                    use_gpu=use_gpu,
                    roi=roi
                )
                
                # 如果启用文字匹配，进行关键词匹配
                if enable_matching and ocr_results:
                    from src.text_matcher import match_and_display
                    match_and_display(ocr_results, txt_file=banlist_file, duration=3)
            
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




