"""
清理旧文件模块
删除超过指定时间的扫描结果文件夹
支持独立线程定时清理
"""

import os
import shutil
import threading
import time
from datetime import datetime, timedelta

from .logger import logger


def parse_timestamp_from_folder(folder_name):
    """
    从文件夹名称解析时间戳
    
    Args:
        folder_name (str): 文件夹名称，格式为 YYYYMMDD_HHMM 或 YYYYMMDD_HHMMSS
    
    Returns:
        datetime: 解析出的时间对象，如果解析失败返回 None
    """
    try:
        # 尝试解析分钟级时间戳格式: YYYYMMDD_HHMM
        return datetime.strptime(folder_name, "%Y%m%d_%H%M")
    except ValueError:
        try:
            # 尝试解析秒级时间戳格式: YYYYMMDD_HHMMSS
            return datetime.strptime(folder_name, "%Y%m%d_%H%M%S")
        except (ValueError, TypeError):
            return None


def cleanup_old_folders_by_count(output_dir="output", max_folders=10):
    """
    按数量清理旧的扫描结果文件夹，保留最新的指定数量
    
    Args:
        output_dir (str): 输出目录路径
        max_folders (int): 最大保留文件夹数量，默认为10
    
    Returns:
        int: 删除的文件夹数量
    """
    if not os.path.exists(output_dir):
        return 0
    
    deleted_count = 0
    
    try:
        # 获取所有文件夹及其时间戳
        folders = []
        for folder_name in os.listdir(output_dir):
            folder_path = os.path.join(output_dir, folder_name)
            
            # 只处理文件夹
            if not os.path.isdir(folder_path):
                continue
            
            # 解析文件夹名称中的时间戳
            folder_time = parse_timestamp_from_folder(folder_name)
            
            if folder_time is None:
                # 如果无法解析时间戳，跳过（可能是其他文件夹）
                continue
            
            folders.append((folder_path, folder_name, folder_time))
        
        # 按时间戳排序（最新的在前）
        folders.sort(key=lambda x: x[2], reverse=True)
        
        # 如果文件夹数量超过最大保留数量，删除旧的
        if len(folders) > max_folders:
            folders_to_delete = folders[max_folders:]
            
            for folder_path, folder_name, folder_time in folders_to_delete:
                try:
                    shutil.rmtree(folder_path)
                    deleted_count += 1
                    logger.info(f"已删除旧文件夹: {folder_name} (保留最新的{max_folders}个文件夹)")
                except Exception as e:
                    logger.error(f"删除文件夹失败 {folder_name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"按数量清理完成，当前保留 {len(folders) - deleted_count} 个文件夹，删除了 {deleted_count} 个旧文件夹")
    
    except Exception as e:
        logger.error(f"按数量清理旧文件时出错: {e}", exc_info=True)
    
    return deleted_count


def cleanup_old_folders(output_dir="output", max_age_hours=1):
    """
    清理超过指定时间的扫描结果文件夹
    
    Args:
        output_dir (str): 输出目录路径
        max_age_hours (int): 最大保留时间（小时），默认为1小时
    
    Returns:
        int: 删除的文件夹数量
    """
    if not os.path.exists(output_dir):
        return 0
    
    deleted_count = 0
    current_time = datetime.now()
    max_age = timedelta(hours=max_age_hours)
    
    try:
        # 遍历output目录下的所有文件夹
        for folder_name in os.listdir(output_dir):
            folder_path = os.path.join(output_dir, folder_name)
            
            # 只处理文件夹
            if not os.path.isdir(folder_path):
                continue
            
            # 解析文件夹名称中的时间戳
            folder_time = parse_timestamp_from_folder(folder_name)
            
            if folder_time is None:
                # 如果无法解析时间戳，跳过（可能是其他文件夹）
                continue
            
            # 计算时间差
            age = current_time - folder_time
            
            # 如果超过最大保留时间，删除文件夹
            if age > max_age:
                try:
                    shutil.rmtree(folder_path)
                    deleted_count += 1
                    logger.info(f"已删除过期文件夹: {folder_name} (已存在 {age})")
                except Exception as e:
                    logger.error(f"删除文件夹失败 {folder_name}: {e}")
    
    except Exception as e:
        logger.error(f"清理旧文件时出错: {e}", exc_info=True)
    
    return deleted_count


def get_next_cleanup_time(interval_minutes: int = 10):
    """
    计算下一个清理时间点
    
    Args:
        interval_minutes: 清理间隔（分钟），默认为10分钟
    
    Returns:
        datetime: 下一个清理时间点
    """
    now = datetime.now()
    # 计算当前分钟数
    current_minute = now.minute
    # 计算下一个整间隔时间点
    next_minute = ((current_minute // interval_minutes) + 1) * interval_minutes
    
    if next_minute >= 60:
        # 如果超过60分钟，则下一小时的第0分钟
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        # 否则当前小时的下一个整间隔时间点
        next_time = now.replace(minute=next_minute, second=0, microsecond=0)
    
    # 如果计算出的时间小于等于当前时间（可能因为秒数），则加间隔时间
    if next_time <= now:
        next_time = next_time + timedelta(minutes=interval_minutes)
    
    return next_time


def cleanup_scheduler(output_dir="output", max_age_hours=1, interval_minutes=10):
    """
    清理任务调度器，按指定间隔执行清理
    
    Args:
        output_dir (str): 输出目录路径
        max_age_hours (int): 最大保留时间（小时），默认为1小时
        interval_minutes (int): 清理间隔（分钟），默认为10分钟
    """
    while True:
        try:
            # 计算下一个清理时间
            next_cleanup = get_next_cleanup_time(interval_minutes)
            now = datetime.now()
            wait_seconds = (next_cleanup - now).total_seconds()
            
            if wait_seconds > 0:
                logger.info(f"清理任务已调度，下次清理时间: {next_cleanup.strftime('%Y-%m-%d %H:%M:%S')} "
                          f"(等待 {int(wait_seconds)} 秒)")
                time.sleep(wait_seconds)
            
            # 执行清理
            logger.info("开始执行自动清理...")
            deleted = cleanup_old_folders(output_dir, max_age_hours)
            if deleted > 0:
                logger.info(f"清理完成，共删除 {deleted} 个过期文件夹")
            else:
                logger.info("清理完成，无过期文件夹")
            
            # 循环继续，会重新计算下一个清理时间
            
        except Exception as e:
            logger.error(f"清理调度器出错: {e}", exc_info=True)
            # 出错后等待间隔时间再重试
            time.sleep(interval_minutes * 60)


def start_cleanup_thread(output_dir="output", max_age_hours=1, interval_minutes=10):
    """
    启动清理线程
    
    Args:
        output_dir (str): 输出目录路径
        max_age_hours (int): 最大保留时间（小时），默认为1小时
        interval_minutes (int): 清理间隔（分钟），默认为10分钟
    
    Returns:
        threading.Thread: 清理线程对象
    """
    thread = threading.Thread(
        target=cleanup_scheduler,
        args=(output_dir, max_age_hours, interval_minutes),
        daemon=True  # 设置为守护线程，主程序退出时自动结束
    )
    thread.start()
    return thread


if __name__ == "__main__":
    """直接运行此脚本时，执行一次清理"""
    from .logger import setup_logger
    setup_logger()
    logger.info("执行清理旧文件...")
    deleted = cleanup_old_folders()
    logger.info(f"清理完成，共删除 {deleted} 个过期文件夹")


