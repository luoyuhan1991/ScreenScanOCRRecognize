"""
ScreenScanOCRRecognize - 主程序入口
每N秒扫描一次当前屏幕，并进行OCR识别
支持ROI选择、GPU加速等优化功能
"""

import os
import sys
import time
from datetime import datetime

from src.cleanup_old_files import start_cleanup_thread, cleanup_old_folders_by_count
from src.config import config
from src.logger import logger
from src.scan_screen import scan_screen, select_roi_interactive
from src.ocr_adapter import OCRConfig, OCRFactory


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
        
        logger.info(f"[命令行模式] ROI选项: {roi_choice}, GPU选项: {gpu_choice}, 语言选项: {lang_choice}, "
                   f"OCR选项: {ocr_choice}, 匹配选项: {match_choice}, Banlist文件: {banlist_file or '默认'}")
        return (roi_choice, gpu_choice, lang_choice, ocr_choice, match_choice, banlist_file)
    except Exception as e:
        logger.warning(f"解析命令行参数失败: {e}，将使用交互式输入")
        return None


def main():
    """主函数 - 按配置的间隔扫描屏幕并进行OCR识别"""
    # 从配置读取参数
    output_dir = config.get('files.output_dir', 'output')
    scan_interval = config.get('scan.interval_seconds', 5)
    roi_padding = config.get('scan.roi_padding', 10)
    folder_mode = config.get('files.folder_mode', 'minute')  # 文件夹组织模式
    max_folders = config.get('files.max_folders', 10)  # 最大保留文件夹数量
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    logger.info("=" * 60)
    logger.info("ScreenScanOCRRecognize - 屏幕扫描OCR识别程序")
    logger.info(f"每{scan_interval}秒自动扫描一次屏幕并进行OCR识别")
    logger.info(f"文件夹组织模式: {'按分钟' if folder_mode == 'minute' else '按次扫描'}")
    logger.info(f"截图和OCR结果将保存到: {os.path.abspath(output_dir)}")
    if folder_mode == 'minute':
        logger.info(f"最多保留 {max_folders} 个分钟文件夹")
    
    cleanup_enabled = config.get('cleanup.enabled', True)
    if cleanup_enabled:
        cleanup_interval = config.get('cleanup.interval_minutes', 10)
        logger.info(f"自动清理超过{config.get('cleanup.max_age_hours', 1)}小时的旧文件（每{cleanup_interval}分钟执行一次）")
    logger.info("按 Ctrl+C 停止程序")
    logger.info("=" * 60)
    
    # 检查是否使用命令行参数
    cmd_args = parse_command_line_args()
    
    if cmd_args:
        roi_choice, gpu_choice, lang_choice, ocr_choice, match_choice, banlist_file = cmd_args
    else:
        # 使用默认参数（从配置文件读取）
        roi_choice = '2'
        gpu_choice = None
        lang_choice = None
        ocr_choice = '1' if config.get('ocr.default_engine', 'paddle') == 'paddle' else '2'
        match_choice = '1' if config.get('matching.enabled', True) else '0'
        banlist_file = None  # 稍后统一从配置读取
        logger.info("\n[使用默认配置]")
    
    # 统一设置banlist文件（命令行参数优先，否则使用配置）
    if banlist_file is None:
        banlist_file = config.get('files.banlist_file', 'docs/banlist.txt')
    
    roi = None
    if roi_choice == '2':
        roi = select_roi_interactive()
        if roi is None:
            logger.info("ROI选择取消，使用全屏扫描")
        else:
            logger.info(f"已设置ROI区域: {roi}")
    
    # 文字匹配功能选择
    match_choice = match_choice if match_choice else '1'
    enable_matching = match_choice == '1'
    if enable_matching:
        logger.info("\n启用文字匹配功能")
    else:
        logger.info("\n禁用文字匹配功能")
    
    # 语言配置 - 根据命令行语言选项设置语言
    if lang_choice == '1':
        languages_config = ['ch', 'en']  # 中英文
        logger.info(f"语言选项: 中英文")
    elif lang_choice == '2':
        languages_config = ['ch']  # 仅中文
        logger.info(f"语言选项: 中文")
    elif lang_choice == '3':
        languages_config = ['en']  # 仅英文
        logger.info(f"语言选项: 英文")
    else:
        # 使用配置文件的语言设置
        languages_config = config.get('ocr.languages', ['ch', 'en'])
        logger.info(f"语言选项: 使用配置文件 {languages_config}")
    
    # GPU配置 - 处理命令行GPU选项（如果提供）
    use_gpu_param = None
    if gpu_choice == '0':
        use_gpu_param = False
        logger.info("GPU选项: 使用CPU")
    elif gpu_choice == '1':
        use_gpu_param = True
        logger.info("GPU选项: 使用GPU")
    elif gpu_choice == '2':
        use_gpu_param = None  # 自动检测
        logger.info("GPU选项: 自动检测")
    # 如果gpu_choice为None，则使用OCRConfig内部的默认逻辑（从配置文件读取）
    
    # 创建统一的OCR配置对象
    ocr_choice = ocr_choice if ocr_choice else '1'
    engine_type = 'paddle' if ocr_choice == '1' else 'easy'
    ocr_config = OCRConfig(
        languages=languages_config,
        use_gpu=use_gpu_param,
        engine=engine_type
    )
    
    # 创建OCR适配器（使用工厂模式）
    try:
        ocr_adapter = OCRFactory.create(ocr_choice)
        ocr_name = ocr_adapter.engine_name
        logger.info(f"\n使用 {ocr_name}")
    except ValueError as e:
        logger.error(f"创建OCR适配器失败: {e}")
        logger.info("使用默认的 PaddleOCR")
        ocr_adapter = OCRFactory.create('1')
        ocr_name = ocr_adapter.engine_name
    
    # 显示OCR配置信息
    logger.info(f"OCR语言配置: {ocr_config.languages}")
    logger.info(f"GPU设置: {'启用' if ocr_config.use_gpu else '禁用'}")
    
    logger.info("\n[配置信息]")
    logger.info(f"OCR引擎: {ocr_name}")
    logger.info(f"扫描间隔: {scan_interval}秒")
    if match_choice != '0':
        logger.info(f"关键词匹配文件: {banlist_file}")
    
    logger.info("\n" + "=" * 60)
    logger.info("配置完成，开始扫描...")
    logger.info("=" * 60)
    
    # 预先初始化OCR（使用适配器统一接口，不使用force_reinit，使用缓存）
    logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在初始化{ocr_name}模型...")
    ocr_adapter.init_reader(ocr_config, force_reinit=False)
    logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {ocr_name}模型初始化完成\n")
    
    # 启动清理线程（如果启用）
    cleanup_thread = None
    if cleanup_enabled:
        max_age_hours = config.get('cleanup.max_age_hours', 1)
        cleanup_interval = config.get('cleanup.interval_minutes', 10)
        cleanup_thread = start_cleanup_thread(output_dir, max_age_hours=max_age_hours, 
                                            interval_minutes=cleanup_interval)
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理线程已启动")
    
    try:
        scan_count = 0
        current_minute_folder = None
        current_minute = None
        
        while True:
            scan_count += 1
            scan_start_time = time.time()
            logger.info(f"\n开始第 {scan_count} 次扫描...")
            
            # 获取当前时间
            now = datetime.now()
            
            # 根据文件夹组织模式决定保存目录
            if folder_mode == 'minute':
                # 按分钟组织文件夹
                minute_timestamp = now.strftime("%Y%m%d_%H%M")
                
                # 检查是否需要创建新的分钟文件夹
                if current_minute != minute_timestamp:
                    current_minute = minute_timestamp
                    current_minute_folder = os.path.join(output_dir, current_minute)
                    
                    # 创建新的分钟文件夹
                    if not os.path.exists(current_minute_folder):
                        os.makedirs(current_minute_folder)
                        logger.info(f"创建新的分钟文件夹: {current_minute}")
                        
                        # 清理旧的分钟文件夹，保留最多max_folders个
                        cleanup_old_folders_by_count(output_dir, max_folders=max_folders)
                
                # 使用分钟文件夹作为保存目录
                save_dir = current_minute_folder
            else:
                # 按次扫描组织文件夹（原有模式）
                second_timestamp = now.strftime("%Y%m%d_%H%M%S")
                save_dir = os.path.join(output_dir, second_timestamp)
                os.makedirs(save_dir, exist_ok=True)
            
            # 生成秒级时间戳（用于匹配截图和OCR结果文件名）
            second_timestamp = now.strftime("%Y%m%d_%H%M%S")
            
            try:
                # 扫描屏幕（保存到分钟文件夹，支持ROI）
                screenshot, timestamp = scan_screen(
                    save_dir=save_dir, 
                    timestamp=second_timestamp,
                    roi=roi,
                    padding=roi_padding
                )
                
                # 如果扫描成功，进行OCR识别并保存结果
                if screenshot:
                    # 在按分钟模式下，删除该文件夹中所有旧的截图
                    if folder_mode == 'minute':
                        # 查找并删除所有旧的截图文件
                        import glob
                        old_screenshots = glob.glob(os.path.join(save_dir, "screenshot_*.png"))
                        for old_screenshot in old_screenshots:
                            if old_screenshot != os.path.join(save_dir, f"screenshot_{second_timestamp}.png"):
                                try:
                                    os.remove(old_screenshot)
                                    logger.debug(f"删除旧截图: {os.path.basename(old_screenshot)}")
                                except Exception as e:
                                    logger.warning(f"删除旧截图失败: {e}")
                    
                    # 使用适配器的统一接口进行OCR识别
                    ocr_results = ocr_adapter.recognize_and_print(
                        screenshot,
                        config=ocr_config,
                        save_dir=save_dir,
                        timestamp=second_timestamp,
                        roi=None  # 截图已在scan_screen中裁剪过，不需要再次裁剪
                    )
                    
                    # 如果启用文字匹配，进行关键词匹配
                    if enable_matching and ocr_results:
                        from src.text_matcher import match_and_display
                        display_duration = config.get('matching.display_duration', 3)
                        display_position = config.get('matching.position', 'center')
                        
                        # 统一OCR结果格式：text_matcher期望列表格式，每个元素包含'text'键
                        # PaddleOCR返回 List[Dict]，EasyOCR返回 str
                        if isinstance(ocr_results, str):
                            # EasyOCR返回字符串，转换为列表格式
                            # 按行分割，每行作为一个文本项
                            text_lines = [line.strip() for line in ocr_results.split('\n') if line.strip()]
                            ocr_results_for_match = [{'text': line} for line in text_lines]
                        elif isinstance(ocr_results, list):
                            # PaddleOCR返回列表格式，直接使用
                            ocr_results_for_match = ocr_results
                        else:
                            # 其他格式，转换为列表
                            ocr_results_for_match = [{'text': str(ocr_results)}]
                        
                        match_and_display(ocr_results_for_match, txt_file=banlist_file, 
                                        duration=display_duration, position=display_position)
                
            except Exception as e:
                logger.error(f"扫描或OCR处理出错: {e}", exc_info=True)
            
            # 计算实际处理时间，动态调整等待时间
            scan_duration = time.time() - scan_start_time
            wait_time = max(0, scan_interval - scan_duration)
            
            if wait_time > 0:
                logger.info(f"\n扫描完成，耗时 {scan_duration:.2f}秒，等待 {wait_time:.2f}秒后进行下一次扫描...")
                time.sleep(wait_time)
            else:
                logger.warning(f"\n扫描耗时 {scan_duration:.2f}秒，超过间隔时间 {scan_interval}秒，立即开始下一次扫描")
            
    except KeyboardInterrupt:
        logger.info(f"\n\n程序已停止，共完成 {scan_count} 次扫描")
        logger.info(f"所有文件已保存到: {os.path.abspath(output_dir)}")
    except Exception as e:
        logger.error(f"\n程序运行出错: {e}", exc_info=True)


if __name__ == "__main__":
    main()








