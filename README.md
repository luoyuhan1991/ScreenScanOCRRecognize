# ScreenScanOCRRecognize

屏幕扫描OCR识别项目

## 项目描述

本项目用于屏幕扫描和OCR文字识别。

## 环境要求

- Python 3.8+
- 无需安装额外的OCR引擎（使用纯Python的EasyOCR库）

## 安装依赖

```bash
pip install -r requirements.txt
```

或使用：

```bash
py -m pip install -r requirements.txt
```

**注意：** 首次运行时会自动下载OCR模型文件（约几百MB），请确保网络连接正常。

## 运行

### 方式1: 交互式运行（默认）
```bash
py main.py
```
或
```bash
python main.py
```

然后根据提示输入选项：
- 是否选择ROI区域
- 是否使用GPU加速
- OCR语言设置

### 方式2: 命令行参数运行
```bash
# 格式: py main.py [roi_choice] [gpu_choice] [lang_choice]

# 示例1: 全屏扫描、自动GPU、中英文
py main.py 1 1 1

# 示例2: 选择ROI区域、自动GPU、中英文
py main.py 2 1 1

# 示例3: 全屏扫描、强制CPU、仅英文
py main.py 1 3 3
```

#### 参数说明

**ROI选项 (roi_choice)**
- `1`: 全屏扫描（默认）
- `2`: 选择ROI区域（需要交互式选择）

**GPU选项 (gpu_choice)**
- `1`: 自动检测（默认）
- `2`: 强制使用GPU
- `3`: 强制使用CPU

**语言选项 (lang_choice)**
- `1`: 中文简体 + 英文（默认）
- `2`: 仅中文简体
- `3`: 仅英文
- `4`: 自定义语言（需要额外参数，如：`py main.py 1 1 4 ch_sim,en,ja`）

### 测试脚本

项目提供了多个测试脚本用于验证功能：

```bash
# 快速测试OCR功能
py tests/simple_test.py

# 测试图像分辨率优化
py tests/resolution_test.py

# 带超时的OCR测试
py tests/timeout_test.py

# 测试GPU加速是否正常工作
py scripts/test_gpu.py
```

## 功能特性

- 自动屏幕截图（每5秒一次）
- **优化的OCR文字识别**（支持中文和英文）
  - 图像预处理：自适应阈值、降噪、锐化
  - 智能文本后处理：修复常见OCR错误
  - 降低置信度阈值以获取更多识别结果
- 识别结果实时输出并保存到文件
- 截图和OCR结果自动保存到 `output` 文件夹
- **自动清理超过1小时的旧文件**（独立线程，每整10分钟执行一次），节省磁盘空间

## 输出文件

所有文件保存在 `output` 文件夹中，每次扫描会创建一个以时间戳命名的子文件夹：

```
output/
├── 20251227_123507/
│   ├── screenshot.png      # 屏幕截图
│   └── ocr_result.txt     # OCR识别结果文本
├── 20251227_123512/
│   ├── screenshot.png
│   └── ocr_result.txt
└── ...
```

每个扫描文件夹包含对应的截图和OCR识别结果，便于管理和查找。

**注意：** 程序会在独立线程中自动清理超过1小时的扫描结果文件夹，每整10分钟执行一次清理（例如：10:00, 10:10, 10:20等），只保留最近1小时内的数据。

## 项目结构

```
ScreenScanOCRRecognize/
├── main.py              # 主程序入口
├── requirements.txt     # 项目依赖
├── .gitignore          # Git忽略文件
├── README.md           # 项目说明
│
├── src/                # 源代码目录
│   ├── __init__.py
│   ├── scan_screen.py       # 屏幕扫描模块
│   └── ocr_recognize.py     # OCR识别模块
│
├── scripts/            # 辅助脚本目录
│   ├── cleanup_old_files.py # 清理旧文件模块
│   ├── test_gpu.py          # GPU加速测试脚本
│   └── install_gpu.bat      # GPU安装脚本
│
├── docs/               # 文档目录
│   └── GPU_SETUP_GUIDE.md   # GPU安装指南
│
├── tests/              # 测试脚本目录
│   ├── simple_test.py       # 快速OCR测试
│   ├── resolution_test.py   # 图像分辨率优化测试
│   └── timeout_test.py      # 带超时的OCR测试
│
└── output/             # 输出目录（截图和OCR结果）
```

### 目录说明

- **main.py**: 程序入口，每5秒扫描一次屏幕并进行OCR识别
- **src/**: 核心源代码模块
  - `scan_screen.py`: 屏幕截图和ROI选择功能
  - `ocr_recognize.py`: OCR文字识别功能（使用EasyOCR）
- **scripts/**: 辅助工具脚本
  - `cleanup_old_files.py`: 自动清理旧文件
  - `test_gpu.py`: 测试GPU加速是否正常工作
  - `install_gpu.bat`: 一键安装GPU版本PyTorch
- **docs/**: 项目文档
  - `GPU_SETUP_GUIDE.md`: 详细的GPU安装和配置指南
- **tests/**: 测试脚本
  - `simple_test.py`: 快速测试OCR功能
  - `resolution_test.py`: 测试图像分辨率优化效果
  - `timeout_test.py`: 测试带超时控制的OCR识别
- **output/**: 自动生成的输出目录，保存截图和OCR结果