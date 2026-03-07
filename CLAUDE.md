# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

ScreenScanOCRRecognize 是一个基于 Python 的屏幕扫描和 OCR（光学字符识别）应用程序。它定期捕获屏幕截图，执行 OCR 文字识别，并从关键词文件中匹配关键词。应用程序支持 GUI 和 CLI 两种界面。

## 运行应用程序

### GUI 模式（推荐）
```bash
python app.py
```
GUI 提供实时状态监控、可视化配置和日志显示。

### CLI 模式
```bash
python cli.py
```
或使用命令行参数：
```bash
python cli.py [roi_choice] [gpu_choice] [lang_choice] [ocr_choice] [match_choice] [banlist_file]
```

### 快速启动（Windows）
```bash
gui.bat
```

## 开发命令

### 安装依赖
```bash
pip install -r requirements.txt
```

**重要**：GPU 加速需要额外步骤：
- 对于 PaddleOCR 配合 CUDA 11.8：
  ```bash
  pip install paddlepaddle-gpu==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
  ```
- 对于 EasyOCR 配合 CUDA 11.8：
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
  ```

### 构建可执行文件
```bash
python src/utils/buildexe/build_exe.py
# 或
pyinstaller ScreenScanOCR.spec
```

### 测试 GPU 支持
```bash
python src/tests/test_gpu.py
```

## 架构

### 核心组件

**入口点：**
- `app.py` - GUI 应用程序（基于 tkinter）
- `cli.py` - 命令行界面

**服务层：**
- `src/core/scan_service.py` - 主扫描服务，协调 截图 → OCR → 匹配 工作流
- `src/core/ocr/ocr_adapter.py` - 统一的 OCR 配置和适配器模式，支持不同引擎

**OCR 引擎：**
- `src/core/ocr/paddle_ocr.py` - PaddleOCR 实现（默认，准确率更高）
- `src/core/ocr/easy_ocr.py` - EasyOCR 实现（备选）

**配置：**
- `src/config/config.py` - 单例配置管理器，从 `config/config.yaml` 加载
- `src/config/gui_state.py` - GUI 窗口状态持久化
- `src/config/config_editor.py` - 内置 YAML 配置编辑器

**工具类：**
- `src/utils/scan_screen.py` - 屏幕截图和 ROI 区域选择
- `src/utils/text_matcher.py` - 关键词匹配（带缓存）
- `src/utils/logger.py` - 日志配置
- `src/utils/gui_logger.py` - GUI 日志处理器（基于队列）
- `src/utils/global_hotkey.py` - 系统全局热键（Ctrl+Alt+1/2）
- `src/utils/tray_icon.py` - 系统托盘集成
- `src/utils/mem_monitor.py` - 内存监控

### 关键设计模式

**单例模式：**
- `Config` 类使用单例模式确保整个应用程序中只有一个配置实例

**适配器模式：**
- `OCRConfig` 为 PaddleOCR 和 EasyOCR 引擎提供统一接口
- 语言代码自动映射（例如：'ch' → Paddle 的 'ch'，Easy 的 'ch_sim'）

**服务模式：**
- `ScanService` 封装完整的扫描工作流：截图 → OCR → 匹配 → 保存
- 缓存配置以避免扫描循环中重复读取文件

**基于队列的日志：**
- GUI 使用 `queue.Queue` 安全地将日志消息从工作线程传递到主 GUI 线程

### 配置系统

配置从 `config/config.yaml` 加载，结构如下：
- `scan.*` - 扫描设置（间隔、ROI、边距）
- `ocr.*` - OCR 引擎、语言、置信度阈值
- `gpu.*` - GPU/CPU 选择（force_gpu、force_cpu、auto_detect）
- `files.*` - 输出目录、关键词文件、保存选项
- `matching.*` - 关键词匹配设置（启用、显示时长、位置）
- `logging.*` - 日志级别、文件、格式

`Config` 类将文件配置与默认值合并，并提供点号访问：`config.get('scan.interval_seconds', 5)`

### OCR 工作流

1. **初始化**：`ScanService.init_ocr()` 创建 `OCRConfig` 并初始化选定的引擎
2. **截图**：`scan_screen()` 捕获屏幕或 ROI 区域
3. **识别**：引擎特定的 `recognize_and_print()` 执行 OCR
4. **匹配**：`TextMatcher.match()` 检查 OCR 结果是否匹配关键词
5. **显示**：`display_matches()` 在覆盖窗口中显示匹配结果
6. **清理**：每 10 次扫描删除旧的输出文件

### 线程模型

- **主线程**：GUI 事件循环（tkinter）
- **扫描线程**：运行 `_scan_loop()`，重复调用 `scan_service.scan_once()`
- **日志线程**：处理日志队列并更新 GUI 文本控件
- **热键线程**：监听全局键盘快捷键（Ctrl+Alt+1/2）
- **托盘线程**：管理系统托盘图标

## 重要说明

### GPU 配置优先级
1. 传递给 `init_ocr()` 的显式 `use_gpu` 参数
2. 配置文件设置：`force_cpu` > `force_gpu` > `auto_detect`
3. 默认值：`force_gpu=True`

### 语言处理
- PaddleOCR 仅支持单一语言（如果指定多个则默认为 'ch'）
- EasyOCR 支持同时使用多种语言
- 语言代码由 `OCRConfig` 自动映射

### 文件组织
- 截图和 OCR 结果保存到 `output/` 目录
- 每 10 次扫描自动清理（删除 output/ 中的所有文件）
- 日志保存到 `logs/app.log`，支持日志轮转

### ROI（感兴趣区域）
- 可通过 `select_roi_interactive()` 交互式选择 ROI
- 如果 `remember_roi=true`，ROI 坐标会保存到配置
- ROI 区域周围应用边距（默认 10px）

### 内存管理
- OCR 模型加载一次后在多次扫描中重复使用
- `release_resources()` 显式清除 OCR 实例并运行垃圾回收
- 日志队列设置 maxsize=2000 以防止无限增长

### OCR 性能优化
- **图像取反优化**：通过 `ocr.enable_image_invert` 配置控制是否进行图像取反处理
  - 白底黑字场景：设置为 `false` 可提升 15-25% 识别速度
  - 黑底白字场景：设置为 `true` 以提高识别准确率
  - 自动检测：设置 `ocr.auto_detect_invert=true` 自动判断是否需要取反
- **图像格式转换优化**：自动检测图像类型，避免重复转换，减少 5-10ms 处理时间

## 常见模式

### 添加新的 OCR 引擎
1. 在 `src/core/ocr/` 中创建新文件（例如 `tesseract_ocr.py`）
2. 实现 `init_reader()` 和 `recognize_and_print()` 函数
3. 将语言映射添加到 `OCRConfig.TESSERACT_LANG_MAP`
4. 更新 `OCRConfig.get_tesseract_params()` 方法
5. 在 `ScanService.init_ocr()` 中添加引擎选择

### 修改配置
- 直接编辑 `config/config.yaml`，或
- 使用 GUI 的内置配置编辑器（⚙ 编辑配置按钮），或
- 编程方式：`config.set('key.path', value)` 然后 `config.save()`

### 添加 GUI 控件
- 在 `MainGUI.create_widgets()` 中添加控件
- 在 `load_settings()` 和 `save_settings()` 中绑定到配置
- 更新 `on_start_scan()` 以使用新设置

## 故障排除

### OCR 模型无法加载
- 检查 GPU 驱动程序和 CUDA 版本兼容性
- 验证正确安装了 paddlepaddle-gpu 或 torch
- 尝试强制 CPU 模式：在配置中设置 `gpu.force_cpu=true`

### 内存占用过高
- 减少 `MainGUI.__init__()` 中的日志队列大小（默认 2000）
- 启用自动清理：`cleanup.enabled=true`
- 增加扫描间隔以降低频率

### 热键不工作
- Windows 上需要 `keyboard` 包和管理员权限
- 检查是否有其他应用程序正在使用 Ctrl+Alt+1/2
- 热键注册在 `app.py` 中通过 `register_scan_hotkeys()` 完成
