"""
屏幕扫描模块
提供屏幕截图和保存功能
"""

import os
from datetime import datetime
from PIL import ImageGrab


def scan_screen(save_dir="output", save_file=True, timestamp=None):
    """
    扫描当前屏幕并保存截图
    
    Args:
        save_dir (str): 截图保存目录，默认为 "output"
        save_file (bool): 是否保存文件，默认为 True
        timestamp (str): 时间戳，用于生成文件名。如果为None，则自动生成
    
    Returns:
        tuple: (PIL.Image截图对象, str时间戳)，如果出错返回 (None, None)
    """
    try:
        # 捕获整个屏幕
        screenshot = ImageGrab.grab()
        
        # 获取屏幕尺寸
        width, height = screenshot.size
        
        if save_file:
            # 创建保存截图的目录
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 生成文件名（使用时间戳）
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 如果save_dir已经是时间戳文件夹，则直接使用screenshot.png
            if os.path.basename(save_dir) == timestamp:
                filename = os.path.join(save_dir, "screenshot.png")
            else:
                filename = os.path.join(save_dir, f"screenshot_{timestamp}.png")
            
            # 保存截图
            screenshot.save(filename)
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"屏幕扫描完成 - 尺寸: {width}x{height}, 已保存: {filename}")
        else:
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"屏幕扫描完成 - 尺寸: {width}x{height}")
        
        return screenshot, timestamp
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 扫描屏幕时出错: {e}")
        return None, None


if __name__ == "__main__":
    """直接运行此脚本时，执行一次扫描"""
    print("执行单次屏幕扫描...")
    screenshot, timestamp = scan_screen()
    if screenshot:
        print(f"扫描成功，时间戳: {timestamp}")

