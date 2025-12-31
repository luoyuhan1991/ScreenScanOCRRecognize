"""
屏幕扫描模块
提供屏幕截图和保存功能
支持ROI（感兴趣区域）选择
"""

import os
from datetime import datetime
from PIL import ImageGrab
from .logger import logger


def select_roi_interactive():
    """
    交互式选择ROI区域
    用户可以通过鼠标拖动选择屏幕上的感兴趣区域
    
    Returns:
        tuple: ROI区域 (x1, y1, x2, y2)，如果取消选择返回None
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
        from PIL import ImageTk
        
        logger.info("\n[ROI选择模式]")
        logger.info("请按照以下步骤选择ROI区域：")
        logger.info("1. 将鼠标移动到要识别区域的左上角")
        logger.info("2. 按住鼠标左键并拖动到右下角")
        logger.info("3. 松开鼠标左键完成选择")
        logger.info("4. 按ESC键取消选择")
        logger.info("\n提示：选择完成后，该区域将用于后续的OCR识别")
        
        # 捕获整个屏幕
        screenshot = ImageGrab.grab()
        width, height = screenshot.size
        
        # 创建窗口
        root = tk.Tk()
        root.title("选择ROI区域")
        root.geometry(f"{width}x{height}")
        root.attributes('-fullscreen', True)
        root.attributes('-topmost', True)  # 确保窗口在最上层
        root.attributes('-alpha', 0.5)  # 半透明，便于看到下方内容
        
        # 显示截图
        photo = ImageTk.PhotoImage(screenshot)
        canvas = tk.Canvas(root, width=width, height=height, cursor='crosshair')
        canvas.pack(fill='both', expand=True)
        canvas.create_image(0, 0, image=photo, anchor='nw')
        
        # ROI选择变量
        roi_data = {'start': None, 'end': None, 'rect': None, 'completed': False}
        
        def on_mouse_down(event):
            logger.debug(f"鼠标按下: ({event.x}, {event.y})")
            roi_data['start'] = (event.x, event.y)
            roi_data['end'] = None
            roi_data['completed'] = False
        
        def on_mouse_drag(event):
            if roi_data['start']:
                roi_data['end'] = (event.x, event.y)
                # 绘制矩形
                if roi_data['rect']:
                    canvas.delete(roi_data['rect'])
                x1, y1 = roi_data['start']
                x2, y2 = event.x, event.y
                roi_data['rect'] = canvas.create_rectangle(
                    x1, y1, x2, y2, 
                    outline='red', width=3, fill='yellow', stipple='gray25'
                )
        
        def on_mouse_up(event):
            if roi_data['start']:
                logger.debug(f"鼠标释放: ({event.x}, {event.y})")
                roi_data['end'] = (event.x, event.y)
                roi_data['completed'] = True
                logger.debug("ROI选择完成，关闭窗口...")
                root.destroy()
        
        def on_key_press(event):
            if event.keysym == 'Escape':
                logger.debug("按下ESC，取消选择")
                roi_data['completed'] = False
                root.destroy()
        
        # 绑定事件
        canvas.bind('<Button-1>', on_mouse_down)
        canvas.bind('<B1-Motion>', on_mouse_drag)
        canvas.bind('<ButtonRelease-1>', on_mouse_up)
        root.bind('<Key>', on_key_press)
        
        # 确保canvas获得焦点
        canvas.focus_set()
        
        logger.debug("ROI选择窗口已创建，等待用户操作...")
        
        # 运行窗口
        root.mainloop()
        
        # 返回ROI
        if roi_data['completed'] and roi_data['start'] and roi_data['end']:
            x1, y1 = roi_data['start']
            x2, y2 = roi_data['end']
            # 确保坐标顺序正确
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            logger.info(f"ROI区域已选择: ({x1}, {y1}, {x2}, {y2})")
            return (x1, y1, x2, y2)
        else:
            logger.info("ROI选择已取消")
            return None
            
    except ImportError:
        logger.warning("交互式ROI选择需要tkinter库，请安装或使用固定ROI")
        return None
    except Exception as e:
        logger.error(f"ROI选择失败: {e}", exc_info=True)
        return None


def scan_screen(save_dir="output", save_file=True, timestamp=None, roi=None, padding=10):
    """
    扫描当前屏幕并保存截图
    
    Args:
        save_dir (str): 截图保存目录，默认为 "output"
        save_file (bool): 是否保存文件，默认为 True
        timestamp (str): 时间戳，用于生成文件名。如果为None，则自动生成
        roi (tuple): 感兴趣区域 (x1, y1, x2, y2)，默认为None（全屏）
        padding (int): 边距（像素），默认为10。用于扩展ROI区域，避免文字太靠近边框
    
    Returns:
        tuple: (PIL.Image截图对象, str时间戳)，如果出错返回 (None, None)
    """
    try:
        # 获取屏幕尺寸
        screen = ImageGrab.grab()
        screen_width, screen_height = screen.size
        
        # 捕获屏幕（支持ROI）
        if roi is not None:
            x1, y1, x2, y2 = roi
            
            # 添加边距，避免文字太靠近边框
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(screen_width, x2 + padding)
            y2 = min(screen_height, y2 + padding)
            
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            logger.info(f"使用ROI区域: ({x1}, {y1}, {x2}, {y2}), 边距: {padding}px")
        else:
            screenshot = ImageGrab.grab()
        
        # 获取截图尺寸
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
            
            roi_info = f" ROI: {roi}" if roi else ""
            logger.info(f"屏幕扫描完成 - 尺寸: {width}x{height}{roi_info}, 已保存: {filename}")
        else:
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            roi_info = f" ROI: {roi}" if roi else ""
            logger.info(f"屏幕扫描完成 - 尺寸: {width}x{height}{roi_info}")
        
        return screenshot, timestamp
        
    except Exception as e:
        logger.error(f"扫描屏幕时出错: {e}", exc_info=True)
        return None, None


if __name__ == "__main__":
    """直接运行此脚本时，执行一次扫描"""
    print("执行单次屏幕扫描...")
    
    # 询问是否使用ROI
    print("\n是否要选择ROI区域？")
    print("1. 全屏扫描")
    print("2. 选择ROI区域")
    choice = input("请输入选项 (1/2，默认1): ").strip()
    
    roi = None
    if choice == '2':
        roi = select_roi_interactive()
        if roi is None:
            print("ROI选择取消，使用全屏扫描")
    
    screenshot, timestamp = scan_screen(roi=roi)
    if screenshot:
        print(f"扫描成功，时间戳: {timestamp}")

