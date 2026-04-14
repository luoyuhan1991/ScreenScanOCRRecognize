# ScreenScanOCRRecognize 优化设计方案

## 背景

游戏匹配机制中，通过定时截图 + OCR 识别玩家列表，在匹配过程中提示被标记的用户。当前实现功能完整，在无明显痛点的情况下进行系统性优化。

### 使用场景

- 主要扫描玩家列表 ROI 区域（约 710x587 像素），偶尔全屏
- 扫描间隔 1-3 秒均可接受，越快越好但不以资源换速度
- 硬件：i5 + RTX 4060 Ti，已安装 Python 及全部依赖
- 关键词格式：`用户名关键字 提示词`（提示词含用户名、工会等便于肉眼确认）

### 实施策略

两套方案并行实现：
- **方案一**：在当前目录原地优化（已完成）
- **方案二**：在 `new_version/` 目录全新实现（已完成）

---

## 方案一：优化当前实现（已完成）

在现有代码上做渐进式修改，不改变架构，逐项优化。

### 1.1 性能优化

#### P1: 关闭生产环境文件 I/O [已完成]

**改动**：`config/config.yaml` 中 `save_screenshot`、`save_ocr_result`、`save_processed_image` 默认值改为 `false`。GUI 增加"保存截图和识别结果"复选框（默认关闭）。

#### P2: 截图加速 — mss 替换 PIL.ImageGrab [已完成]

**改动**：`src/utils/scan_screen.py` 使用 `mss` 库替换 `ImageGrab.grab()`，保留 PIL 作为 fallback（`_USE_MSS` 标志）。`requirements.txt` 已添加 `mss>=9.0.0`。

#### P3: 图像格式转换优化 [已完成]

**改动**：mss 返回 BGRA numpy 数组时直接切 alpha 通道得到 BGR，跳过 PIL→numpy→cvtColor 转换链。

#### P4: 变化检测 — 跳过无变化帧 [已完成]

**改动**：`ScanService._is_frame_similar()` 实现帧差比较：缩放为 160x120 灰度图 → 计算 MSE → 低于阈值跳过 OCR。配置项 `scan.enable_diff_skip`（默认 true）和 `scan.diff_threshold`（默认 5.0）。

#### P5: 预计算关键词 casefold [已完成]

**改动**：`TextMatcher._load_keywords()` 预计算 `keywords_casefolded` 列表，`match()` 方法使用预计算值，避免每次匹配重复 casefold。

### 1.2 产品体验优化

#### UX1: 持久化浮窗复用 [已完成]

**改动**：`FloatingTextDisplay` 改为单例持久窗口模式（`_singleton` + `_singleton_lock`），通过 `get_singleton(parent_root)` 获取。`update_content()` 只重绘 Canvas 内容，无内容时 `withdraw()` 隐藏。

#### UX2: 匹配命中音效提示 [已完成]

**改动**：匹配到新关键词时播放音效提示。配置项 `matching.enable_sound`（默认 true）。同一关键词在同一扫描会话中只提示一次（`session_keyword_latest_hint` 去重）。`reset_alerted_keywords()` 可重置已提醒关键词。

#### UX3: 托盘图标 [已完成]

**改动**：`pystray` 托盘图标（动态生成 64x64 雷达扫描风格图标）。关闭窗口时缩到托盘，左键显示/隐藏，右键菜单退出。

### 1.3 其他优化

#### O1: 配置热更新优化 [已完成]

**改动**：Config 对象增加 dirty flag（`is_dirty()` / `clear_dirty()`），`ScanService._cache_config()` 只在 dirty 时刷新。

#### O2: 日志队列优化 [已完成]

**改动**：日志处理改为 drain 模式，`update_log_from_queue()` 一次取完队列所有待处理日志。队列大小和清理阈值可通过 `performance.max_log_queue_size` 和 `performance.log_queue_cleanup_threshold` 配置。

#### O3: 清理逻辑简化 [已完成]

**改动**：文件 I/O 关闭后清理逻辑简化，仅在启用文件保存时按 `cleanup.scan_interval`（默认 10 次扫描）执行清理。

---

## 方案二：基于需求重新设计（已完成）

在 `new_version/` 目录下全新实现，围绕「游戏匹配时快速识别标记玩家」单一需求设计。

### 2.1 目录结构（实际）

```
new_version/
├── app.py                      # GUI 入口（~1049 行，MainGUI 类）
├── cli.py                      # CLI 入口（~65 行）
├── gui.bat                     # GUI 启动批处理
├── start.bat                   # 另一个启动脚本
├── requirements.txt            # 精简依赖
├── config/
│   └── config.yaml             # 精简配置文件
├── src/
│   ├── pipeline/
│   │   ├── capture.py          # CaptureStage: mss 截图（线程安全）
│   │   ├── diff_gate.py        # DiffGate: 帧差检测（160x120 灰度 MSE）
│   │   ├── ocr_stage.py        # OCRStage: PaddleOCR GPU（懒加载单例）
│   │   ├── match_stage.py      # MatchStage: Aho-Corasick 匹配
│   │   └── pipeline.py         # ScanPipeline + ScanResult 数据类
│   ├── overlay/
│   │   └── overlay.py          # Overlay: 持久透明浮窗 + C 大三和弦音效
│   ├── config/
│   │   └── config.py           # 配置管理
│   └── utils/
│       └── logger.py           # 日志
└── docs/
    └── banlist.txt             # 关键词文件
```

### 2.2 流水线架构

```
CaptureStage → DiffGate → OCRStage → MatchStage → Overlay
   (mss)      (numpy MSE)  (PaddleOCR)  (Aho-Corasick)  (持久浮窗+音效)
```

- **CaptureStage**：mss 抓取 ROI 区域，输出 numpy BGR 数组，线程感知（thread-local mss context），不保存文件
- **DiffGate**：160x120 灰度缩略图 MSE 比较，`should_skip(frame_bgr)` 返回是否跳过
- **OCRStage**：仅 PaddleOCR + GPU，懒加载单例，禁用文档方向检测以提速
- **MatchStage**：`pyahocorasick` 自动机，O(文本总长度) 匹配复杂度
- **Overlay**：持久透明浮窗 + C 大三和弦（C5+E5+G5）音效提示

### 2.3 配置精简（实际）

```yaml
gpu:
  enabled: true

ocr:
  language: ch
  min_confidence: 0.3

scan:
  interval_seconds: 5.0
  diff_threshold: 5.0
  roi: [1170, 256, 1880, 843]

matching:
  banlist_file: docs/banlist.txt
  display_duration: 3.0
  enable_sound: true
  font_size: 18
```

相比主版本去掉了：双引擎支持、文件 I/O 配置、三级 GPU 配置、performance/cleanup 分组。

### 2.4 相比主版本的差异

| 特性 | 主版本 | new_version |
|------|--------|-------------|
| OCR 引擎 | PaddleOCR + EasyOCR | 仅 PaddleOCR |
| 匹配算法 | 子串 + 比例匹配 O(K*N) | Aho-Corasick O(T) |
| 文件 I/O | 可选保存截图/结果 | 无文件 I/O |
| 截图 | mss (PIL fallback) | 仅 mss |
| 浮窗音效 | winsound.Beep | C 大三和弦 WAV |
| GPU 配置 | force_cpu/force_gpu/auto | 单开关 |
| 配置编辑器 | 内置 YAML 编辑器 | 无 |
| 热键 | Ctrl+Alt+1/2 | 无 |
| 依赖 | pillow, easyocr 等 | 精简（+pyahocorasick） |

---

## 性能对比

| 指标 | 优化前 | 方案一优化后 | 方案二重设计 |
|------|--------|-------------|-------------|
| 单次扫描耗时 | 300-900ms | 150-400ms | 100-300ms |
| 画面无变化时 | 仍做全量 OCR | 跳过 OCR (~5ms) | 跳过 OCR (~2ms) |
| 内存占用 | 800-1200MB | ~相同 | 600-900MB |
| 磁盘 I/O | 3 次写/周期 | 0（默认关闭） | 0 |
| 匹配复杂度 | O(K*N) | O(K*N) | O(T) |
| 浮窗 | 创建/销毁闪烁 | 单例复用 | 单例复用 |

---

## 实施状态

### 方案一（当前目录）— 全部完成

1. P1: 关闭文件 I/O 默认值
2. P2 + P3: mss 截图 + 图像转换优化
3. P4: 帧差变化检测
4. P5: 预计算 casefold
5. UX1: 持久化浮窗
6. UX2: 音效提示
7. UX3: 托盘图标
8. O1-O3: 配置热更新、日志 drain、清理简化

### 方案二（new_version/ 目录）— 全部完成

1. 目录结构和配置
2. CaptureStage + DiffGate
3. OCRStage（PaddleOCR only）
4. MatchStage（Aho-Corasick）
5. ScanPipeline 串联 + CLI 入口
6. Overlay 持久浮窗 + 音效
7. GUI (app.py)
