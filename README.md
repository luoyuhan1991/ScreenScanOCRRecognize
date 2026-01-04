# ScreenScanOCRRecognize

屏幕扫描OCR识别项目

## 项目描述

本项目用于屏幕扫描和OCR文字识别。

## 环境要求

- Python 3.8+
- tkinter（GUI界面，Python标准库，某些Linux系统可能需要单独安装）
- 支持PaddleOCR和EasyOCR两种OCR引擎（通过pip安装依赖即可）

## 安装依赖

### 步骤1：安装核心依赖

```bash
pip install -r requirements.txt
```

这会安装以下核心依赖：
- **图像处理**：Pillow (PIL)、OpenCV (cv2)、NumPy
- **配置文件**：PyYAML
- **OCR引擎**：PaddleOCR 或 EasyOCR（二选一或同时安装）
- **打包工具**：PyInstaller（可选，用于打包成EXE）

### 步骤2：安装GPU加速依赖（可选，但推荐）

**重要提示**：`paddlepaddle-gpu` 和 `torch` 不能直接从PyPI安装，需要根据CUDA版本从指定源安装。

#### 如果使用PaddleOCR（推荐）

1. **检查CUDA版本**：
   ```bash
   nvidia-smi
   ```

2. **根据CUDA版本安装PaddlePaddle-GPU**：
   
   **CUDA 11.8（推荐，兼容性最好）**：
   ```bash
   pip install paddlepaddle-gpu==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
   ```
   
   **CUDA 12.3+（使用CUDA 11.8版本，向后兼容）**：
   ```bash
   pip install paddlepaddle-gpu==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
   ```
   
   **其他CUDA版本**：请参考 `requirements.txt` 中的详细说明
   
   **无GPU（CPU版本）**：
   ```bash
   pip install paddlepaddle==3.2.2
   ```

#### 如果使用EasyOCR

1. **根据CUDA版本安装PyTorch-GPU**：
   
   **CUDA 11.8**：
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
   
   **CUDA 12.1**：
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
   
   **无GPU（CPU版本）**：
   ```bash
   pip install torch torchvision torchaudio
   ```

### 验证安装

安装完成后，可以验证GPU是否可用：

```bash
# 验证PaddlePaddle GPU（如果使用PaddleOCR）
python -c "import paddle; print('PaddlePaddle版本:', paddle.__version__); print('CUDA支持:', paddle.is_compiled_with_cuda())"

# 验证PyTorch GPU（如果使用EasyOCR）
python -c "import torch; print('PyTorch版本:', torch.__version__); print('CUDA可用:', torch.cuda.is_available())"
```

**注意：** 
- 首次运行时会自动下载OCR模型文件（约几百MB），请确保网络连接正常
- 如果使用GPU加速，需要先安装CUDA和cuDNN
- 详细安装说明请参考 `requirements.txt` 中的注释

## 运行

### 方式1: GUI图形界面（推荐）

提供友好的图形用户界面，方便配置参数和监控状态。

```bash
python gui.py
```

**GUI功能特点：**
- 📊 实时状态监控（扫描次数、最后扫描时间）
- ⚙️ 可视化参数配置（扫描、OCR、匹配等）
- 📝 实时日志显示（支持颜色区分）
- 💾 自动保存配置和窗口状态
- 🔧 内置配置文件编辑器（语法高亮、格式验证）

详细使用说明请参考 [GUI使用指南](#gui使用指南) 章节。

### 方式2: 命令行运行

```bash
python main.py
```

根据提示输入选项，或使用命令行参数：
```bash
# 格式: py main.py [roi_choice] [gpu_choice] [lang_choice]

# 示例1: 全屏扫描、自动GPU、中英文
py main.py 1 1 1

# 示例2: 选择ROI区域、自动GPU、中英文
py main.py 2 1 1

# 示例3: 全屏扫描、强制CPU、仅英文
py main.py 1 3 3
```

**参数格式**: `python main.py [roi_choice] [gpu_choice] [lang_choice]`

- **ROI选项**: `1`=全屏扫描, `2`=选择ROI区域
- **GPU选项**: `1`=自动检测, `2`=强制GPU, `3`=强制CPU
- **语言选项**: `1`=中英文, `2`=仅中文, `3`=仅英文

## 功能特性

- **自动屏幕截图**：按设定间隔自动截图
- **OCR文字识别**：支持PaddleOCR和EasyOCR引擎，支持中文和英文
  - 图像预处理：自适应阈值、降噪、锐化
  - 智能文本后处理：修复常见OCR错误
- **ROI区域选择**：可选择特定区域进行识别
- **GPU加速**：支持GPU加速，提升识别速度
- **文字匹配**：支持关键词匹配和弹窗提醒
- **自动保存**：截图和OCR结果自动保存到 `output` 文件夹
- **自动清理**：自动清理超过1小时的旧文件（每10分钟执行一次）

## GUI使用指南

### 快速开始

1. **运行GUI程序**
   ```bash
   python gui.py
   ```

2. **配置参数**
   - 在界面中调整扫描配置、OCR配置和文字匹配配置
   - 配置会自动保存到 `config/config.yaml`

3. **开始扫描**
   - 点击"▶ 开始扫描"按钮
   - 如果启用了ROI，会弹出ROI选择窗口
   - 程序开始按设定的间隔进行扫描

### 主界面功能

#### 状态栏
- 显示当前运行状态（已停止/运行中）
- 显示扫描次数和最后扫描时间

#### 扫描配置
- **启用ROI区域选择**：勾选后，开始扫描时会弹出ROI选择窗口
- **启用GPU加速**：是否使用GPU加速OCR识别
- **扫描间隔**：设置两次扫描之间的间隔时间（1-60秒）

#### OCR配置
- **OCR引擎**：选择PaddleOCR或EasyOCR
- **最小置信度**：设置OCR识别的最小置信度阈值（0.0-1.0）
- **图像预处理选项**：启用预处理、CLAHE增强、图像锐化、快速模式

#### 文字匹配
- **启用文字匹配**：是否启用关键词匹配功能
- **关键词文件**：选择关键词文件路径
- **显示设置**：显示时长（1-10秒）和显示位置（居中/顶部/底部）

#### 运行日志
- 实时显示程序运行日志
- 支持不同级别的日志颜色显示
- 自动滚动到最新日志

#### 功能按钮
- **▶ 开始扫描**：开始OCR扫描
- **⏹ 停止扫描**：停止当前扫描
- **⚙ 重置配置**：重置所有配置为默认值
- **📝 编辑配置**：打开配置文件编辑器（支持YAML语法高亮和格式验证）

## 打包为EXE

**前置要求**：安装 PyInstaller
```bash
pip install -r requirements.txt
```

**打包方法**：
```bash
# 方法1：使用打包脚本（推荐）
python src/buildexe/build_exe.py

# 方法2：使用 spec 文件
pyinstaller src/buildexe/build_exe.spec
```

**打包结果**：EXE文件位于 `dist/ScreenScanOCR.exe`

**注意事项**：
- 打包后的EXE文件较大（几百MB到几GB），包含OCR模型
- 首次运行可能需要解压临时文件，启动较慢
- 配置文件 `config/config.yaml` 会被打包进EXE
- 打包后的EXE仍然可以使用GPU，但需要目标机器安装相应的CUDA驱动

**常见问题**：
- **打包失败：找不到模块**：检查是否安装了所有依赖，在 `src/buildexe/build_exe.spec` 中添加缺失的隐藏导入
- **运行时错误：找不到配置文件**：确保 `--add-data` 参数正确，检查代码中文件路径是否为相对路径
- **EXE文件太大**：使用 `--onedir` 而不是 `--onefile`（启动更快）

## 项目结构

```
ScreenScanOCRRecognize/
├── main.py              # 命令行主程序入口
├── gui.py               # GUI主程序入口
├── requirements.txt     # 项目依赖
├── .gitignore          # Git忽略文件
├── README.md           # 项目说明
├── config/             # 配置文件目录
│   ├── config.yaml          # 主配置文件
│   └── gui_state.json       # GUI状态文件
├── src/                # 源代码目录
│   ├── __init__.py
│   ├── buildexe/        # 打包相关文件
│   │   ├── build_exe.py     # 打包脚本
│   │   └── build_exe.spec   # PyInstaller打包配置
│   ├── config/         # 配置模块（代码）
│   │   ├── __init__.py
│   │   ├── config.py          # 配置管理
│   │   ├── gui_state.py       # GUI状态管理
│   │   └── config_editor.py  # 配置编辑器
│   ├── ocr/            # OCR模块
│   │   ├── __init__.py
│   │   ├── ocr_adapter.py     # OCR适配器
│   │   ├── paddle_ocr.py      # PaddleOCR实现
│   │   └── easy_ocr.py        # EasyOCR实现
│   ├── gui/            # GUI模块
│   │   ├── __init__.py
│   │   └── gui_logger.py      # GUI日志处理器
│   ├── utils/           # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py           # 日志模块
│   │   ├── scan_screen.py      # 屏幕扫描
│   │   ├── text_matcher.py     # 文字匹配
│   │   └── cleanup_old_files.py # 文件清理
│   └── tests/           # 测试模块
│       ├── __init__.py
│       └── test_gpu.py         # GPU测试
│
├── docs/               # 文档目录
│   ├── GUI_DESIGN.md        # GUI设计文档
│   ├── GPU_SETUP_GUIDE.md   # GPU安装指南
│   └── banlist.txt          # 关键词文件示例
│
└── output/             # 输出目录（截图和OCR结果）
```

### 目录说明

- **main.py**: 命令行程序入口
- **gui.py**: GUI程序入口
- **config/**: 配置文件目录
  - `config.yaml`: 主配置文件（YAML格式）
  - `gui_state.json`: GUI界面状态文件
- **src/config/**: 配置管理模块（代码）
- **src/ocr/**: OCR引擎模块（PaddleOCR、EasyOCR）
- **src/gui/**: GUI相关模块
- **src/utils/**: 工具模块（日志、屏幕扫描、文字匹配、文件清理等）
- **src/buildexe/**: 打包相关文件
- **docs/**: 项目文档
- **output/**: 输出目录（自动生成，保存截图和OCR结果）