"""
ScreenScanOCRRecognize - 主程序入口
每N秒扫描一次当前屏幕，并进行OCR识别
支持ROI选择、GPU加速等优化功能
"""

import os
import sys
import time

from src.config.config import config
from src.core.scan_service import ScanService
from src.utils.logger import logger
from src.utils.scan_screen import select_roi_interactive
from src.utils.text_matcher import display_matches


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
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建输出目录: {output_dir}")
    
    logger.info("=" * 60)
    logger.info("ScreenScanOCRRecognize - 屏幕扫描OCR识别程序")
    logger.info(f"每{scan_interval}秒自动扫描一次屏幕并进行OCR识别")
    logger.info(f"文件夹组织模式: {'按分钟' if folder_mode == 'minute' else '按次扫描'}")
    logger.info(f"截图和OCR结果将保存到: {os.path.abspath(output_dir)}")
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
    
    # 创建统一的扫描服务
    scan_service = ScanService()
    
    # 初始化OCR
    try:
        scan_service.init_ocr(
            engine_choice=ocr_choice,
            languages=languages_config,
            use_gpu=use_gpu_param
        )
        logger.info(f"\n使用 {scan_service.ocr_adapter.engine_name}")
    except ValueError as e:
        logger.error(f"创建OCR适配器失败: {e}")
        logger.info("使用默认的 PaddleOCR")
        scan_service.init_ocr(engine_choice='1')
    
    # 显示OCR配置信息
    logger.info(f"OCR语言配置: {scan_service.ocr_config.languages}")
    logger.info(f"GPU设置: {'启用' if scan_service.ocr_config.use_gpu else '禁用'}")
    
    logger.info("\n[配置信息]")
    logger.info(f"OCR引擎: {scan_service.ocr_adapter.engine_name}")
    logger.info(f"扫描间隔: {scan_interval}秒")
    if match_choice != '0':
        logger.info(f"关键词匹配文件: {banlist_file}")
    
    logger.info("\n" + "=" * 60)
    logger.info("配置完成，开始扫描...")
    logger.info("=" * 60)
    
    # 设置ROI
    scan_service.set_roi(roi)
    
    try:
        scan_count = 0
        
        while True:
            scan_count += 1
            logger.info(f"\n开始第 {scan_count} 次扫描...")
            
            # 执行扫描
            result = scan_service.scan_once()
            
            if result['success']:
                logger.info(f"扫描完成，耗时 {result['duration']:.2f}秒")
                if 'matches' in result and result['matches']:
                    logger.info(f"匹配到关键词: {result['matches']}")
                    # 显示匹配结果
                    display_matches(
                        result['matches'],
                        duration=scan_service.display_duration,
                        position=scan_service.display_position,
                        font_size=scan_service.display_font_size
                    )
            elif 'error' in result:
                logger.error(f"扫描出错: {result['error']}")
            
            # 计算等待时间
            scan_duration = result['duration']
            wait_time = max(0, scan_interval - scan_duration)
            
            if wait_time > 0:
                logger.info(f"等待 {wait_time:.2f}秒后进行下一次扫描...")
                time.sleep(wait_time)
            else:
                logger.warning(f"扫描耗时 {scan_duration:.2f}秒，超过间隔时间 {scan_interval}秒，立即开始下一次扫描")
            
    except KeyboardInterrupt:
        logger.info(f"\n\n程序已停止，共完成 {scan_count} 次扫描")
        logger.info(f"所有文件已保存到: {os.path.abspath(output_dir)}")
        # 释放资源
        scan_service.release_resources()
    except Exception as e:
        logger.error(f"\n程序运行出错: {e}", exc_info=True)
        scan_service.release_resources()


if __name__ == "__main__":
    main()

