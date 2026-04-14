# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

ScreenScanOCRRecognize 是一个 Windows 平台的屏幕扫描 OCR 应用。核心流程：定时截图 → OCR 识别 → 关键词匹配 → 屏幕弹窗提示。支持 GUI（tkinter）和 CLI 两种界面。

## 运行与构建

```bash
# GUI 模式（推荐）
python app.py
# 或 Windows 双击 gui.bat（通过 VBScript 隐藏控制台窗口，通过 .venv 虚拟环境启动）

# CLI 模式
python cli.py
python cli.py [roi_choice] [gpu_choice] [lang_choice] [ocr_choice] [match_choice] [banlist_file]

# 安装依赖
pip install -r requirements.txt

# GPU 加速（需要额外安装，不在 requirements.txt 中）
# PaddleOCR + CUDA 11.8:
pip install paddlepaddle-gpu==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
# EasyOCR + CUDA 11.8:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 测试 GPU
python src/tests/test_gpu.py

# 打包 EXE
python src/utils/buildexe/build_exe.py
```

## 目录结构

```
ScreenScanOCRRecognize/
├── app.py                          # GUI 入口（~1160 行，MainGUI 类）
├── cli.py                          # CLI 入口（~210 行，交互式/命令行参数）
├── gui.bat                         # GUI 启动批处理（VBScript 隐藏控制台）
├── config/
│   ├── config.yaml                 # 主配置文件
│   └── gui_state.json              # GUI 窗口状态持久化
├── src/
│   ├── config/
│   │   ├── config.py               # Config 单例（~195 行）
│   │   ├── config_editor.py        # YAML 配置编辑器（带语法高亮）
│   │   └── gui_state.py            # GUIStateManager 窗口状态管理
│   ├── core/
│   │   ├── scan_service.py         # ScanService 扫描工作流（~311 行）
│   │   └── ocr/
│   │       ├── ocr_adapter.py      # OCRConfig 统一适配器（~182 行）
│   │       ├── paddle_ocr.py       # PaddleOCR 引擎（~324 行）
│   │       └── easy_ocr.py         # EasyOCR 引擎（~334 行）
│   ├── utils/
│   │   ├── logger.py               # 日志配置（控制台+旋转文件）
│   │   ├── gui_logger.py           # GUI 日志处理器（线程安全队列）
│   │   ├── scan_screen.py          # 截图 + ROI 交互选择（~303 行）
│   │   ├── text_matcher.py         # 关键词匹配 + 弹窗显示（~839 行）
│   │   ├── global_hotkey.py        # 全局热键（Ctrl+Alt+1/2）
│   │   ├── tray_icon.py            # 系统托盘图标（pystray）
│   │   ├── mem_monitor.py          # 内存监控
│   │   └── buildexe/
│   │       └── build_exe.py        # PyInstaller 打包脚本
│   └── tests/
│       ├── test_gpu.py             # GPU 检测测试
│       ├── test_memory_optimization.py
│       └── test_ocr_performance.py
├── docs/                           # 文档和默认关键词文件
├── new_version/                    # 实验性 pipeline 架构版本
│   └── src/pipeline/               # capture → diff_gate → ocr_stage → match_stage
├── output/                         # 截图和 OCR 结果输出
└── logs/                           # 应用日志
```

## 架构

### 数据流

```
app.py/cli.py → ScanService.scan_once()
  → scan_screen(roi) → 帧差检测 → OCR引擎 → _normalize_ocr_results()
  → TextMatcher.match() → display_ocr_results()
```

### 核心模块

- **`app.py`** — GUI 入口，`MainGUI` 类。管理扫描配置面板（ROI/GPU/间隔/OCR引擎/置信度）、匹配配置面板（关键词文件/显示时长/位置/字号）、日志显示区、系统托盘。OCR 初始化在后台线程完成，通过回调通知 GUI
- **`cli.py`** — CLI 入口，支持命令行参数（位置参数）和交互式输入两种模式。循环调用 `ScanService.scan_once()` + `display_matches()`
- **`src/core/scan_service.py`** — `ScanService` 类，封装完整扫描工作流。`scan_once()` 执行：缓存配置刷新 → 截图 → 帧差检测（MSE，160x120 灰度图）→ OCR → 结果标准化 → 匹配 → 清理。帧差相似时跳过 OCR 复用上次结果
- **`src/core/ocr/ocr_adapter.py`** — `OCRConfig` 适配器，统一 PaddleOCR 和 EasyOCR 的语言映射和参数格式。GPU 设置三级优先级：函数参数 > 配置文件(`force_cpu`/`force_gpu`/`auto_detect`) > 默认
- **`src/core/ocr/paddle_ocr.py`** / **`easy_ocr.py`** — 各引擎实现，暴露 `init_reader()` 和 `recognize_and_print()` 两个函数。内部维护全局单例（`_ocr_instance` / `_reader`），参数不变时复用。包含图像预处理（自适应阈值、去噪、锐化）和文本后处理
- **`src/config/config.py`** — `Config` 单例，从 `config/config.yaml` 加载，与硬编码默认值深度合并。点号路径访问：`config.get('scan.interval_seconds', 5)`，支持 `config.set()` + `config.save()`。脏标记（`is_dirty()`/`clear_dirty()`）用于 `ScanService` 按需刷新缓存
- **`src/utils/text_matcher.py`** — `TextMatcher` 类，加载关键词文件（banlist），支持子串匹配（`keyword_in_text`）和模糊比例匹配（`_match_ratio`，按顺序字符匹配百分比）。关键词文件格式：`关键词 提示词`（空白分隔）或 `关键词:提示词`（冒号分隔）。通过 `_get_cached_matcher()` 缓存实例，文件修改时间变更时自动重载。`display_ocr_results()` 在 Tkinter 窗口显示弹窗提示，`reset_alerted_keywords()` 重置已提醒关键词

### 线程模型（GUI 模式）

- **主线程**：tkinter 事件循环
- **OCR 初始化线程**：`_init_ocr_in_thread()` 后台加载模型，完成后通过 `root.after(0, callback)` 通知主线程
- **扫描线程**：循环调用 `scan_service.scan_once()`，通过 `threading.Event` (`stop_event`) 控制停止
- **日志线程**：`queue.Queue` 从工作线程收集日志，主线程定时 `update_log_from_queue()` 读取更新 GUI（带颜色：DEBUG=cyan, INFO=green, WARNING=yellow, ERROR=red）
- **热键线程**：`keyboard` 库全局钩子，Ctrl+Alt+1 开始 / Ctrl+Alt+2 停止，通过 `root.after(0, callback)` 回到主线程
- **托盘线程**：`pystray` 系统托盘图标，左键显示/隐藏窗口，右键菜单

同步原语：`threading.Event`（停止信号）、`threading.Lock`（单例锁、缓存锁、已提醒关键词锁）、`queue.Queue`（日志队列）。

### 配置体系

配置文件 `config/config.yaml`，主要分组：
- `scan.*` — 间隔秒数、ROI 开关/保存/边距、帧差检测开关/阈值
- `ocr.*` — 引擎选择(`paddle`/`easy`)、语言列表、最低置信度、图像取反开关/自动检测、EasyOCR 专用参数(`canvas_size`/`mag_ratio`/`dynamic_params`)
- `gpu.*` — GPU 优先级：`force_cpu` > `force_gpu` > `auto_detect`
- `files.*` — 输出目录、关键词文件路径、截图/OCR结果保存开关、文件夹模式(`minute`)、最大文件夹数
- `matching.*` — 匹配开关、显示时长/位置/字号、模糊阈值、声音提示开关
- `performance.*` — 内存监控间隔、psutil 开关、日志队列大小/清理阈值、显式图像清理
- `cleanup.*` — 自动清理开关、最大保留小时数、清理检查间隔、扫描清理间隔
- `logging.*` — 日志级别、文件路径、格式、旋转大小/备份数

GUI 窗口状态单独保存在 `config/gui_state.json`（`GUIStateManager`），包含窗口位置大小和控件值。

## 关键设计决策

**OCR 引擎延迟加载**：`init_reader()` 只在首次扫描前调用一次，模型常驻内存复用。`release_resources()` 显式置空实例 + `gc.collect()`。

**帧差检测跳过 OCR**：`scan.enable_diff_skip` 控制。将截图缩放为 160x120 灰度图计算 MSE，低于阈值（默认 5.0）则跳过 OCR 直接复用上次结果，大幅减少 GPU/CPU 占用。

**语言映射**：PaddleOCR 只支持单语言（多语言时默认 'ch'），EasyOCR 支持多语言并发。`OCRConfig` 内置 `PADDLE_LANG_MAP` 和 `EASYOCR_LANG_MAP` 做代码转换。

**图像取反优化**：`ocr.enable_image_invert` 控制。白底黑字关闭可提速 15-25%，黑底白字需开启提升准确率。`ocr.auto_detect_invert` 可自动判断。

**输出清理**：`ScanService` 每 N 次扫描（`cleanup.scan_interval`，默认 10）清空 output 目录旧文件；另有 `cleanup.*` 配置定时清理。

**PaddleOCR 版本兼容**：`paddle_ocr.py` 检测 PaddleOCR v2/v3 版本，v3 使用 `device='gpu'`/`device='cpu'`，v2 使用 `use_gpu=True/False`。

**全局热键**：仅 Windows，依赖 `keyboard` 库（需管理员权限）。缺失时会尝试 `pip install keyboard` 自动安装。

## 扩展模式

### 添加新 OCR 引擎
1. `src/core/ocr/` 新建引擎文件，实现 `init_reader()` 和 `recognize_and_print()`，返回格式 `[{'text': str, 'confidence': float, 'bbox': list}, ...]`
2. `OCRConfig` 添加语言映射字典和 `get_xxx_params()` 参数转换方法
3. `ScanService.init_ocr()` 添加引擎分支

### 添加 GUI 控件
1. `MainGUI.create_widgets()` 添加控件
2. `load_settings()` / `save_settings()` 绑定配置
3. `on_start()` 使用新设置

### 修改配置
- 编辑 `config/config.yaml`
- GUI 内置编辑器（`ConfigEditor`，支持 YAML 语法高亮和格式验证）
- 编程：`config.set('key.path', value)` + `config.save()`

## new_version 实验版本

`new_version/` 目录包含实验性的 pipeline 架构重构版本，将扫描流程拆分为独立阶段：`capture.py` → `diff_gate.py` → `ocr_stage.py` → `match_stage.py`，由 `pipeline.py` 编排。另有 `overlay/` 模块处理弹窗显示。当前主版本仍为根目录的 `app.py`/`cli.py`。
