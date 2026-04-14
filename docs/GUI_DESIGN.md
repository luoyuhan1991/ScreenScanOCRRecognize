# 屏幕扫描OCR识别系统 - GUI 设计文档

## 项目概述

ScreenScanOCRRecognize 的图形用户界面（GUI），基于 tkinter 实现，提供参数配置、状态监控、日志显示和系统托盘集成。

---

## 界面布局

### 主窗口结构

```
┌─────────────────────────────────────────────────────────────────────────┐
│  屏幕扫描OCR识别系统                                     [最小化][关闭] │
├─────────────────────────────────────────────────────────────────────────┤
│  【状态】                                                              │
│  状态: ● 已停止  |  扫描次数: 0  |  最后扫描: 无  |  内存: -- MB      │
├─────────────────────────────────────────────────────────────────────────┤
│  【扫描配置】                                                          │
│  ☑ 启用ROI区域选择  ☑ 记住ROI区域  ☑ 启用GPU加速  扫描间隔: [3] 秒   │
├─────────────────────────────────────────────────────────────────────────┤
│  【OCR配置】                                                           │
│  OCR引擎: ○ PaddleOCR  ○ EasyOCR  最小置信度: [0.30]  ☐ 保存截图和结果│
├─────────────────────────────────────────────────────────────────────────┤
│  【文字匹配】                                                          │
│  ☑ 启用文字匹配  关键词文件: [路径] [浏览...] [编辑]                   │
│  显示时长: [3] 秒  字体大小: [18] 像素  显示位置: [居中 ▼]            │
│  匹配比例: [0.85]  (50%~100%，达到该比例即算匹配)                      │
├─────────────────────────────────────────────────────────────────────────┤
│  【运行日志】                                              [🗑]        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  深色背景，彩色日志（Consolas 9pt）                              │   │
│  │  INFO=绿色  WARNING=黄色  ERROR=红色  DEBUG=蓝色                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│  [▶ 开始扫描]  [⏹ 停止扫描]  [⚙ 重置配置]  [📝 编辑配置]            │
└─────────────────────────────────────────────────────────────────────────┘
```

默认窗口大小 800x700，支持窗口状态持久化（位置、大小保存到 `config/gui_state.json`）。

---

## 参数配置

### 1. 扫描配置

| 参数 | 控件类型 | 默认值 | 范围 | 配置路径 |
|------|---------|--------|------|----------|
| 启用ROI区域选择 | 复选框 | false | - | `scan.enable_roi` |
| 记住ROI区域 | 复选框 | true | - | `scan.remember_roi` |
| 启用GPU加速 | 复选框 | true | - | `gpu.force_gpu` |
| 扫描间隔 | 滑动条+输入框 | 3.0 | 1-15秒 | `scan.interval_seconds` |

- ROI 边距使用 `scan.roi_padding`（默认 10 像素）
- ROI 区域保存在 `scan.saved_roi`（启用"记住ROI"时）
- 语言固定使用 `ocr.languages` 配置值（默认 `['ch', 'en']`）

### 2. OCR配置

| 参数 | 控件类型 | 默认值 | 范围 | 配置路径 |
|------|---------|--------|------|----------|
| OCR引擎 | 单选按钮 | PaddleOCR | paddle/easy | `ocr.default_engine` |
| 最小置信度 | 滑动条+输入框 | 0.30 | 0.0-1.0 | `ocr.min_confidence` |
| 保存截图和识别结果 | 复选框 | false | - | `files.save_screenshot` + `files.save_ocr_result` |

### 3. 文字匹配

| 参数 | 控件类型 | 默认值 | 范围 | 配置路径 |
|------|---------|--------|------|----------|
| 启用文字匹配 | 复选框 | true | - | `matching.enabled` |
| 关键词文件 | 输入框+浏览+编辑 | docs/banlist.txt | - | `files.banlist_file` |
| 显示时长 | 滑动条+输入框 | 3.0 | 1-10秒 | `matching.display_duration` |
| 字体大小 | 滑动条+输入框 | 18 | 12-22px | `matching.font_size` |
| 显示位置 | 下拉菜单 | 居中 | 居中/顶部/底部 | `matching.position` |
| 匹配比例 | 滑动条+输入框 | 0.85 | 0.5-1.0 | `matching.match_ratio_threshold` |

- 关键词文件支持浏览按钮选择和直接编辑按钮
- 匹配比例：关键词中该比例字符按顺序出现在 OCR 文本中即算匹配

### 4. 高级配置

通过"编辑配置"按钮打开 `ConfigEditor`，直接编辑 `config/config.yaml`：
- YAML 语法高亮和行号显示
- 保存时自动验证 YAML 格式
- 保存成功后自动重新加载配置

以下配置项不在 GUI 中直接显示，需通过配置编辑器修改：

| 配置分组 | 主要项 |
|----------|--------|
| `scan.*` | `roi_padding`、`enable_diff_skip`、`diff_threshold` |
| `ocr.*` | `languages`、`enable_image_invert`、`auto_detect_invert`、`easyocr.*` |
| `files.*` | `folder_mode`、`max_folders` |
| `cleanup.*` | `enabled`、`max_age_hours`、`interval_minutes`、`scan_interval` |
| `matching.*` | `enable_sound` |
| `logging.*` | `level`、`file`、`max_bytes`、`backup_count` |
| `performance.*` | `memory_monitor_interval_ms`、`max_log_queue_size`、`explicit_image_cleanup` |

---

## 文件结构

```
ScreenScanOCRRecognize/
├── app.py                          # GUI 入口，MainGUI 类（~1160 行）
├── gui.bat                         # 启动批处理（VBScript 隐藏控制台）
├── config/
│   ├── config.yaml                 # 业务配置（YAML）
│   └── gui_state.json              # GUI 窗口状态（JSON，自动生成）
├── src/
│   ├── config/
│   │   ├── config.py               # Config 单例，管理 config.yaml
│   │   ├── config_editor.py        # ConfigEditor，YAML 编辑器窗口
│   │   └── gui_state.py            # GUIStateManager，窗口状态管理
│   ├── core/
│   │   ├── scan_service.py         # ScanService，扫描工作流
│   │   └── ocr/                    # OCR 引擎
│   └── utils/
│       ├── gui_logger.py           # GUILoggerHandler，线程安全日志处理
│       ├── global_hotkey.py        # 全局热键注册
│       ├── tray_icon.py            # 系统托盘图标
│       ├── mem_monitor.py          # 内存监控
│       ├── scan_screen.py          # 截图 + ROI 交互选择
│       └── text_matcher.py         # 匹配 + 弹窗显示
└── docs/
    └── banlist.txt                 # 默认关键词文件
```

---

## 核心类

### MainGUI（app.py）

主 GUI 界面类，负责所有界面逻辑和用户交互。

**初始化流程**：
1. 创建 `ScanService` 和 `GUIStateManager` 实例
2. 加载窗口几何状态
3. `create_widgets()` 构建所有 UI 控件
4. `load_settings()` 从 config.yaml 加载配置到控件
5. `setup_gui_logger()` 设置日志处理器
6. 启动日志队列处理、托盘图标、全局热键

**主要方法**：

| 方法 | 职责 |
|------|------|
| `create_widgets()` | 构建状态栏、扫描/OCR/匹配配置面板、日志区、按钮区 |
| `on_start()` | 开始扫描：后台线程初始化 OCR → 启动扫描循环 |
| `on_stop()` | 停止扫描：设置 stop_event → 释放资源 |
| `_init_ocr_in_thread()` | 后台线程初始化 OCR 引擎，避免阻塞 GUI |
| `_on_ocr_init_complete()` | OCR 初始化完成回调，启动扫描循环 |
| `update_log_from_queue()` | 定时从日志队列读取消息更新日志区（drain 模式） |
| `load_settings()` / `save_settings()` | 配置与 GUI 控件间的双向绑定 |
| `on_interval_change()` 等 | 配置变更处理器，实时更新 config.yaml |

### GUIStateManager（src/config/gui_state.py）

管理 GUI 窗口状态，持久化到 `config/gui_state.json`。

| 方法 | 职责 |
|------|------|
| `get_window_geometry()` | 获取窗口位置和大小 |
| `set_window_geometry()` | 保存窗口位置和大小 |
| `load_state()` / `save_state()` | JSON 文件读写 |

### GUILoggerHandler（src/utils/gui_logger.py）

线程安全的日志处理器，将日志消息放入 `queue.Queue`，主线程定时消费。

- 日志颜色：INFO=绿色(#4ec9b0)、WARNING=黄色(#dcdcaa)、ERROR=红色(#f48771)、DEBUG=蓝色(#569cd6)
- 日志背景：深色(#1e1e1e)，字体 Consolas 9pt
- 队列大小可配置（`performance.max_log_queue_size`）

### ConfigEditor（src/config/config_editor.py）

YAML 配置文件编辑器窗口。

| 方法 | 职责 |
|------|------|
| `show()` | 打开编辑器窗口 |
| `load_config()` | 加载 config.yaml 内容到编辑区 |
| `save_config()` | 验证 YAML 格式并保存 |
| `validate_yaml()` | YAML 格式验证 |
| `highlight_syntax()` | 语法高亮 |
| `update_line_numbers()` | 行号显示 |

---

## 配置管理

### 双文件策略

| 文件 | 格式 | 内容 | 保存时机 |
|------|------|------|----------|
| `config/config.yaml` | YAML | 所有业务配置 | GUI 参数变更时实时保存 |
| `config/gui_state.json` | JSON | 窗口位置/大小 | 窗口关闭时保存 |

### 配置优先级

GUI 设置 → config.yaml → Config 类硬编码默认值

### 配置流程

- **参数变更**：GUI 控件 → `config.set('key.path', value)` → 自动保存 config.yaml
- **窗口关闭**：`GUIStateManager.save_state()` → 保存 gui_state.json
- **重置配置**：恢复 Config 类默认值 → 重新加载到 GUI 控件

---

## 线程架构

```
主线程（tkinter 事件循环）
  ├── OCR 初始化线程（一次性）
  │   └── init_reader() → root.after(0, callback)
  ├── 扫描线程（持续运行）
  │   └── while not stop_event: scan_once() → sleep(interval)
  ├── 热键线程（keyboard 库）
  │   └── Ctrl+Alt+1/2 → root.after(0, on_start/on_stop)
  ├── 托盘线程（pystray）
  │   └── 左键显示/隐藏 → root.after(0, callback)
  └── 日志处理（主线程定时器）
      └── root.after(100ms) → drain queue → 更新日志文本框
```

### 同步机制

| 原语 | 用途 |
|------|------|
| `threading.Event` | `stop_event`：扫描停止信号 |
| `queue.Queue` | 日志消息从工作线程传递到主线程 |
| `root.after(0, callback)` | 热键/托盘线程回到主线程执行 GUI 操作 |

### 线程安全原则

- GUI 更新必须在主线程执行，通过 `root.after()` 转发
- 日志通过队列传递，不直接操作 GUI 控件
- 扫描线程通过 `stop_event.wait(interval)` 实现可中断等待

---

## 系统托盘

使用 `pystray` 库实现（可选依赖，缺失时降级）：

- 托盘图标：动态生成 64x64 雷达扫描风格图标
- 左键点击：显示/隐藏主窗口
- 右键菜单：显示窗口、退出程序
- 关闭窗口行为：缩小到托盘（而非退出）

---

## 全局热键

使用 `keyboard` 库实现（Windows，需管理员权限）：

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Alt+1` | 开始扫描（主键盘/小键盘均可） |
| `Ctrl+Alt+2` | 停止扫描（主键盘/小键盘均可） |

注册在 `root.after_idle()` 中延迟执行，确保 GUI 初始化完成后再注册。

---

## 打包

### 打包命令

```bash
python src/utils/buildexe/build_exe.py
```

使用 PyInstaller 打包为独立 EXE，输出到 `dist/` 目录。

### 打包配置要点

- 入口文件：`app.py`
- `--windowed`：无控制台窗口
- `--add-data`：包含 `config/config.yaml`、`docs/banlist.txt`
- `--hidden-import`：paddleocr、cv2、yaml 等

### 系统要求

- Windows 10/11（64位）
- Python 3.9+
- 8GB RAM（推荐）
- NVIDIA GPU（可选，用于 GPU 加速）
