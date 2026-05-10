"""临时截屏脚本：启动 app.py，等渲染，按窗口标题找到并置顶，截图，关掉 app。"""
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time

sys.path.insert(0, '.')
import mss
from mss.tools import to_png

PROJ = os.path.dirname(os.path.abspath(__file__))
PYW = os.path.join(PROJ, '.venv', 'Scripts', 'pythonw.exe')

WINDOW_TITLE = '屏幕扫描 OCR 识别系统'

user32 = ctypes.windll.user32
SW_RESTORE = 9


def find_window(title):
    """按精确标题找窗口；返回 hwnd 或 0。"""
    return user32.FindWindowW(None, title)


def get_window_rect(hwnd):
    """获取窗口客户区屏幕坐标 (x, y, w, h)；包含标题栏边框。"""
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def bring_to_front(hwnd):
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)


proc = subprocess.Popen([PYW, os.path.join(PROJ, 'app.py')], cwd=PROJ)
try:
    # 轮询找窗口（首次 PySide6 启动会做字体缓存等，可能慢）
    hwnd = 0
    deadline = time.time() + 15
    while time.time() < deadline:
        hwnd = find_window(WINDOW_TITLE)
        if hwnd:
            break
        time.sleep(0.3)
    if not hwnd:
        print('ERROR: window not found within 15s')
        sys.exit(1)
    bring_to_front(hwnd)
    time.sleep(0.5)  # 等置顶动画
    x, y, w, h = get_window_rect(hwnd)
    print(f'window @ ({x},{y}) {w}x{h}')

    with mss.mss() as sct:
        bbox = {'left': x, 'top': y, 'width': w, 'height': h}
        img = sct.grab(bbox)
        to_png(img.rgb, img.size, output='_screenshot.png')
    print('saved _screenshot.png')
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
