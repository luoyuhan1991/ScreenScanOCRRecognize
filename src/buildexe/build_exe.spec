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

# 收集数据文件
datas = [
    ('src/config/config.yaml', 'src/config'),
    ('docs/banlist.txt', 'docs'),
]

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
    'easyocr',
    'torch',
    'paddle',
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

# 收集PaddleOCR和EasyOCR的数据文件
try:
    paddleocr_datas = collect_data_files('paddleocr')
    datas.extend(paddleocr_datas)
except:
    pass

try:
    easyocr_datas = collect_data_files('easyocr')
    datas.extend(easyocr_datas)
except:
    pass

block_cipher = None

a = Analysis(
    ['gui.py'],
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

