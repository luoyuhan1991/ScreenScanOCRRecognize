# PySide6 UI 迁移方案

将主版本 GUI 从 tkinter 迁移到 PySide6，以 1:1 还原 `mockups/light_ui_prototype.html` 设计稿。

## 背景与决策

当前 `app.py` 使用 tkinter（含 ttk/scrolledtext）实现，约 1073 行。设计稿 `mockups/light_ui_prototype.html` 是 1982 行精致 CSS 原型（圆角、阴影、品牌色、卡片化侧栏）。三方案对比后选定 PySide6：

| 方案 | 还原度 | 改造量 | Overlay | 体积 | 选用 |
|---|---|---|---|---|---|
| CustomTkinter | 形似 | ~200 行 | 不动 | +5MB |  |
| **PySide6** | **神似（QSS≈CSS）** | **~800–1200 行** | **顺势重写更优雅** | **+60–80MB** | **是** |
| pywebview/Flet | 神似（直接用 HTML） | ~1500 行 + 桥 | Windows 透明窗有坑 | +50–150MB |  |

核心理由：PySide6 是唯一能 1:1 还原 mockup 的方案，pipeline/matcher/config/hotkey 全部不动，重构面积可控；overlay 重写是净改善（摆脱 `#010101` 魔法色，用真 alpha 通道）。

## 目录结构

```
ScreenScanOCRRecognize/
├── app.py                    # 重写：~50 行启动入口（QApplication + 加载 qss）
├── ui/                       # 新增：所有 PySide6 代码集中于此
│   ├── __init__.py
│   ├── main_window.py        # MainWindow 主窗口骨架（替代 MainGUI 类）
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── scan_panel.py     # 扫描配置面板（ROI/GPU/间隔/语言/置信度）
│   │   ├── match_panel.py    # 匹配配置面板（关键词/时长/位置/字号）
│   │   └── log_panel.py      # 日志显示（QPlainTextEdit）
│   ├── overlay.py            # 新版浮窗（QWidget + 真 alpha）
│   ├── tray.py               # QSystemTrayIcon 托盘
│   ├── log_bridge.py         # QThread + Signal 日志泵
│   └── styles/
│       └── light.qss         # 从 mockup CSS 翻译而来
├── shared/
│   ├── matcher.py            # 不动
│   └── overlay.py            # 保留（old_version 仍依赖）
├── src/pipeline/             # 完全不动
├── src/utils/                # 完全不动
├── src/config/               # 完全不动
├── defaults.py               # 不动
└── config/config.yaml        # 不动
```

## 5 阶段迁移计划

每阶段独立可运行，便于独立 commit / 回滚。

### 阶段 1：启动骨架（0.5 天）

- 安装 PySide6（`pip install PySide6`）
- 写 `app.py`：`QApplication` + 加载 `light.qss` + 显示 `MainWindow`
- `ui/main_window.py`：空 `MainWindow`，标题栏 + 占位中央区域
- 从 mockup `:root` 提取色板，写第一版 `ui/styles/light.qss`

**验证**：能打开窗口，背景/前景/边框颜色与 mockup 一致。

### 阶段 2：三个 panel 翻译（2–3 天）

按 mockup 翻译三个面板（CSS→QSS 占大头）：

- `ui/panels/scan_panel.py` — ROI 选择 / GPU 开关 / 扫描间隔 / OCR 语言 / 置信度阈值
- `ui/panels/match_panel.py` — 关键词文件 / 显示时长 / 位置 / 字号 / 声音开关
- `ui/panels/log_panel.py` — `QPlainTextEdit` + 颜色规则（DEBUG/INFO/WARNING/ERROR）

控件双向绑定 `config` 单例（`config.get(...)` 初始化、`valueChanged` 写回 `config.set(...)` + `config.save()`）。

**验证**：所有控件可见可交互，改动能持久化到 `config/config.yaml`。

### 阶段 3：pipeline 接入（1 天）

- 把 `ScanPipeline` 实例化挪到 `MainWindow.__init__`
- 用 `QThread` 跑扫描循环（替代当前 `threading.Thread + Event`）
- 用 `Signal` 把 `ScanResult` 传回主线程更新 UI
- 日志走新的 `ui/log_bridge.py`：`logging.Handler` → `Signal` → `LogPanel`

**验证**：能完整跑 OCR 流程，启动/停止按钮正常，日志着色与现版一致。

### 阶段 4：Overlay 重写（1 天）

新建 `ui/overlay.py`，用 `QWidget` 实现：

```python
self.setAttribute(Qt.WA_TranslucentBackground)        # 真 alpha 通道
self.setWindowFlags(
    Qt.FramelessWindowHint
    | Qt.WindowStaysOnTopHint
    | Qt.Tool
    | Qt.WindowTransparentForInput                    # 鼠标穿透（替代手写 Win32）
)
```

- 移植 `shared/overlay.py` 的布局算法（左列累计匹配、右列本次 OCR）
- 移植 C 大三和弦音效（`winsound` 不变）
- 用 `paintEvent` + `QPainter` 绘制文字（带阴影）
- `QTimer.singleShot(duration*1000, self.hide)` 替代 tkinter 的 `after`

**验证**：视觉/行为与原 overlay 一致；关键词颜色不再受 `#010101` 限制。

### 阶段 5：托盘 + 收尾（0.5 天）

- `QSystemTrayIcon` 替代 `pystray`（少一个依赖）
- `HotkeyManager`（`keyboard` 库）完全不动，只把回调改成发 `Signal`
- 更新 `gui.bat` 启动入口
- 删除 `app.py` 旧 tkinter 代码

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

## 性能影响（已评估）

UI 框架不影响 OCR/截图主路径（pipeline 在工作线程跑）。PySide6 渲染优于 tkinter（Qt 原生，GPU 合成），`QPlainTextEdit` 比 tkinter `ScrolledText` 更扛日志吞吐。冷启动从 <1s 增至 1–2s，内存 +60–80MB——对桌面工具完全可接受。

## 不在本方案范围内

- `old_version/` 全部不动，仍用 tkinter
- `shared/overlay.py` 保留（`old_version/` 仍依赖），新 overlay 独立放在 `ui/overlay.py`
- `defaults.py` / `src/config/` / `src/pipeline/` / `src/utils/` / `shared/matcher.py` 全部复用，重构 0 行
- 暗色主题（如需，后续基于同一 `light.qss` 派生 `dark.qss`）

## 工作量估算

| 阶段 | 工时 |
|---|---|
| 1. 启动骨架 | 0.5 天 |
| 2. 三个 panel | 2–3 天 |
| 3. pipeline 接入 | 1 天 |
| 4. Overlay 重写 | 1 天 |
| 5. 托盘 + 收尾 | 0.5 天 |
| **合计** | **5–6 天** |
