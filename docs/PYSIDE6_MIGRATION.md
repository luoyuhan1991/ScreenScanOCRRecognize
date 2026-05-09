# PySide6 UI 迁移方案

将主版本 GUI 从 tkinter 迁移到 PySide6，以 1:1 还原 `mockups/light_ui_prototype.html` 设计稿。

## 背景与决策

当前 `app.py` 使用 tkinter（含 ttk/scrolledtext）实现，约 1073 行。设计稿 `mockups/light_ui_prototype.html` 是浅色主题高保真原型（圆角、阴影、品牌色、卡片化侧栏 + 独立设置页）。三方案对比后选定 PySide6：

| 方案 | 还原度 | 改造量 | Overlay | 体积 | 选用 |
|---|---|---|---|---|---|
| CustomTkinter | 形似 | ~200 行 | 不动 | +5MB |  |
| **PySide6** | **神似（QSS≈CSS）** | **~800–1200 行** | **顺势重写更优雅** | **+60–80MB** | **是** |
| pywebview/Flet | 神似（直接用 HTML） | ~1500 行 + 桥 | Windows 透明窗有坑 | +50–150MB |  |

核心理由：PySide6 是唯一能 1:1 还原 mockup 的方案，pipeline / matcher / config / hotkey 全部不动，重构面积可控；overlay 重写是净改善（摆脱 `#010101` 魔法色，用真 alpha 通道）。

## 架构

- **单 `QMainWindow`** + 左侧 sidebar (`QListWidget`) + 右侧 `QStackedWidget`，三页：扫描 / 设置 / 关于
- **系统 titlebar**（不自绘 min/max/close），mockup 里独立"设置窗口"的装饰条不复用
- **扫描页** = 配置面板（4 个 group）+ 启动按钮 + 日志区 + 状态栏
- **设置页** = `QScrollArea` + 5 张卡（其中"热键设置"整卡 disabled + 占位）
- **关于页** = 静态 logo / 版本 / 致谢
- **pipeline / matcher / hotkey / config 大体复用**：`capture.py` 加 1 行读 `enable_roi`；`defaults.py` 新增/重命名若干键；其他文件不动。`OCRStage` 保持纯 Python 无 Qt 依赖（CLI 也用）。Overlay 算法移植到 PySide6 重写（数据结构与音效逻辑保留，渲染层换 Qt）

## 目录结构

```
ScreenScanOCRRecognize/
├── app.py                       # 重写：~50 行启动入口（QApplication + 加载 qss）
├── ui/                          # 新增：所有 PySide6 代码集中于此
│   ├── __init__.py
│   ├── main_window.py           # QMainWindow 装载 sidebar + stacked
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── scan_page.py         # 扫描页：装载 config_panel + log_panel + status_bar
│   │   ├── settings_page.py     # 设置页：QScrollArea + 5 张 settings_card
│   │   └── about_page.py        # 关于页：版本 / 作者 / 依赖致谢
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── sidebar.py           # 自绘 QListWidget（icon + 文案）
│   │   ├── config_panel.py      # 4 个 group：扫描区域 / 节奏 / OCR / 关键词匹配 + 启动按钮
│   │   ├── log_panel.py         # QPlainTextEdit + 颜色规则（DEBUG/INFO/WARNING/ERROR）
│   │   └── status_bar.py        # 4 字段：运行状态 / 内存 / 版本 / 引擎
│   ├── overlay.py               # PySide6 重写浮窗（QWidget + 真 alpha）
│   ├── tray.py                  # QSystemTrayIcon
│   ├── log_bridge.py            # logging.Handler → Signal → log_panel
│   └── styles/
│       └── light.qss            # 从 mockup CSS 翻译而来
├── shared/
│   ├── matcher.py               # 不动
│   └── overlay.py               # 保留（old_version 仍依赖）
├── src/pipeline/                # 完全不动
├── src/utils/                   # 完全不动
├── src/config/                  # 完全不动
├── defaults.py                  # 新增 APP_VERSION 常量 + 'app' 键（minimize_to_tray / startup_mode）
└── config/config.yaml           # 不动
```

## 扫描页（主战场）

mockup 主窗口右侧 = `scan_page.py` 装载：

| 区块 | widget | 控件 | 接 config |
|---|---|---|---|
| 扫描区域 | config_panel | 启用 ROI / 记住区域 / ROI 预设 select / 保存当前按钮 | `scan.enable_roi` / `scan.remember_roi` / `scan.roi_presets`（见下方注） |
| 扫描节奏 | config_panel | 扫描间隔 slider (0.5–10s) | `scan.interval_seconds` |
| OCR 识别 | config_panel | 语言 select / GPU 加速 toggle / 最小置信度 slider | `ocr.language` / `gpu.enabled` / `ocr.min_confidence` |
| 关键词匹配 | config_panel | 词库文件 row（input + 浏览 + 编辑）/ 显示时长 slider | `files.banlist_file` / `matching.display_duration` |
| Action | config_panel | 开始扫描 / 停止扫描 大按钮 + 热键提示 | — |
| 日志 | log_panel | QPlainTextEdit + 着色 + 清空按钮 | — |
| 状态 | status_bar | 4 字段，详见下文 | — |

**ROI 键语义重构**（行为变更，迁移期一次性完成）：

现版 `scan.roi` 一键双义（None=禁用，coords=启用）。本次拆为：

- **`scan.roi_rect`**（重命名自 `scan.roi`）—— 只承载坐标 `[x1,y1,x2,y2]`，可为 None
- **`scan.enable_roi`**（升级为真开关）—— `capture.py` 加一行 `if not config.get('scan.enable_roi'): roi = None`，`enable_roi` 成为 ROI 是否生效的唯一权威

GUI 行为：toggle 只控 `enable_roi`；选预设 / 保存预设只动 `roi_rect` / `roi_presets`；两键完全解耦。

**ROI 数据流 + 边界规约**：

```
GUI / CLI 启动时：
  if config.get('scan.enable_roi'):
      roi = config.get('scan.roi_rect')
      if roi is None:
          logger.warning('enable_roi=True 但 roi_rect 未设置，本次回退全屏')
          roi = None
  else:
      roi = None
  pipeline.set_roi(roi)

capture.py.grab(roi=...)：
  # 防御性二次校验
  if not config.get('scan.enable_roi'):
      roi = None
  # 后续按 roi 是否为 None 走 ROI / 全屏分支
```

`enable_roi=True && roi_rect=None` 的边界：**不报错**，回退全屏 + warn 日志一次。GUI 此时应在 ROI 区域块灰一行提示"未设置 ROI 坐标，当前为全屏扫描"，但不强制 disable toggle（保留用户随时切换的自由）。

**重命名波及面**（迁移期同步改，截至本文档落档时**尚未执行**）：

| 文件 | 残留 `scan.roi` 引用数 |
|---|---|
| `defaults.py` | 1（line 28）|
| `app.py` | 4（lines 522/579/664/684 — 被新版替换前需保持现 tk 能跑） |
| `cli.py` | 1（line 21）|
| `old_version/app.py` | 4（lines 642/645/657）|
| `old_version/cli.py` | 0（grep 后只有 `roi_padding`）|
| `old_version/src/core/scan_service.py` | 间接引用（通过 `self.roi`）|

**阶段 3a 必须把这 6 个文件一次性改完，否则现版 tk + 新版 PySide6 会读不同的 key 互相打架**。

**ROI 预设 select 行为约定**：
- 下拉项 = `scan.roi_presets`（dict）的 keys；defaults 内置 `'4+2': [1170, 256, 1880, 843]`
- 选中后把对应 value 写到 `scan.roi_rect`
- **不持久化"当前选中的预设名"**——重启后下拉回到默认项；避免新增 `scan.current_preset` 键

## 设置页（5 卡）

| 卡 | 控件 | config 键 | 状态 |
|---|---|---|---|
| 常规设置 | 最小化到托盘 toggle | `app.minimize_to_tray`（**新键，默认 true**） | active |
| | 启动后默认状态 select（暂停扫描 / 自动开始） | `app.startup_mode`（**新键，string 枚举 `'paused'` / `'auto'`，默认 `'paused'`**） | active |
| 扫描配置 | 帧差阈值 slider (0–20) | `scan.diff_threshold` | active |
| 浮窗提示 | 字号 slider (10–48) | `matching.font_size` | active |
| | 位置 select（居中 / 顶部 / 底部） | `matching.position` | active |
| | 音效提醒 toggle | `matching.enable_sound` | active |
| 热键设置 | 开始/停止热键编辑 + 恢复默认 | — | **disabled + "敬请期待"**（见注） |
| 配置管理 | 重置全部配置 button | — | active |

**关于"热键设置"卡 disabled**：mockup 该卡视觉是正常可交互的（kbd 显示当前热键 + 编辑笔图标 + "恢复默认"链接 + "保存默认"按钮），并未标 disabled。本方案为节省工时**主动收窄 scope**——热键编辑涉及全局钩子重注册、冲突检测、按键序列录制等边界情况，单独迭代更稳。

**重置配置实现**（前置：`config.load()` 必须已调用过——`MainWindow.__init__` 阶段已满足）：

```python
import copy
from defaults import DEFAULT_CONFIG

def reset_to_defaults():
    config._data = copy.deepcopy(DEFAULT_CONFIG)
    config.save()
    main_window.reload_all_widgets_from_config()  # 触发各 widget 从 config 重读
```

直写 `_data` 是有意为之——走 `config.set('scan', dict)` 在顶层 key 时会触发"按子树覆盖"（参 `Config.set` 方法），但 walker 写到叶子又啰嗦；而"重置全部配置"语义本就是清空所有用户改动，直接整块替换最干净。`Config._loaded` 标志不需复位，因为紧跟的 `save()` 已把 `_data` 同步回 yaml，下次 `get()` 读到的就是 defaults。

**告知**：重置会清空所有用户自定义，包括 `scan.roi_presets` 里用户保存的预设、`scan.roi_rect` 里当前 ROI、关键词文件路径等——`QMessageBox` 二次确认时必须明文提示"会清空所有自定义预设和 ROI 坐标"。

**新增 config 键**（写入 `defaults.py` 的 `DEFAULT_CONFIG`）：

```python
'app': {
    'minimize_to_tray': True,
    'startup_mode': 'paused',  # 'paused' | 'auto'
}
```

旧 yaml 缺这两个键时由 `Config` 深合并兜底。

## 状态栏

```
左：● 运行状态：[运行中 / 已暂停 / 初始化中]   内存占用：XX.X MB
右：版本：1.0.0  |  引擎：PaddleOCR 3.x
```

| 字段 | 来源 |
|---|---|
| 运行状态 | `MainWindow.is_running` 状态推断（pipeline 启停时刷新） |
| 内存占用 | 搬现版 `_get_memory_mb()`，`QTimer(5000)` 每 5s 刷新 |
| 版本 | `defaults.APP_VERSION = "1.0.0"`（新增常量） |
| 引擎 | OCR 初始化前显示"引擎：加载中"；初始化由 worker QThread 跑，完成后 worker 自己 `import paddleocr; ver = paddleocr.__version__`，通过 Signal 推给状态栏，格式 `f"PaddleOCR {ver.split('.')[0]}.x"`。**`OCRStage` 类本身保持纯 Python 无 Qt 依赖**（CLI 也用它） |

## 关于页

```
[扫描图标] ScreenScanOCRRecognize
版本 1.0.0  ·  © 2026 yhluo9

GitHub: https://github.com/yhluo9/ScreenScanOCRRecognize

第三方依赖
  · PaddleOCR (Apache-2.0)
  · pyahocorasick (BSD-3)
  · PySide6 (LGPL-3)        ← 动态链接合规
  · keyboard / mss
```

`QVBoxLayout` 居中对齐，超链接 `QLabel.setOpenExternalLinks(True)`。

## Overlay 重写

新建 `ui/overlay.py`，用 `QWidget` 实现，移植 `shared/overlay.py` 的所有数据逻辑（左列累计匹配、右列本次 OCR、新匹配音效）：

```python
self.setAttribute(Qt.WA_TranslucentBackground)        # 真 alpha 通道
self.setWindowFlags(
    Qt.FramelessWindowHint
    | Qt.WindowStaysOnTopHint
    | Qt.Tool
    | Qt.WindowTransparentForInput                    # 鼠标穿透（替代手写 Win32）
)
```

- 用 `paintEvent` + `QPainter` 绘制带阴影文字
- `QTimer.singleShot(duration*1000, self.hide)` 替代 tkinter `after`
- C 大三和弦 WAV 不变，`winsound.PlaySound(SND_MEMORY)` 直接复用

`shared/overlay.py` 文件**保留**（`old_version/` 仍依赖），新 overlay 独立放在 `ui/overlay.py`。

## 5 阶段迁移计划

每阶段独立可运行，便于独立 commit / 回滚。

### 阶段 1：启动骨架（0.5 天）

- 安装 PySide6（`pip install PySide6`）
- 写 `app.py`：`QApplication` + 加载 `light.qss` + 显示 `MainWindow`
- `ui/main_window.py`：sidebar (`QListWidget`) + `QStackedWidget` 装三个空白页
- 从 mockup `:root` 提取色板，写第一版 `ui/styles/light.qss`

**验证**：能打开窗口，sidebar 能切换三页，背景/前景/边框颜色与 mockup 一致。

### 阶段 2：扫描页（2 天，主战场）

- `ui/widgets/config_panel.py` — 4 个 group + 启动按钮（CSS→QSS 占大头）
- `ui/widgets/log_panel.py` — `QPlainTextEdit` + 颜色规则
- `ui/widgets/status_bar.py` — 4 字段 + `QTimer` 刷新内存
- 控件双向绑定 `config` 单例（`config.get(...)` 初始化、`valueChanged` 写回 `config.set(...)` + `config.save()`）
- 在 `defaults.py` 加 `APP_VERSION` 与 `app.*` 默认键

**验证**：所有控件可见可交互，改动能持久化到 `config/config.yaml`，状态栏内存数字 5s 刷新一次。

### 阶段 3a：pipeline 接入（1 天）

- 把 `ScanPipeline` 实例化挪到 `MainWindow.__init__`
- 用 `QThread` 跑扫描循环（替代当前 `threading.Thread + Event`）；worker 暴露：

  ```python
  class ScanWorker(QObject):
      init_done = Signal(str)        # 参数 = PaddleOCR 版本字符串，OCR init 完成时发射
      result_ready = Signal(object)  # 参数 = ScanResult，每次 scan_once 完成时发射
      log_message = Signal(str, str) # 参数 = (level, message)，作为 logging.Handler 的桥
  ```

  `init_done` 会同时连接：状态栏「引擎」字段 slot + auto 启动 hook（见 3b）
- 日志走新的 `ui/log_bridge.py`：`logging.Handler` → `worker.log_message` Signal → `LogPanel`
- ROI 重命名 + 解耦（**6 处文件必须一次性改完**，见上文「重命名波及面」表）：把 `scan.roi` 改成 `scan.roi_rect`；`capture.py` 加一行 `if not config.get('scan.enable_roi'): roi = None`
- **3a 阶段无浮窗能力**——老 `shared/overlay.py` 是 tkinter 实现，无法挂到 Qt 主循环；浮窗到阶段 4 才回来。GUI 里相关代码先写 `OverlayStub`：

  ```python
  class OverlayStub:
      """阶段 3a 占位实现，全部 no-op + debug 日志，方法签名与 shared/overlay.Overlay 完全一致。"""
      def setup(self): pass
      def update(self, ocr_results, matches):
          if matches: logger.debug(f'[stub overlay] matches={[m["keyword"] for m in matches]}')
      def hide(self): pass
      def clear_session(self): pass
      def destroy(self): pass
  ```

**验证**：能完整跑 OCR 流程，启动/停止按钮正常；状态栏能显示运行状态、内存、引擎版本；日志着色与现版一致；ROI toggle off 时确实跑全屏 OCR；命中关键词只在日志里看到（无浮窗，由 stub 行为决定）。

### 阶段 3b：设置页 + 关于页（1 天）

- `ui/pages/settings_page.py` — 5 张卡（其中"热键设置"整卡 `setEnabled(False)` + 灰底"敬请期待"）
- `ui/pages/about_page.py` — 静态布局
- "重置配置"按钮走 `config._data = copy.deepcopy(DEFAULT_CONFIG); config.save(); reload_all_widgets_from_config()`，弹 `QMessageBox` 二次确认（明文提示"会清空所有自定义预设和 ROI"）
- "启动后默认状态"接入：`app.startup_mode='auto'` 时**连接 `ScanWorker.init_done` Signal**（3a 已定义，签名 `Signal(str)`），slot 内调用扫描启动；不在 `MainWindow.__init__` 调用——否则 UI 卡在"初始化中"且 pipeline 还没 ready

**验证**：切到设置页改字号/帧差阈值能立即生效；重置配置能把 yaml 还原到出厂值并刷新 UI；改 `startup_mode='auto'` 重启后等 OCR 加载完自动开扫。

### 阶段 4：Overlay 重写（1 天）

- `ui/overlay.py` 用 `QWidget` + `WA_TranslucentBackground` 实现真 alpha
- 移植 `shared/overlay.py` 的左右双列布局算法（`paintEvent`）
- 移植 C 大三和弦音效（`winsound` 不变）
- `MainWindow` 切换持有的 overlay 实例为新版

**验证**：视觉/行为与原 overlay 一致；关键词颜色不再受 `#010101` 限制。

### 阶段 5：托盘 + 收尾（0.5 天）

- `QSystemTrayIcon` 替代 `pystray`（少一个依赖）
- 接入"最小化到托盘"配置项
- `HotkeyManager`（`keyboard` 库）完全不动，只把回调改成发 `Signal`
- 更新 `gui.bat` 启动入口
- 删除 `app.py` 旧 tkinter 代码
- pyproject / requirements.txt 加 `PySide6`，删 `pystray` / `Pillow`（如果只用于托盘图标）

**验证**：全功能等价于现 `app.py`，可替换 `gui.bat` 入口；冷启动 + 内存占用记录基线。

## 关键风险与应对

| 风险 | 应对 |
|---|---|
| QSS 不支持 CSS `box-shadow` | 用 `QGraphicsDropShadowEffect` 给关键卡片加阴影 |
| QSS 不支持 `transition` 动画 | 必要处用 `QPropertyAnimation`，否则放弃 hover 过渡 |
| QSS `:hover` 嵌套不如 CSS 灵活 | 把复杂选择器拆成显式 class（`setProperty("class", "primary")` + `style()->polish()`） |
| 日志吞吐过大 | `QPlainTextEdit.setMaximumBlockCount(10000)` 自动截首 |
| 阶段 1–3 期间主分支可能有改动 | 在 `feature/light_ui` 之上新开 `feature/pyside6` 分支，每阶段 rebase 一次 |
| LGPL 合规 | PySide6 用 LGPL，确保动态链接（不要 PyInstaller `--onefile` 静态打包 Qt 库） |
| 重置配置误触 | `QMessageBox` 二次确认 + 提示"不可撤销" |

## 性能影响（已评估）

UI 框架不影响 OCR/截图主路径（pipeline 在工作线程跑）。PySide6 渲染优于 tkinter（Qt 原生，GPU 合成），`QPlainTextEdit` 比 tkinter `ScrolledText` 更扛日志吞吐。冷启动从 <1s 增至 1–2s，内存 +60–80MB——对桌面工具完全可接受。

## 不在本方案范围内

- `old_version/` 仍用 tkinter，**只做 `scan.roi` → `scan.roi_rect` 的机械重命名**（约 5 处），其他逻辑不动
- `shared/overlay.py` 保留（`old_version/` 仍依赖），新 overlay 独立放在 `ui/overlay.py`
- `src/config/` / `src/utils/` / `shared/matcher.py` 完全不动
- `src/pipeline/`：仅 `capture.py` 加 1 行读 `enable_roi`；`OCRStage` 不动
- `defaults.py`：新增 `APP_VERSION` 常量、`app.*` 默认键、`'4+2'` 内置 ROI 预设；rename `'roi'` → `'roi_rect'`
- 暗色主题（如需，后续基于同一 `light.qss` 派生 `dark.qss`）
- 热键编辑（mockup 卡留位但 disabled，后续单独迭代）
- OCR 图像反色（mockup 已删除，主版本无此功能）
- CLI（`cli.py`）不动

## 工作量估算

| 阶段 | 工时 |
|---|---|
| 1. 启动骨架 | 0.5 天 |
| 2. 扫描页 | 2 天 |
| 3a. pipeline 接入 | 1 天 |
| 3b. 设置页 + 关于页 | 1 天 |
| 4. Overlay 重写 | 1 天 |
| 5. 托盘 + 收尾 | 0.5 天 |
| **合计** | **6 天** |
