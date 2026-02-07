# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller配置文件
使用方法: pyinstaller src/buildexe/build_exe.spec
注意：需要在项目根目录执行此命令
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 获取项目根目录（spec文件在src/buildexe文件夹中，需要获取src的父目录）
spec_file = os.path.abspath(__file__ if '__file__' in globals() else sys.argv[0])
build_dir = os.path.dirname(spec_file)
src_dir = os.path.dirname(build_dir)
project_root = os.path.dirname(src_dir)

# 收集数据文件（使用绝对路径）
config_yaml_src = os.path.join(project_root, 'config', 'config.yaml')
config_yaml_dst = 'config'
banlist_txt_src = os.path.join(project_root, 'docs', 'banlist.txt')
banlist_txt_dst = 'docs'

datas = []
if os.path.exists(config_yaml_src):
    datas.append((config_yaml_src, config_yaml_dst))
if os.path.exists(banlist_txt_src):
    datas.append((banlist_txt_src, banlist_txt_dst))

# 收集隐藏导入
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.scrolledtext',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageGrab',
    'cv2',
    'numpy',
    'yaml',
    'paddleocr',
    'paddleocr.paddleocr',  # PaddleOCR主模块
    'paddlepaddle',  # PaddlePaddle核心
    'paddle',  # Paddle别名
    'paddle.fluid',  # PaddlePaddle流体API
    'paddle.inference',  # PaddlePaddle推理API
    'easyocr',
    'torch',
    'torchvision',
    'src',
    'src.config',
    'src.config.config',
    'src.config.config_editor',
    'src.config.gui_state',
    'src.gui',
    'src.gui.gui_logger',
    'src.ocr',
    'src.ocr.ocr_adapter',
    'src.ocr.paddle_ocr',
    'src.ocr.easy_ocr',
    'src.utils',
    'src.utils.logger',
    'src.utils.scan_screen',
    'src.utils.text_matcher',
    'src.utils.cleanup_old_files',
]

# 收集PaddleOCR和EasyOCR的数据文件和子模块
try:
    # 收集所有 paddleocr 子模块
    paddleocr_submodules = collect_submodules('paddleocr')
    hiddenimports.extend(paddleocr_submodules)
    
    # 收集 paddleocr 数据文件
    paddleocr_datas = collect_data_files('paddleocr')
    datas.extend(paddleocr_datas)
except Exception as e:
    print(f"警告: 收集 PaddleOCR 数据时出错: {e}")

try:
    # 收集所有 easyocr 子模块
    easyocr_submodules = collect_submodules('easyocr')
    hiddenimports.extend(easyocr_submodules)
    
    # 收集 easyocr 数据文件
    easyocr_datas = collect_data_files('easyocr')
    datas.extend(easyocr_datas)
except Exception as e:
    print(f"警告: 收集 EasyOCR 数据时出错: {e}")

block_cipher = None

# 确保使用绝对路径
gui_py_path = os.path.join(project_root, 'gui.py')
if not os.path.exists(gui_py_path):
    raise FileNotFoundError(f"找不到 gui.py 文件: {gui_py_path}")

a = Analysis(
    [gui_py_path],  # 使用绝对路径
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScreenScanOCR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件，可以指定路径，如: icon='icon.ico'
)

