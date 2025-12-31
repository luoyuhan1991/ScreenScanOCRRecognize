"""
GUI日志处理器模块
将日志输出重定向到GUI文本框
"""

import logging
import queue
from typing import Optional


class GUILoggerHandler(logging.Handler):
    """将日志输出到GUI文本框的处理器"""
    
    def __init__(self, log_queue: queue.Queue):
        """
        初始化日志处理器
        
        Args:
            log_queue: 日志队列，用于在主线程中处理日志
        """
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                           datefmt='%Y-%m-%d %H:%M:%S'))
    
    def emit(self, record):
        """
        发送日志记录到队列
        
        Args:
            record: 日志记录
        """
        try:
            # 格式化日志消息
            message = self.format(record)
            level = record.levelname
            
            # 将日志放入队列（非阻塞）
            try:
                self.log_queue.put_nowait((message, level))
            except queue.Full:
                # 队列已满，忽略这条日志
                pass
        except Exception:
            # 忽略处理日志时的错误，避免递归
            pass
    
    def get_color(self, level: str) -> str:
        """
        根据日志级别获取颜色标签
        
        Args:
            level: 日志级别
            
        Returns:
            颜色标签名称
        """
        level_map = {
            'DEBUG': 'DEBUG',
            'INFO': 'INFO',
            'WARNING': 'WARNING',
            'ERROR': 'ERROR',
            'CRITICAL': 'ERROR'
        }
        return level_map.get(level, 'INFO')

