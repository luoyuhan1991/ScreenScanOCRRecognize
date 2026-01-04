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

### 方式2: 命令行交互式运行

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

### 方式3: 命令行参数运行
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

项目提供了测试脚本用于验证功能：

```bash
# 测试GPU加速是否正常工作
python -m src.tests.test_gpu
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

## GUI使用指南

### 快速开始

1. **运行GUI程序**
   ```bash
   python gui.py
   ```

2. **配置参数**
   - 在界面中调整扫描配置、OCR配置和文字匹配配置
   - 配置会自动保存到 `src/config/config.yaml`

3. **开始扫描**
   - 点击"▶ 开始扫描"按钮
   - 如果启用了ROI，会弹出ROI选择窗口
   - 程序开始按设定的间隔进行扫描

### 主界面说明

#### 1. 状态栏
- **状态**：显示当前运行状态（已停止/运行中）
- **扫描次数**：显示已完成的扫描次数
- **最后扫描**：显示最后一次扫描的时间

#### 2. 扫描配置
- **启用ROI区域选择**：勾选后，开始扫描时会弹出ROI选择窗口
- **启用GPU加速**：是否使用GPU加速OCR识别
- **扫描间隔**：设置两次扫描之间的间隔时间（1-60秒）

#### 3. OCR配置
- **OCR引擎**：选择PaddleOCR或EasyOCR
- **最小置信度**：设置OCR识别的最小置信度阈值（0.0-1.0）
- **启用图像预处理**：是否启用图像预处理
- **启用CLAHE增强**：是否启用CLAHE对比度增强
- **启用图像锐化**：是否启用图像锐化
- **快速模式**：跳过部分预处理以提升速度

#### 4. 文字匹配
- **启用文字匹配**：是否启用关键词匹配功能
- **关键词文件**：选择关键词文件路径（点击"浏览"按钮选择）
- **显示时长**：匹配成功后的显示时长（1-10秒）
- **显示位置**：选择显示位置（居中/顶部/底部）

#### 5. 运行日志
- 实时显示程序运行日志
- 支持不同级别的日志颜色显示
- 自动滚动到最新日志

#### 6. 功能按钮
- **▶ 开始扫描**：开始OCR扫描
- **⏹ 停止扫描**：停止当前扫描
- **⚙ 重置配置**：重置所有配置为默认值
- **📝 编辑配置**：打开配置文件编辑器

### 配置文件编辑器

点击"📝 编辑配置"按钮可以打开配置文件编辑器，支持：

- **语法高亮**：YAML语法高亮显示
- **格式验证**：保存时自动验证YAML格式
- **快捷键**：
  - `Ctrl+S`：保存配置
  - `Esc`：关闭编辑器
- **重置功能**：可以重置为原始内容

### 打包为EXE

1. **安装PyInstaller**
   ```bash
   pip install pyinstaller
   ```

2. **打包程序**
   ```bash
   pyinstaller build/build.spec
   ```

3. **运行打包后的程序**
   - 进入 `dist/ScreenScanOCR` 目录
   - 双击 `ScreenScanOCR.exe`

## 项目结构

```
ScreenScanOCRRecognize/
├── main.py              # 命令行主程序入口
├── gui.py               # GUI主程序入口
├── requirements.txt     # 项目依赖
├── .gitignore          # Git忽略文件
├── README.md           # 项目说明
├── build/               # 打包相关文件
│   └── build.spec       # PyInstaller打包配置
│
├── src/                # 源代码目录
│   ├── __init__.py
│   ├── config/         # 配置模块
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

- **main.py**: 命令行程序入口，支持交互式和命令行参数模式
- **gui.py**: GUI程序入口，提供图形用户界面
- **src/config/**: 配置管理模块
  - `config.py`: 核心配置管理（YAML读写、默认值）
  - `gui_state.py`: GUI界面状态（窗口大小、位置等）
  - `config_editor.py`: 配置文件编辑器
- **src/ocr/**: OCR模块
  - `ocr_adapter.py`: OCR适配器抽象和工厂
  - `paddle_ocr.py`: PaddleOCR实现
  - `easy_ocr.py`: EasyOCR实现
- **src/gui/**: GUI模块
  - `gui_logger.py`: GUI日志处理器
- **src/utils/**: 工具模块
  - `logger.py`: 日志系统
  - `scan_screen.py`: 屏幕截图和ROI选择
  - `text_matcher.py`: 文字匹配和显示
  - `cleanup_old_files.py`: 文件清理
- **src/tests/**: 测试模块
  - `test_gpu.py`: GPU测试工具
- **docs/**: 项目文档
  - `GUI_DESIGN.md`: GUI设计文档
  - `GPU_SETUP_GUIDE.md`: 详细的GPU安装和配置指南
- **output/**: 自动生成的输出目录，保存截图和OCR结果