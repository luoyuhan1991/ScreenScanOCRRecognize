# UI 重设计——深色主题 + 多视图拆分

**日期：** 2026-05-08
**目标：** 把 `app.py`（当前 ~1264 行单文件、浅色 clam 主题、Notebook 双 tab）重写为深色主题 + 左侧 4 视图导航 + 新增匹配记录面板的多文件结构。
**范围：** 仅 GUI 层。`shared/`、`src/pipeline/`、`src/config/`、`src/utils/`、`cli.py`、`old_version/`、`config/config.yaml`、`gui.bat` 全部不动。

---

## 1. 整体布局

```
┌───────────────────────────────────────────────────────────────────┐
│ [✏ 屏幕扫描 OCR 识别系统]                          [─][□][×]      │
├───────────┬───────────────────────────────────────────────────────┤
│  ◎ 扫描   │  当前视图内容（4 个视图之一）                          │
│  ⚙ 设置   │                                                        │
│  ⌨ 热键   │                                                        │
│  ⓘ 关于   │                                                        │
│           │                                                        │
├───────────┴───────────────────────────────────────────────────────┤
│ ● 运行中  内存:83MB  版本:1.0.0  引擎:PaddleOCR 3.x               │
│   [开始扫描 Ctrl+Alt+1] [停止 Ctrl+Alt+2] [🔊声音提醒] [⚙重置配置]  │
└───────────────────────────────────────────────────────────────────┘
```

**三大区域：**

1. **Sidebar（约 90 px 宽）** —— 4 个图标+文字的纵向导航：扫描 / 设置 / 热键 / 关于。
2. **Content** —— 当前选中视图，占据中央剩余空间。
3. **Statusbar（约 56 px 高，可能 2 行）** —— 左对齐元信息（运行状态●、内存、版本、引擎）+ 右对齐操作（开始/停止/声音提醒/重置配置）。

**没有顶部 topbar**（旧版的状态卡 + 扫描次数 + 最近扫描 + 内存占用整排删除）。

## 2. 视图划分

| 视图 | 内容 |
|---|---|
| **扫描**（默认选中） | 简单/常用配置：扫描区域（启用 ROI / 记住 / ROI 预设 / 保存当前）、扫描节奏（间隔秒数）、OCR 识别（语言、GPU 加速、最小置信度）、关键词匹配（词库文件、显示时长）。**右侧并列两个面板：** 运行日志 + 匹配记录（最近 10 条）。 |
| **设置** | 高级配置：帧差检测阈值、浮窗外观（字号、位置、音效）、图像反色、日志级别、配置文件路径展示。 |
| **热键** | Phase 1 只读：展示当前热键（Ctrl+Alt+1 / Ctrl+Alt+2）+ 启用/禁用开关。改键放未来。 |
| **关于** | 项目名 + 版本号 + 引擎信息 + 简短说明 + GitHub 链接。 |

**扫描视图不嵌套内 tab**——侧栏导航本身已分组。旧版的"常用配置 / 高级"内 tab 完全去除。

## 3. 文件结构

```
ScreenScanOCRRecognize/
├── app.py                          # 入口（< 50 行）
├── src/gui/                        # ★ 新目录
│   ├── __init__.py
│   ├── theme.py                    # 深色色板 + 字体常量 + ttk style 配置
│   ├── main_window.py              # MainWindow：组装三大区 + 协调全局状态
│   ├── sidebar.py                  # Sidebar：4 个导航按钮
│   ├── statusbar.py                # StatusBar：底栏（状态/内存/版本/引擎 + 开始/停止/声音/重置）
│   ├── views/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseView：mount/unmount 钩子最小基类
│   │   ├── scan_view.py
│   │   ├── settings_view.py
│   │   ├── hotkey_view.py
│   │   └── about_view.py
│   └── widgets/
│       ├── __init__.py
│       ├── log_panel.py            # 运行日志面板（队列消费 + 颜色 tag）
│       ├── match_records.py        # 匹配记录面板（deque(10) + 时间 chip + ocr_text）
│       ├── roi_overlay.py          # 拖选 ROI 全屏窗
│       ├── roi_border.py           # 扫描时 ROI 红框可视化
│       └── tray.py                 # pystray 托盘图标
└── （shared/, src/pipeline/, src/utils/, src/config/, cli.py, old_version/ 等不动）
```

**拆分原则：**

- `main_window.py` 是协调者，持有 pipeline / overlay / hotkey_mgr / tray / log_queue / match_records / scan_thread / stop_event / 视图字典。
- 每个 View 是 `ttk.Frame` 子类；构造接收 `main_window` 引用以读 config 和回调全局动作。
- `widgets/` 放跨视图复用的小组件。
- `theme.py` 是常量 + 一个 `apply(root)` 函数，**不引入主题切换机制**。

**视图切换实现：**
`MainWindow` 持有 `self._views = {"scan": ScanView(...), ...}`，**全部预先实例化**。切换时 `self._current.pack_forget()` + `self._views[name].pack(...)`。Sidebar 的 `set_active(name)` 只更新选中态高亮。

## 4. 主题与色板

`src/gui/theme.py` 定义所有颜色与字体常量，并提供 `apply(root)` 一次性配好 ttk 全部 style。固定深色，**不支持切换**。

```python
UI_FONT = "Microsoft YaHei"
FONT_SIZE_BASE  = 9
FONT_SIZE_TITLE = 11

# 背景层
COLOR_BG_WINDOW     = "#0f1420"
COLOR_BG_SIDEBAR    = "#161b2a"
COLOR_BG_CONTENT    = "#0f1420"
COLOR_BG_CARD       = "#1a2235"
COLOR_BG_CARD_HOVER = "#222b40"
COLOR_BG_INPUT      = "#0a0f1a"

# 边框
COLOR_BORDER       = "#2a3245"
COLOR_BORDER_FOCUS = "#3a82f7"

# 文字
COLOR_TEXT       = "#e8ecf3"
COLOR_TEXT_DIM   = "#8a93a8"
COLOR_TEXT_MUTED = "#5a6478"

# 状态色
COLOR_PRIMARY       = "#3a82f7"
COLOR_PRIMARY_HOVER = "#4a92ff"
COLOR_DANGER        = "#e54848"
COLOR_DANGER_HOVER  = "#ff5858"
COLOR_SUCCESS       = "#22c55e"
COLOR_WARNING       = "#f59e0b"

# 日志颜色
COLOR_INFO_LOG  = "#60a5fa"
COLOR_DEBUG_LOG = "#9ca3af"
COLOR_ERROR_LOG = "#f87171"

# 时间 chip：bg = COLOR_SUCCESS, fg = "#0a1f12"
```

**注册的 ttk 样式：**
- 基础：`.TFrame / .TLabel / .TButton / .TCheckbutton / .TCombobox / .TEntry / .TScale`
- 派生：`Primary.TButton`（开始）、`Danger.TButton`（停止）、`Sidebar.TButton`（导航，含选中态）、`Card.TFrame`（带边框的卡片容器）

**对外 API：** 其它模块 `from src.gui.theme import COLOR_BG_CARD, ...` 用常量；不直接传颜色给 widget。

**不使用第三方 ttk 主题包**（azure / sun-valley 等）：避免新依赖、避免色板对不上 mockup 后还要手动覆盖一堆样式。

## 5. 数据流与状态归属

```
MainWindow（协调者）
├── 持有：
│   pipeline, overlay, hotkey_mgr, tray
│   log_queue (queue.Queue, maxsize=1000)
│   match_records (deque, maxlen=10)
│   is_running, stop_event, scan_thread, roi
│   _views = {scan, settings, hotkey, about}
│   _current_view
│   log_panel, match_panel  ← 常驻 widget 实例
├── 持有 widget：StatusBar、Sidebar、视图们、LogPanel、MatchRecords
└── 职责：
    on_start / on_stop（按钮 + 热键回调）
    _scan_loop（工作线程）
    _on_scan_result（主线程派发器）
    _drain_log_queue（主线程定时器）
    _switch_view(name)（侧栏点击）
    _on_close（看门狗式清理）
```

**扫描结果分发：**

```python
# 工作线程 _scan_loop：
result = pipeline.scan_once()
self.root.after(0, self._on_scan_result, result)

# 主线程 _on_scan_result：
def _on_scan_result(self, result):
    if result.skipped:
        logger.info("[skip] 帧无变化")
    else:
        logger.info(f"OCR: {len(result.ocr_results)}行, 匹配: {len(result.matches)}, 耗时: {result.duration:.3f}s")
    for m in result.matches:
        self._push_match_record(m)
    self.overlay.update(result.ocr_results, result.matches)
```

**匹配记录数据：**
- `deque(maxlen=10)`，**仅内存**，关闭程序丢弃（与 `Overlay._session_matches` 的语义一致，符合"零文件 I/O"哲学）
- N=10 写死，不做配置项
- 每条 record：`{'time': 'HH:MM:SS', 'keyword': str, 'ocr_text': str}`（直接显示完整 `ocr_text`，**不**做截断）

**LogPanel 与 MatchRecords 归 MainWindow 持有：**
- 这两个 widget 跟视图正交（不论在哪个视图，数据采集都在跑）
- `MainWindow` 持有 widget 实例；`ScanView` 构造时接收引用，仅负责"在自己的布局里把这俩面板 pack 出来"
- 切到非扫描视图时 `pack_forget`，widget 不销毁，数据继续累积；切回时 `refresh(deque)` 一次性同步

## 6. 生命周期 / 线程 / 错误处理

**线程清单（沿用当前模型，归属变了）：**

| 线程 | 谁创建 | 工作 | 同步 |
|---|---|---|---|
| 主线程 | OS | tkinter mainloop + 全部 widget 操作 | — |
| OCR 初始化 | `MainWindow.on_start` | `pipeline.init()`，完成后 `root.after(0)` 切回主线程 | one-shot daemon |
| 扫描线程 | `MainWindow._start_scanning` | `_scan_loop()` 循环 `pipeline.scan_once()` + `root.after` 派发 | `stop_event: threading.Event` |
| 日志队列消费 | `MainWindow.__init__` | 主线程 `root.after(100, _drain_log_queue)` 自调度 | `queue.Queue(1000)` |
| 热键钩子 | `keyboard` 库 | Ctrl+Alt+1/2，回调走 `root.after(0)` | — |
| 托盘 | `pystray` | 系统托盘菜单回调走 `root.after` | daemon |

**铁律：**
- 任何 widget 操作必须在主线程；工作线程要 UI 必须 `root.after(0, ...)`
- `on_start` / `on_stop` 幂等
- `pipeline.set_roi` / `init` / `release` 不并发

**错误处理（保留当前行为）：**

| 失败点 | 处理 |
|---|---|
| `pipeline.init()` 抛错 | 主线程弹 `messagebox.showerror` + 日志 ERROR + 状态回 "已停止" |
| `pipeline.scan_once()` 抛错 | 工作线程 `try/except`：日志 ERROR，跳出循环；`finally` 块 `root.after` 调 `_on_scan_thread_exit` 恢复 UI 状态 |
| ROI 选择取消（ESC） | 日志 WARNING，按全屏继续 |
| 词库文件不存在 | `SubstringMatcher` 已处理（返回空），日志 WARNING；编辑按钮提示是否创建 |
| 关闭窗口 | `_on_close`：3 秒看门狗 + 逐项 `try/except` 清理（roi_border / overlay / tray / hotkey / pipeline），最后 `os._exit(0)`。**这块原样保留**——它是踩过坑的兜底逻辑 |
| `pystray` 未安装 | tray 创建返回 None，关闭窗口走普通 `_on_close` 而不是缩托盘 |
| `keyboard` 库注册失败 | 日志 WARNING，按钮仍可用 |

**视图切换的安全性：**
- 切视图发生在主线程；`pack_forget` + `pack` 都是即时操作
- 工作线程对视图无感知，只发 `root.after(0, _on_scan_result)`
- LogPanel / MatchRecords 由 MainWindow 持有，切视图后 widget 仍存活，仅 `pack_forget`，调 `refresh()` 不会崩

**冒烟测试清单（手测，无自动化——tkinter GUI）：**
1. 启动 → 默认在扫描视图，所有控件可见
2. 点开始 → 状态变 "运行中"，日志开始滚动；命中关键词时匹配记录新增一行
3. 切到设置视图改帧差阈值 → 切回扫描视图，新阈值生效
4. 切到关于视图 → 等几秒切回扫描视图，匹配记录面板能补齐期间的命中
5. 点停止 → 状态变 "已停止"，按钮状态恢复
6. 按 Ctrl+Alt+2 在任意视图都能停
7. 关窗口（有 tray）缩托盘；从托盘退出能干净关闭（无 zombie 进程）
8. ROI 选择取消（ESC）回退全屏

## 7. 迁移路径

**写新代码的同时保持 `app.py` 能跑**——直到最后一步替换入口才切到新版，每一步可 `python app.py` 验证。

```
Step 1  src/gui/theme.py
        独立可测：写一个 demo Tk 窗口验证色板和 ttk style
        → app.py 暂不动

Step 2  src/gui/widgets/log_panel.py + match_records.py + roi_overlay.py
              + roi_border.py + tray.py
        把当前 app.py 里相关逻辑原样抽成模块
        → app.py 暂不 import 它们

Step 3  src/gui/sidebar.py + statusbar.py
        独立 widget，写 demo 窗口验证选中态/按钮状态切换

Step 4  src/gui/views/base.py + 4 个 view 文件
        每个 view 独立可挂载到一个 demo Frame 验证布局
        scan_view 内部布局：扫描配置 + LogPanel 占位 + MatchRecords 占位

Step 5  src/gui/main_window.py
        把当前 MainGUI 的协调逻辑搬过来，widget 全换成新模块的实例
        view 切换、scan 结果分发、按钮状态在这里收尾

Step 6  改写 app.py（< 50 行）
        from src.gui.main_window import MainWindow
        root = tk.Tk(); MainWindow(root); root.mainloop()
        → 这一步开始就跑新版 UI
        旧版的 1200+ 行可以在同一 commit 删除

Step 7  清理
        - mockups/mockup_c.py：删除（不再是设计参考）
        - 当前 app.py 顶部 25 行 "UI 配色与字体" 常量：随旧 GUI 删掉
        - 确认 cli.py / shared/ / src/pipeline/ / src/{config,utils} 完全没动
```

## 8. 显式不变项

下列模块本次重构**不动**：

| 模块 | 状态 |
|---|---|
| `src/pipeline/*` | 不动（capture / diff_gate / ocr_stage / pipeline） |
| `src/config/config.py` + `defaults.py` + `config/config.yaml` | 不动（schema 不变） |
| `shared/matcher.py` + `shared/overlay.py` | 不动 |
| `src/utils/{logger,hotkey}.py` | 不动 |
| `cli.py` | 不动（CLI 不依赖 GUI） |
| `old_version/*` | 不动（归档） |
| `gui.bat` | 不动（仍调 `app.py`） |

**配置 schema 完全保持**：
- `scan.{interval_seconds, roi, roi_padding, roi_presets, diff_threshold}`
- `ocr.{language, min_confidence, enable_image_invert}`
- `gpu.enabled`
- `files.banlist_file`
- `matching.{display_duration, font_size, position, enable_sound}`
- `logging.level`

## 9. 显式删除项

按用户指示删除的代码逻辑：

- `MainGUI.scan_count`、`MainGUI.last_scan_time` 实例变量
- `MainGUI._update_stats` 方法
- `_lbl_count` / `_lbl_last` 标签
- `_create_topbar` 整个方法
- `_scan_loop` 里的 `self.scan_count += 1` 与 `self.last_scan_time = ...` 两行

**保留并迁移：**
- `_get_memory_mb()` 移到 `statusbar.py`
- `_schedule_memory_update` 移到 `MainWindow`，每 5 s 调 `statusbar.set_memory(mb)`

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 拆 widget 时把 `_on_close` 看门狗逻辑改坏 → 关窗 zombie 进程 | Step 5 把现有清理顺序原样搬到 `MainWindow._on_close`，**逐 try/except + 看门狗 Timer**；冒烟测试 #7 覆盖 |
| 视图切换中 `root.after` 的 callback 操作已 `pack_forget` 的 widget | 设计已规避：LogPanel / MatchRecords 由 MainWindow 持有，常驻不销毁，仅 `pack_forget` |
| 主题色板对比度不够 / 与 mockup 视觉偏差 | Step 1 的 demo 窗口先用色板渲染所有 widget 类型；和 mockup 截图对比；偏差大就在 commit 前调 `theme.py` 常量 |
| 滑块/Combobox 在 clam 主题上的 ttk style 已经踩过 padding 坑（旧 app.py 注释里详述） | 沿用旧 app.py 已调好的 ttk style 配置（`Primary.TButton` / `Danger.TButton` / `TNotebook.Tab` 的边框处理）；只换颜色不换结构 |

---

**实施技能：** `superpowers:writing-plans` 将基于本 spec 产出 step-by-step 实施计划。
