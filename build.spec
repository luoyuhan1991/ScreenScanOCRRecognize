# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/config.yaml', 'config'),     # 主配置（运行时可写回）
        ('requirements.txt', '.'),
        ('ui/styles/light.qss', 'ui/styles'),  # QSS 主题
        ('ui/icons/app.ico', 'ui/icons'),     # exe / 任务栏图标
        ('ui/icons/app.png', 'ui/icons'),
        ('ui/icons/check.svg', 'ui/icons'),    # 控件 SVG 资源（QSS 用 {ICON_DIR}/*.svg 引用）
        ('ui/icons/chevron-down.svg', 'ui/icons'),
        ('ui/icons/pencil.svg', 'ui/icons'),
        ('ui/icons/play.svg', 'ui/icons'),
        ('ui/icons/rotate-ccw.svg', 'ui/icons'),
        ('ui/icons/stop.svg', 'ui/icons'),
    ],
    hiddenimports=[
        'paddleocr',
        'paddlepaddle',
        'cv2',
        'numpy',
        'yaml',
        'PIL',
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

