# ScreenScanOCRRecognize 优化设计方案

## 背景

游戏匹配机制中，通过定时截图 + OCR 识别玩家列表，在匹配过程中提示被标记的用户。当前实现功能完整，在无明显痛点的情况下进行系统性优化。

### 使用场景

- 主要扫描玩家列表 ROI 区域（约 710×587 像素），偶尔全屏
- 扫描间隔 1-3 秒均可接受，越快越好但不以资源换速度
- 硬件：i5 + RTX 4060 Ti，已安装 Python 及全部依赖
- 关键词格式：`用户名关键字 提示词`（提示词含用户名、工会等便于肉眼确认）

### 实施策略

两套方案并行实现：
- **方案一**：在当前目录原地优化
- **方案二**：在 `new_version/` 目录全新实现

---

## 方案一：优化当前实现

在现有代码上做渐进式修改，不改变架构，逐项优化。

### 1.1 性能优化

#### P1: 关闭生产环境文件 I/O

**问题**：每次扫描 3 次磁盘写入（截图 PNG、处理后图像 PNG、OCR 结果 TXT），加上 glob 清理旧文件。

**改动**：
- `config/config.yaml`：`save_screenshot`、`save_ocr_result`、`save_processed_image` 默认值改为 `false`
- 预计提速 30-50ms/次

**涉及文件**：
- `config/config.yaml`

#### P2: 截图加速 — mss 替换 PIL.ImageGrab

**问题**：`ImageGrab.grab()` 基于 GDI，ROI 截图约 50-100ms。

**改动**：
- `src/utils/scan_screen.py`：用 `mss` 库替换 `ImageGrab.grab()`
- `mss` 直接返回 numpy 数组（BGRA），ROI 截图约 10-20ms
- 保留 PIL 作为 fallback（mss 未安装时）
- `requirements.txt`：添加 `mss>=9.0.0`

**涉及文件**：
- `src/utils/scan_screen.py`
- `requirements.txt`

#### P3: 图像格式转换优化

**问题**：`paddle_ocr.py:120` 每次做 PIL→numpy→cvtColor(RGB→BGR) 转换。

**改动**：
- 如果截图来自 mss（已经是 BGRA numpy 数组），直接切掉 alpha 通道得到 BGR，跳过所有转换
- 如果截图是 PIL Image，保留现有转换逻辑作为兼容路径

**涉及文件**：
- `src/core/ocr/paddle_ocr.py`

#### P4: 变化检测 — 跳过无变化帧

**问题**：游戏匹配等待时画面大部分时间不变，但每次都做全量 OCR。

**改动**：
- `src/core/scan_service.py`：增加帧差比较逻辑
- 将当前帧与上一帧做 numpy 差异计算（对灰度缩略图比较，<1ms）
- 差异低于阈值时跳过 OCR，直接复用上一次结果
- 新增配置项 `scan.enable_diff_skip`（默认 true）和 `scan.diff_threshold`（默认 0.02）

**涉及文件**：
- `src/core/scan_service.py`
- `config/config.yaml`

#### P5: 预计算关键词 casefold

**问题**：`text_matcher.py:199` 每次匹配对每个关键词调 `casefold()`。

**改动**：
- `TextMatcher._load_keywords()` 时预计算 casefolded 版本存储
- `keyword_in_text()` 接受预计算值，避免重复 casefold

**涉及文件**：
- `src/utils/text_matcher.py`

### 1.2 产品体验优化

#### UX1: 持久化浮窗复用

**问题**：每次扫描创建/销毁 Toplevel 窗口，闪烁且每次重设鼠标穿透。

**改动**：
- `FloatingTextDisplay` 改为持久窗口模式
- 新增 `update_content(text_lines)` 方法，只重绘 Canvas 内容
- 窗口穿透和属性只在首次创建时设置
- 无内容时隐藏窗口（`withdraw()`），有内容时显示（`deiconify()`）

**涉及文件**：
- `src/utils/text_matcher.py`

#### UX2: 匹配命中音效提示

**改动**：
- 匹配到新关键词时，通过 `winsound.Beep()` 或 `winsound.PlaySound()` 播放短音效
- 新增配置项 `matching.enable_sound`（默认 true）
- 同一关键词在同一扫描会话中只提示一次（通过 session_matched_records 去重）

**涉及文件**：
- `src/utils/text_matcher.py` 或 `app.py`（调用层）
- `config/config.yaml`

#### UX3: 托盘图标状态指示

**改动**：
- 托盘图标颜色反映状态：绿色=扫描中 / 灰色=暂停 / 红色=有匹配
- 利用现有 `pystray` 托盘模块，动态更换图标

**涉及文件**：
- `src/utils/tray_icon.py`
- `app.py`

### 1.3 其他优化

#### O1: 配置热更新优化

**改动**：Config 对象增加 dirty flag，`_cache_config()` 只在 dirty 时刷新。

**涉及文件**：
- `src/config/config.py`
- `src/core/scan_service.py`

#### O2: 日志队列优化

**改动**：日志处理从每次最多 10 条改为 drain 模式（一次取完队列所有待处理日志）。

**涉及文件**：
- `app.py`

#### O3: 清理逻辑简化

**改动**：P1 落地后，文件 I/O 关闭，清理逻辑可简化或移除。

**涉及文件**：
- `src/core/scan_service.py`

---

## 方案二：基于需求重新设计

在 `new_version/` 目录下全新实现，围绕「游戏匹配时快速识别标记玩家」单一需求设计。

### 2.1 目录结构

```
new_version/
├── app.py                      # GUI 入口
├── cli.py                      # CLI 入口
├── requirements.txt            # 精简依赖
├── config/
│   └── config.yaml             # 配置文件
├── src/
│   ├── pipeline/
│   │   ├── capture.py          # CaptureStage: mss 截图
│   │   ├── diff_gate.py        # DiffGate: 帧差检测
│   │   ├── ocr_stage.py        # OCRStage: PaddleOCR GPU
│   │   ├── match_stage.py      # MatchStage: Aho-Corasick 匹配
│   │   └── pipeline.py         # Pipeline: 串联各阶段
│   ├── overlay/
│   │   └── overlay.py          # 持久透明浮窗
│   ├── config/
│   │   └── config.py           # 配置管理
│   └── utils/
│       ├── logger.py           # 日志
│       └── hotkey.py           # 全局热键
└── docs/
    └── banlist.txt             # 关键词文件（格式兼容现有）
```

### 2.2 流水线架构

```
CaptureStage → DiffGate → OCRStage → MatchStage → OverlayStage
   (mss)      (numpy diff)  (PaddleOCR)  (Aho-Corasick)  (持久浮窗)
```

#### CaptureStage

- 使用 `mss` 抓取 ROI 区域，输出 numpy BGR 数组
- 不保存文件，不经过 PIL
- ROI 预设管理：支持保存/切换多组 ROI

#### DiffGate

- 将当前帧缩放为小尺寸灰度图（如 160×120），与上一帧做均方差比较
- 差异低于阈值：返回 `None`（短路后续阶段）
- 差异超过阈值：放行当前帧

#### OCRStage

- 仅 PaddleOCR + GPU，去掉 EasyOCR 分支
- 去掉文件 I/O（不保存处理后图像、不保存结果文件）
- 去掉 glob 清理逻辑
- 图像预处理精简：只保留可选的图像反色（基于配置，不每次自动检测）

#### MatchStage

- 使用 `pyahocorasick` 构建自动机
- 关键词加载时构建一次，文件变更时重建
- 匹配复杂度 O(文本总长度)，与关键词数量无关
- 返回匹配结果列表，每个结果包含关键词和对应提示词

#### Pipeline

```python
class ScanPipeline:
    def __init__(self, config):
        self.capture = CaptureStage(config)
        self.diff_gate = DiffGate(config)
        self.ocr = OCRStage(config)
        self.matcher = MatchStage(config)
    
    def scan_once(self) -> ScanResult:
        frame = self.capture.grab()
        if self.diff_gate.should_skip(frame):
            return self.last_result  # 复用上次结果
        ocr_texts = self.ocr.recognize(frame)
        matches = self.matcher.match(ocr_texts)
        self.last_result = ScanResult(ocr_texts, matches)
        return self.last_result
```

### 2.3 持久浮窗 Overlay

- 程序启动时创建一个透明、置顶、鼠标穿透的 Toplevel 窗口
- 内含一个 Canvas，所有内容通过 `canvas.delete('all')` + 重绘更新
- 布局：
  - 左侧：本局已匹配的玩家列表（累积显示，不随扫描周期消失）
  - 右侧：最新一次 OCR 结果（红色=匹配，绿色=未匹配）
- 无匹配且无 OCR 结果时自动 `withdraw()` 隐藏
- 新增匹配时可选播放音效

### 2.4 配置精简

```yaml
scan:
  interval_seconds: 2.0
  roi: [1170, 256, 1880, 843]
  roi_presets: {}             # 命名ROI预设
  diff_threshold: 0.02       # 帧差阈值

ocr:
  language: ch                # 单语言（PaddleOCR）
  min_confidence: 0.3
  enable_image_invert: false

gpu:
  enabled: true               # 简化：开或关

matching:
  banlist_file: docs/banlist.txt
  display_duration: 3.0
  position: center
  font_size: 18
  enable_sound: true

logging:
  level: INFO
```

去掉的配置项：
- `save_screenshot`、`save_ocr_result`、`save_processed_image`（无文件 I/O）
- EasyOCR 相关配置
- `force_cpu` / `force_gpu` / `auto_detect` 三级 GPU 配置（简化为单开关）
- `performance.*` 中的大部分项（架构本身已优化）

### 2.5 依赖精简

```
mss>=9.0.0
numpy>=2.2.0
opencv-python>=4.10.0
pyyaml>=6.0
paddleocr>=3.3.0
pyahocorasick>=2.0.0
keyboard>=0.13.5
pystray>=0.19.0
```

去掉：
- `pillow` — mss 直接输出 numpy，不需要 PIL
- `easyocr` — 只保留 PaddleOCR

### 2.6 GUI (app.py)

保留 tkinter GUI，但精简：
- 去掉 OCR 引擎选择（只有 PaddleOCR）
- 去掉文件保存相关控件
- 增加 ROI 预设管理 UI
- 增加匹配音效开关
- 保留：扫描间隔、置信度、匹配显示设置、热键、托盘、日志

### 2.7 预期性能

| 指标 | 当前实现 | 方案一优化后 | 方案二重设计 |
|------|---------|-------------|-------------|
| 单次扫描耗时 | 300-900ms | 150-400ms | 100-300ms |
| 画面无变化时 | 仍做全量 OCR | 跳过 OCR (~5ms) | 跳过 OCR (~2ms) |
| 内存占用 | 800-1200MB | ~相同 | 600-900MB |
| 磁盘 I/O | 3 次写/周期 | 0 | 0 |
| 匹配复杂度 | O(K×N) | O(K×N) | O(T) |
| 浮窗 | 创建/销毁闪烁 | 复用 | 复用 |
| 新增依赖 | — | mss | mss, pyahocorasick |
| 去掉依赖 | — | — | pillow, easyocr |

---

## 实施顺序

### 方案一（当前目录）

1. P1: 修改 config.yaml 默认值（关闭文件 I/O）
2. P2 + P3: mss 截图 + 图像转换优化
3. P4: 变化检测
4. P5: 预计算 casefold
5. UX1: 持久浮窗
6. UX2: 音效提示
7. UX3: 托盘状态
8. O1-O3: 其他优化

### 方案二（new_version/ 目录）

1. 搭建目录结构和配置
2. CaptureStage + DiffGate
3. OCRStage（PaddleOCR only）
4. MatchStage（Aho-Corasick）
5. Pipeline 串联 + CLI 入口
6. Overlay 持久浮窗
7. GUI (app.py)
8. 热键 + 托盘
