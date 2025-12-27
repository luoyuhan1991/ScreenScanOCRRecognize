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


def parse_timestamp_from_folder(folder_name):
    """
    从文件夹名称解析时间戳
    
    Args:
        folder_name (str): 文件夹名称，格式为 YYYYMMDD_HHMMSS
    
    Returns:
        datetime: 解析出的时间对象，如果解析失败返回 None
    """
    try:
        # 文件夹名称格式: YYYYMMDD_HHMMSS
        return datetime.strptime(folder_name, "%Y%m%d_%H%M%S")
    except (ValueError, TypeError):
        return None


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
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                          f"已删除过期文件夹: {folder_name} (已存在 {age})")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                          f"删除文件夹失败 {folder_name}: {e}")
    
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理旧文件时出错: {e}")
    
    return deleted_count


def get_next_cleanup_time():
    """
    计算下一个整10分钟的时间点
    
    Returns:
        datetime: 下一个整10分钟的时间点
    """
    now = datetime.now()
    # 计算当前分钟数
    current_minute = now.minute
    # 计算下一个整10分钟（0, 10, 20, 30, 40, 50）
    next_minute = ((current_minute // 10) + 1) * 10
    
    if next_minute >= 60:
        # 如果超过60分钟，则下一小时的第0分钟
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        # 否则当前小时的下一个整10分钟
        next_time = now.replace(minute=next_minute, second=0, microsecond=0)
    
    # 如果计算出的时间小于等于当前时间（可能因为秒数），则加10分钟
    if next_time <= now:
        next_time = next_time + timedelta(minutes=10)
    
    return next_time


def cleanup_scheduler(output_dir="output", max_age_hours=1, interval_minutes=10):
    """
    清理任务调度器，每整10分钟执行一次清理
    
    Args:
        output_dir (str): 输出目录路径
        max_age_hours (int): 最大保留时间（小时），默认为1小时
        interval_minutes (int): 清理间隔（分钟），默认为10分钟
    """
    while True:
        try:
            # 计算下一个清理时间
            next_cleanup = get_next_cleanup_time()
            now = datetime.now()
            wait_seconds = (next_cleanup - now).total_seconds()
            
            if wait_seconds > 0:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"清理任务已调度，下次清理时间: {next_cleanup.strftime('%Y-%m-%d %H:%M:%S')} "
                      f"(等待 {int(wait_seconds)} 秒)")
                time.sleep(wait_seconds)
            
            # 执行清理
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行自动清理...")
            deleted = cleanup_old_folders(output_dir, max_age_hours)
            if deleted > 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理完成，共删除 {deleted} 个过期文件夹")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理完成，无过期文件夹")
            
            # 循环继续，会重新计算下一个整10分钟时间
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理调度器出错: {e}")
            # 出错后等待10分钟再重试
            time.sleep(600)


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
    print("执行清理旧文件...")
    deleted = cleanup_old_folders()
    print(f"清理完成，共删除 {deleted} 个过期文件夹")

