# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/config.yaml', 'config'),    # 配置文件
        ('requirements.txt', '.'),            # 依赖清单
        ('ui/icons/app.ico', 'ui/icons'),     # 主应用图标（运行时 QIcon 也会读这里）
        # TODO: 打包 PySide6 资源（ui/styles/*.qss、ui/icons/*.svg）；tkinter hiddenimport 已不再使用
    ],
    hiddenimports=[
        'paddleocr',
        'paddlepaddle',
        'cv2',
        'numpy',
        'yaml',
        'PIL',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的模块以减小体积
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
    ],
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
    icon='ui/icons/app.ico',  # exe 文件图标 / 任务栏 fallback
)

