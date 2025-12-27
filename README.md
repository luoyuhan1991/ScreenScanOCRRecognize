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

```bash
python main.py
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
├── scan_screen.py       # 屏幕扫描模块
├── ocr_recognize.py     # OCR识别模块
├── cleanup_old_files.py # 清理旧文件模块
├── requirements.txt     # 项目依赖
├── .gitignore          # Git忽略文件
├── README.md           # 项目说明
└── output/             # 输出目录（截图和OCR结果）
```

