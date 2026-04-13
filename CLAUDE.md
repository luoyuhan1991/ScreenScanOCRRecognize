# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

ScreenScanOCRRecognize 是一个 Windows 平台的屏幕扫描 OCR 应用。核心流程：定时截图 → OCR 识别 → 关键词匹配 → 屏幕弹窗提示。支持 GUI（tkinter）和 CLI 两种界面。

## 运行与构建

```bash
# GUI 模式（推荐）
python app.py
# 或 Windows 双击 gui.bat（会隐藏控制台窗口，通过 .venv 虚拟环境启动）

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

## 架构

### 数据流

```
app.py/cli.py → ScanService.scan_once() → scan_screen() → OCR引擎 → TextMatcher.match() → display_matches()
```

### 核心模块

- **`app.py`** — GUI 入口，1300+ 行的 `MainGUI` 类，包含所有界面逻辑
- **`cli.py`** — CLI 入口，交互式参数输入或命令行参数
- **`src/core/scan_service.py`** — `ScanService` 类，封装完整扫描工作流。每次 `scan_once()` 执行：准备目录 → 截图 → OCR → 匹配 → 清理。配置通过 `_cache_config()` 缓存，每次扫描前刷新
- **`src/core/ocr/ocr_adapter.py`** — `OCRConfig` 适配器，统一 PaddleOCR 和 EasyOCR 的语言映射和参数格式
- **`src/core/ocr/paddle_ocr.py`** / **`easy_ocr.py`** — 各引擎实现，暴露 `init_reader()` 和 `recognize_and_print()` 两个函数
- **`src/config/config.py`** — `Config` 单例，从 `config/config.yaml` 加载，与硬编码默认值合并。点号路径访问：`config.get('scan.interval_seconds', 5)`，支持 `config.set()` + `config.save()`
- **`src/utils/text_matcher.py`** — `TextMatcher` 类，加载关键词文件（banlist），支持子串匹配（`keyword_in_text`）和模糊比例匹配。关键词文件格式：`关键词 提示词`（空白分隔）或 `关键词:提示词`（冒号分隔）。通过 `_get_cached_matcher()` 缓存实例，文件变更时自动重载

### 线程模型（GUI 模式）

- **主线程**：tkinter 事件循环
- **扫描线程**：循环调用 `scan_service.scan_once()`，通过 `stop_event` 控制停止
- **日志线程**：`queue.Queue` 从工作线程收集日志，主线程定时读取更新 GUI
- **热键线程**：`keyboard` 库全局钩子，Ctrl+Alt+1 开始 / Ctrl+Alt+2 停止
- **托盘线程**：`pystray` 系统托盘图标

### 配置体系

配置文件 `config/config.yaml`，主要分组：
- `scan.*` — 间隔、ROI、边距
- `ocr.*` — 引擎选择、语言、置信度、图像取反
- `gpu.*` — GPU 优先级：`force_cpu` > `force_gpu` > `auto_detect`
- `files.*` — 输出目录、关键词文件、保存开关、文件夹模式
- `matching.*` — 匹配开关、显示时长/位置/字号、模糊阈值
- `performance.*` — 内存监控间隔、日志队列大小
- `cleanup.*` — 自动清理旧文件

GUI 窗口状态单独保存在 `config/gui_state.json`（`GUIStateManager`）。

## 关键设计决策

**OCR 引擎延迟加载**：`init_reader()` 只在首次扫描前调用一次，模型常驻内存复用。`release_resources()` 显式置空实例 + `gc.collect()`。

**语言映射**：PaddleOCR 只支持单语言（多语言时默认 'ch'），EasyOCR 支持多语言并发。`OCRConfig` 内置 `PADDLE_LANG_MAP` 和 `EASYOCR_LANG_MAP` 做代码转换。

**图像取反优化**：`ocr.enable_image_invert` 控制。白底黑字关闭可提速 15-25%，黑底白字需开启提升准确率。`ocr.auto_detect_invert` 可自动判断。

**输出清理**：`ScanService` 每 10 次扫描清空 output 目录旧文件；另有 `cleanup.*` 配置定时清理。

**全局热键**：仅 Windows，依赖 `keyboard` 库（需管理员权限）。缺失时会尝试 `pip install keyboard` 自动安装。

## 扩展模式

### 添加新 OCR 引擎
1. `src/core/ocr/` 新建引擎文件，实现 `init_reader()` 和 `recognize_and_print()`
2. `OCRConfig` 添加语言映射和参数转换方法
3. `ScanService.init_ocr()` 添加引擎分支

### 添加 GUI 控件
1. `MainGUI.create_widgets()` 添加控件
2. `load_settings()` / `save_settings()` 绑定配置
3. `on_start_scan()` 使用新设置

### 修改配置
- 编辑 `config/config.yaml`
- GUI 内置编辑器（`ConfigEditor`，支持 YAML 语法高亮和格式验证）
- 编程：`config.set('key.path', value)` + `config.save()`
