"""
打包脚本 - 将项目打包成可执行EXE文件
使用方法: python src/buildexe/build_exe.py
"""

import os

import PyInstaller.__main__


def build_exe():
    """构建EXE文件"""
    
    # 获取项目根目录（buildexe文件夹在src下，需要获取src的父目录）
    build_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(build_dir)
    project_root = os.path.dirname(src_dir)
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    # PyInstaller参数
    args = [
        'gui.py',  # 主入口文件
        '--name=ScreenScanOCR',  # 生成的EXE名称
        '--onefile',  # 打包成单个文件
        '--windowed',  # 不显示控制台窗口（GUI应用）
        # '--icon=icon.ico',  # 如果有图标文件，取消注释并指定路径
        
        # 添加数据文件
        '--add-data=src/config/config.yaml;src/config',  # 配置文件
        '--add-data=docs/banlist.txt;docs',  # 关键词文件
        
        # 隐藏导入（PyInstaller可能无法自动检测的模块）
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=tkinter.scrolledtext',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageTk',
        '--hidden-import=PIL.ImageGrab',
        '--hidden-import=cv2',
        '--hidden-import=numpy',
        '--hidden-import=yaml',
        '--hidden-import=paddleocr',
        '--hidden-import=easyocr',
        '--hidden-import=torch',
        '--hidden-import=paddle',
        
        # 排除不需要的模块（减小文件大小）
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        '--exclude-module=pandas',
        
        # 其他选项
        '--clean',  # 清理临时文件
        '--noconfirm',  # 覆盖输出目录而不询问
    ]
    
    print("=" * 60)
    print("ScreenScanOCR 打包工具")
    print("=" * 60)
    print(f"项目目录: {project_root}")
    print("\n注意：")
    print("1. 打包过程可能需要较长时间，请耐心等待...")
    print("2. 生成的EXE文件将在 dist 目录中")
    print("3. 由于包含OCR模型，EXE文件会比较大（几百MB到几GB）")
    print("=" * 60)
    print()
    
    # 执行打包
    PyInstaller.__main__.run(args)
    
    print("\n打包完成！")
    print(f"EXE文件位置: {os.path.join(project_root, 'dist', 'ScreenScanOCR.exe')}")

if __name__ == '__main__':
    build_exe()

