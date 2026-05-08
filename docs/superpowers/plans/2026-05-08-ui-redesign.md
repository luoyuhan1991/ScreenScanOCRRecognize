# UI 重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `app.py` 单文件 GUI 重写为 `src/gui/` 多文件深色主题结构，加 4 视图侧栏导航 + 匹配记录面板，状态/控制移到底栏。

**Architecture:** 三大区域（左侧 Sidebar / 中央 Content / 底部 Statusbar）。`MainWindow` 是协调者，持有 pipeline / overlay / 跨视图常驻 widget；4 个 View 子类各自负责自己的配置项。`pipeline / config / shared / cli` 完全不动。

**Tech Stack:** Python 3, tkinter / ttk（clam 主题 + 自定义深色样式），PaddleOCR 3.x（不动），mss / Pillow / pyahocorasick / pystray / keyboard。

**Spec:** [`docs/superpowers/specs/2026-05-08-ui-redesign-design.md`](../specs/2026-05-08-ui-redesign-design.md) — commit `4954118`。

---

## 实施约定

**TDD ≠ pytest 在这里。** 项目无 pytest 基础设施，主版本无自动化测试（仅 `old_version/src/tests/`）。本计划"测试" = 在每个新模块底部加 `if __name__ == "__main__":` 演示块，构造 widget + 触发关键操作 + 视觉检查。需要数据正确性的（如 deque 截断）用 `assert` 加在演示块开头。

**app.py 在 Task 17 之前一直能跑。** Task 1-16 只**新增** `src/gui/` 下的文件；不修改 `app.py`，不修改 pipeline / config / shared / utils 任何文件。每个 Task commit 完后 `python app.py` 仍是旧版 UI 正常运行。

**冒烟测试约定：** 每个含演示块的模块用 `python -m <module.path>` 运行（项目根目录）。Windows PowerShell 直接 `python -m src.gui.widgets.log_panel` 即可——`src/config/config.py` 顶部已经把项目根加进 `sys.path`，但子模块不依赖那个，演示块里要先 `sys.path.insert(0, '.')` 才能 import `from defaults import ...` 等。简单方案：演示块先做 `import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))` 把项目根加上。

**提交规范：** 每个 Task 末尾 `git commit`。commit message 用中文，遵循 `<type>: <summary>` 格式（见现有 `git log`）。type ∈ {feat, refactor, style, docs, chore}。

**目录写法：** 路径用斜杠 `/`，PowerShell 也能识别。

---

## 文件结构（最终目标）

```
ScreenScanOCRRecognize/
├── app.py                          # < 50 行（Task 17 重写）
├── src/gui/                        # ★ 全部新增
│   ├── __init__.py
│   ├── theme.py                    # 常量 + apply(root)
│   ├── main_window.py              # MainWindow（协调者）
│   ├── sidebar.py                  # Sidebar 导航
│   ├── statusbar.py                # StatusBar 底栏
│   ├── views/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseView
│   │   ├── scan_view.py            # 扫描视图（最大）
│   │   ├── settings_view.py        # 设置视图
│   │   ├── hotkey_view.py          # 热键视图
│   │   └── about_view.py           # 关于视图
│   └── widgets/
│       ├── __init__.py
│       ├── log_panel.py            # 运行日志面板
│       ├── match_records.py        # 匹配记录面板（NEW 类）
│       ├── roi_overlay.py          # 拖选 ROI 全屏窗
│       ├── roi_border.py           # 扫描 ROI 红框
│       └── tray.py                 # pystray 托盘
└── （shared/, src/{config,pipeline,utils}/, cli.py, old_version/, gui.bat 不动）
```

---

# Phase 1：骨架与主题（Spec §3 + §4）

## Task 1：创建目录骨架

**Files:**
- Create: `src/gui/__init__.py`
- Create: `src/gui/views/__init__.py`
- Create: `src/gui/widgets/__init__.py`

- [ ] **Step 1：创建 3 个空 `__init__.py`**

PowerShell：
```powershell
New-Item -ItemType Directory -Path src/gui, src/gui/views, src/gui/widgets -Force | Out-Null
New-Item -ItemType File -Path src/gui/__init__.py, src/gui/views/__init__.py, src/gui/widgets/__init__.py -Force | Out-Null
```

每个文件留空（无内容）。

- [ ] **Step 2：验证目录结构**

```powershell
Get-ChildItem src/gui -Recurse -File | Select-Object FullName
```

期望输出三行 `__init__.py` 路径，无别的文件。

- [ ] **Step 3：app.py 仍能跑**

```powershell
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('app.py syntax OK')"
```

期望：`app.py syntax OK`（不修改 app.py，只是确认）。

- [ ] **Step 4：提交**

```powershell
git add src/gui/__init__.py src/gui/views/__init__.py src/gui/widgets/__init__.py
git commit -m "chore: 创建 src/gui 目录骨架"
```

---

## Task 2：theme.py — 深色色板与 ttk 样式

**Files:**
- Create: `src/gui/theme.py`

- [ ] **Step 1：写 theme.py 全文**

```python
"""
深色主题色板 + ttk 样式配置。

固定深色，不支持主题切换。其它模块只 import 常量，不直接传颜色给 widget。
"""

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# 字体
# ---------------------------------------------------------------------------

UI_FONT = "Microsoft YaHei"
FONT_SIZE_BASE = 9
FONT_SIZE_TITLE = 11
FONT_SIZE_HEADER = 13

# ---------------------------------------------------------------------------
# 背景层（外 → 内：窗口 → 侧栏 → 内容 → 卡片）
# ---------------------------------------------------------------------------

COLOR_BG_WINDOW     = "#0f1420"
COLOR_BG_SIDEBAR    = "#161b2a"
COLOR_BG_CONTENT    = "#0f1420"
COLOR_BG_CARD       = "#1a2235"
COLOR_BG_CARD_HOVER = "#222b40"
COLOR_BG_INPUT      = "#0a0f1a"
COLOR_BG_LOG        = "#0a0f1a"

# ---------------------------------------------------------------------------
# 边框
# ---------------------------------------------------------------------------

COLOR_BORDER       = "#2a3245"
COLOR_BORDER_FOCUS = "#3a82f7"

# ---------------------------------------------------------------------------
# 文字
# ---------------------------------------------------------------------------

COLOR_TEXT       = "#e8ecf3"
COLOR_TEXT_DIM   = "#8a93a8"
COLOR_TEXT_MUTED = "#5a6478"

# ---------------------------------------------------------------------------
# 状态色
# ---------------------------------------------------------------------------

COLOR_PRIMARY        = "#3a82f7"
COLOR_PRIMARY_HOVER  = "#4a92ff"
COLOR_PRIMARY_PRESS  = "#2a72e7"
COLOR_DANGER         = "#e54848"
COLOR_DANGER_HOVER   = "#ff5858"
COLOR_DANGER_PRESS   = "#c53838"
COLOR_SUCCESS        = "#22c55e"
COLOR_WARNING        = "#f59e0b"

# ---------------------------------------------------------------------------
# 日志颜色（深底浅字）
# ---------------------------------------------------------------------------

COLOR_INFO_LOG    = "#60a5fa"
COLOR_DEBUG_LOG   = "#9ca3af"
COLOR_WARNING_LOG = "#fbbf24"
COLOR_ERROR_LOG   = "#f87171"

# ---------------------------------------------------------------------------
# 时间 chip（绿底深字）
# ---------------------------------------------------------------------------

COLOR_CHIP_BG = COLOR_SUCCESS
COLOR_CHIP_FG = "#0a1f12"


def apply(root):
    """一次性把 ttk style 全配好。MainWindow.__init__ 一开始调一次。"""
    root.configure(bg=COLOR_BG_WINDOW)

    style = ttk.Style(root)
    style.theme_use("clam")

    # ---- 基础 ----
    style.configure(".",
                    background=COLOR_BG_WINDOW,
                    foreground=COLOR_TEXT,
                    font=(UI_FONT, FONT_SIZE_BASE))

    style.configure("TFrame", background=COLOR_BG_WINDOW)
    style.configure("Card.TFrame", background=COLOR_BG_CARD,
                    relief="flat", borderwidth=0)
    style.configure("Sidebar.TFrame", background=COLOR_BG_SIDEBAR)
    style.configure("Content.TFrame", background=COLOR_BG_CONTENT)
    style.configure("Statusbar.TFrame", background=COLOR_BG_CARD)

    style.configure("TLabel", background=COLOR_BG_WINDOW, foreground=COLOR_TEXT)
    style.configure("Card.TLabel", background=COLOR_BG_CARD, foreground=COLOR_TEXT)
    style.configure("Sidebar.TLabel", background=COLOR_BG_SIDEBAR, foreground=COLOR_TEXT)
    style.configure("Statusbar.TLabel", background=COLOR_BG_CARD, foreground=COLOR_TEXT)
    style.configure("Dim.TLabel", background=COLOR_BG_CARD,
                    foreground=COLOR_TEXT_DIM, font=(UI_FONT, FONT_SIZE_BASE - 1))
    style.configure("Header.TLabel", background=COLOR_BG_CARD,
                    foreground=COLOR_TEXT, font=(UI_FONT, FONT_SIZE_TITLE, "bold"))
    style.configure("Section.TLabel", background=COLOR_BG_CARD,
                    foreground=COLOR_PRIMARY, font=(UI_FONT, FONT_SIZE_BASE, "bold"))

    # ---- Checkbutton ----
    style.configure("TCheckbutton",
                    background=COLOR_BG_CARD,
                    foreground=COLOR_TEXT,
                    focuscolor=COLOR_BG_CARD)
    style.map("TCheckbutton",
              background=[("active", COLOR_BG_CARD)],
              foreground=[("disabled", COLOR_TEXT_MUTED)])

    # ---- Combobox ----
    style.configure("TCombobox",
                    fieldbackground=COLOR_BG_INPUT,
                    background=COLOR_BG_INPUT,
                    foreground=COLOR_TEXT,
                    bordercolor=COLOR_BORDER,
                    arrowcolor=COLOR_TEXT,
                    selectbackground=COLOR_BG_INPUT,
                    selectforeground=COLOR_TEXT)
    style.map("TCombobox",
              fieldbackground=[("readonly", COLOR_BG_INPUT)],
              foreground=[("readonly", COLOR_TEXT)],
              bordercolor=[("focus", COLOR_BORDER_FOCUS)])
    # Listbox（下拉项）必须用 option_add，ttk style 管不到
    root.option_add("*TCombobox*Listbox.background", COLOR_BG_INPUT)
    root.option_add("*TCombobox*Listbox.foreground", COLOR_TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", COLOR_PRIMARY)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")

    # ---- Entry ----
    style.configure("TEntry",
                    fieldbackground=COLOR_BG_INPUT,
                    foreground=COLOR_TEXT,
                    bordercolor=COLOR_BORDER,
                    insertcolor=COLOR_TEXT)
    style.map("TEntry", bordercolor=[("focus", COLOR_BORDER_FOCUS)])

    # ---- Scale ----
    style.configure("TScale",
                    background=COLOR_BG_CARD,
                    troughcolor=COLOR_BG_INPUT,
                    bordercolor=COLOR_BG_CARD,
                    lightcolor=COLOR_PRIMARY,
                    darkcolor=COLOR_PRIMARY)

    # ---- 默认 Button（深灰背景） ----
    _btn_bg       = "#222b40"
    _btn_hover    = "#2a3650"
    _btn_press    = "#1a2235"
    _btn_disabled = "#161b2a"
    style.configure("TButton",
                    background=_btn_bg, foreground=COLOR_TEXT,
                    bordercolor=_btn_bg, lightcolor=_btn_bg, darkcolor=_btn_bg,
                    borderwidth=0, padding=(12, 6), relief="flat",
                    font=(UI_FONT, FONT_SIZE_BASE))
    for prop in ("background", "bordercolor", "lightcolor", "darkcolor"):
        style.map("TButton", **{prop: [
            ("disabled", _btn_disabled),
            ("pressed", _btn_press),
            ("active", _btn_hover),
        ]})
    style.map("TButton", foreground=[("disabled", COLOR_TEXT_MUTED)])

    # ---- Primary（开始扫描） ----
    style.configure("Primary.TButton",
                    background=COLOR_PRIMARY, foreground="white",
                    bordercolor=COLOR_PRIMARY, lightcolor=COLOR_PRIMARY, darkcolor=COLOR_PRIMARY,
                    borderwidth=0, padding=(20, 8), relief="flat",
                    font=(UI_FONT, FONT_SIZE_BASE, "bold"))
    for prop in ("background", "bordercolor", "lightcolor", "darkcolor"):
        style.map("Primary.TButton", **{prop: [
            ("disabled", "#1f4a8c"),
            ("pressed", COLOR_PRIMARY_PRESS),
            ("active", COLOR_PRIMARY_HOVER),
        ]})
    style.map("Primary.TButton", foreground=[("disabled", "#9bbfe2")])

    # ---- Danger（停止扫描） ----
    style.configure("Danger.TButton",
                    background=COLOR_DANGER, foreground="white",
                    bordercolor=COLOR_DANGER, lightcolor=COLOR_DANGER, darkcolor=COLOR_DANGER,
                    borderwidth=0, padding=(20, 8), relief="flat",
                    font=(UI_FONT, FONT_SIZE_BASE, "bold"))
    for prop in ("background", "bordercolor", "lightcolor", "darkcolor"):
        style.map("Danger.TButton", **{prop: [
            ("disabled", "#7a2828"),
            ("pressed", COLOR_DANGER_PRESS),
            ("active", COLOR_DANGER_HOVER),
        ]})
    style.map("Danger.TButton", foreground=[("disabled", "#e8b5a8")])

    # ---- Sidebar 导航按钮（基础态 + 选中态由 Sidebar 自己刷 background） ----
    style.configure("Sidebar.TButton",
                    background=COLOR_BG_SIDEBAR, foreground=COLOR_TEXT_DIM,
                    bordercolor=COLOR_BG_SIDEBAR, lightcolor=COLOR_BG_SIDEBAR,
                    darkcolor=COLOR_BG_SIDEBAR,
                    borderwidth=0, padding=(8, 12), relief="flat",
                    font=(UI_FONT, FONT_SIZE_BASE))
    for prop in ("background", "bordercolor", "lightcolor", "darkcolor"):
        style.map("Sidebar.TButton", **{prop: [
            ("active", "#1f2538"),
        ]})
    style.map("Sidebar.TButton", foreground=[("active", COLOR_TEXT)])

    style.configure("SidebarActive.TButton",
                    background=COLOR_PRIMARY, foreground="white",
                    bordercolor=COLOR_PRIMARY, lightcolor=COLOR_PRIMARY,
                    darkcolor=COLOR_PRIMARY,
                    borderwidth=0, padding=(8, 12), relief="flat",
                    font=(UI_FONT, FONT_SIZE_BASE, "bold"))
    for prop in ("background", "bordercolor", "lightcolor", "darkcolor"):
        style.map("SidebarActive.TButton", **{prop: [
            ("active", COLOR_PRIMARY_HOVER),
            ("pressed", COLOR_PRIMARY_PRESS),
        ]})


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    root.title("theme.py demo")
    root.geometry("520x420")
    apply(root)

    frm = ttk.Frame(root, style="Card.TFrame", padding=16)
    frm.pack(fill="both", expand=True, padx=16, pady=16)

    ttk.Label(frm, text="主题样式预览", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
    ttk.Label(frm, text="副标题文字", style="Dim.TLabel").pack(anchor="w")
    ttk.Label(frm, text="区段标签", style="Section.TLabel").pack(anchor="w", pady=(8, 4))

    row = ttk.Frame(frm, style="Card.TFrame")
    row.pack(fill="x", pady=4)
    ttk.Button(row, text="默认按钮").pack(side="left", padx=4)
    ttk.Button(row, text="开始扫描", style="Primary.TButton").pack(side="left", padx=4)
    ttk.Button(row, text="停止扫描", style="Danger.TButton").pack(side="left", padx=4)

    row2 = ttk.Frame(frm, style="Card.TFrame")
    row2.pack(fill="x", pady=4)
    var = tk.BooleanVar(value=True)
    ttk.Checkbutton(row2, text="启用某项", variable=var).pack(side="left", padx=4)

    ttk.Combobox(frm, values=["选项一", "选项二", "选项三"],
                 state="readonly").pack(fill="x", pady=4)
    ttk.Entry(frm).pack(fill="x", pady=4)
    ttk.Scale(frm, from_=0, to=10).pack(fill="x", pady=4)

    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.theme
```

视觉检查：
- 窗口背景近黑（`#0f1420`）
- 内部卡片颜色更亮一些（`#1a2235`）
- "开始扫描" 按钮亮蓝、"停止扫描" 按钮亮红
- Combobox 下拉项是深底浅字（不是默认白底黑字）
- Entry 输入区是深色（`#0a0f1a`）
- Scale 拖动条凹槽颜色协调
- 所有文字清晰可读

关闭窗口，终端无报错。

- [ ] **Step 3：app.py 仍能跑**

```powershell
python -c "import app; print('app.py import OK')"
```

期望：能成功 import（不报错）。

- [ ] **Step 4：提交**

```powershell
git add src/gui/theme.py
git commit -m "feat: 添加 src/gui/theme.py 深色主题与 ttk 样式"
```

---

# Phase 2：跨视图复用 widget（Spec §3 widgets/ + §6 错误处理）

> **重要：** 这个 phase 创建的 widget 跟 `app.py` 里现有逻辑**功能等价**但**作为独立模块**存在。`app.py` 不修改、不导入它们。Task 17 替换入口时这些 widget 就直接被 `MainWindow` 使用。

## Task 3：LogPanel widget

**Files:**
- Create: `src/gui/widgets/log_panel.py`

**职责：** 一个 ScrolledText 包装类，提供 `append(message, level)` 接口，自带 INFO/WARNING/ERROR/DEBUG 颜色 tag、行数上限、自动滚到底。**不**包含 logging.Handler / queue.Queue（那部分归 MainWindow）。

- [ ] **Step 1：写 log_panel.py 全文**

```python
"""
运行日志面板 widget。

提供 append(msg, level) 接口；INFO/WARNING/ERROR/DEBUG 各自带颜色；
超过 max_lines 时丢弃最早的 200 行（保留近期日志，避免无限增长）。

不包含 logging.Handler / queue.Queue —— 那是 MainWindow 的职责。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext

# 项目根加 sys.path，让演示块能 import theme
_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.theme import (
    UI_FONT, FONT_SIZE_BASE, FONT_SIZE_TITLE,
    COLOR_BG_CARD, COLOR_BG_LOG, COLOR_BORDER,
    COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_INFO_LOG, COLOR_DEBUG_LOG, COLOR_WARNING_LOG, COLOR_ERROR_LOG,
)


class LogPanel(ttk.Frame):
    """运行日志面板：标题栏（含清空按钮）+ 深色 ScrolledText。"""

    MAX_LINES = 2000      # 超过这个数就裁掉最早的 200 行

    def __init__(self, parent, on_clear=None):
        super().__init__(parent, style="Card.TFrame", padding=8)
        self._on_clear = on_clear
        self._build()

    def _build(self):
        # 标题栏
        head = ttk.Frame(self, style="Card.TFrame")
        head.pack(fill="x", pady=(0, 6))
        ttk.Label(head, text="运行日志", style="Header.TLabel").pack(side="left")
        ttk.Button(head, text="清空", command=self._clear).pack(side="right")

        # 文本框（外加 1px 边框）
        wrap = tk.Frame(self, bg=COLOR_BORDER)
        wrap.pack(fill="both", expand=True)
        self._text = scrolledtext.ScrolledText(
            wrap, wrap=tk.WORD, font=("Consolas", 9),
            bg=COLOR_BG_LOG, fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            borderwidth=0, highlightthickness=0,
        )
        self._text.pack(fill="both", expand=True, padx=1, pady=1)
        self._text.tag_config("INFO",    foreground=COLOR_INFO_LOG)
        self._text.tag_config("WARNING", foreground=COLOR_WARNING_LOG)
        self._text.tag_config("ERROR",   foreground=COLOR_ERROR_LOG)
        self._text.tag_config("DEBUG",   foreground=COLOR_DEBUG_LOG)

    def append(self, message, level="INFO"):
        """追加一行日志。message 不要自带换行——内部统一加。"""
        if not message.endswith("\n"):
            message = message + "\n"
        self._text.insert(tk.END, message, level)
        self._text.see(tk.END)

        lines = int(self._text.index("end-1c").split(".")[0])
        if lines > self.MAX_LINES:
            self._text.delete("1.0", "200.0")

    def clear(self):
        self._text.delete("1.0", tk.END)

    def _clear(self):
        self.clear()
        if self._on_clear:
            self._on_clear()


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.gui.theme import apply

    root = tk.Tk()
    root.title("LogPanel demo")
    root.geometry("700x400")
    apply(root)

    panel = LogPanel(root)
    panel.pack(fill="both", expand=True, padx=16, pady=16)

    panel.append("2026-05-08 10:00:00.123 - 程序启动", "INFO")
    panel.append("2026-05-08 10:00:01.456 - 调试细节: foo=42, bar=hello", "DEBUG")
    panel.append("2026-05-08 10:00:02.789 - 警告: 词库文件较大，加载慢", "WARNING")
    panel.append("2026-05-08 10:00:03.012 - 错误: 无法连接 GPU", "ERROR")

    btn = ttk.Button(root, text="追加 10 行测试",
                     command=lambda: [panel.append(f"测试行 #{i}", "INFO") for i in range(10)])
    btn.pack(pady=8)

    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.widgets.log_panel
```

视觉检查：
- 黑色文本框，4 行示例日志，颜色分别为蓝（INFO）/灰（DEBUG）/黄（WARNING）/红（ERROR）
- 点"清空"按钮——文本框清空
- 点"追加 10 行测试"——10 行 INFO 显示，自动滚到底
- 标题栏 "运行日志" + 右侧"清空"按钮位置正确

- [ ] **Step 3：提交**

```powershell
git add src/gui/widgets/log_panel.py
git commit -m "feat: 添加 LogPanel widget（含演示块）"
```

---

## Task 4：MatchRecords widget（新增）

**Files:**
- Create: `src/gui/widgets/match_records.py`

**职责：** 显示最近 N 条匹配记录。每行：时间 chip（绿底深字）+ 关键词 + OCR 文本片段。提供 `refresh(records: deque)` 接口，整面板按 records 重绘。**widget 自身不持有 deque 数据**——数据归 MainWindow，widget 是无状态视图。

- [ ] **Step 1：写 match_records.py 全文**

```python
"""
匹配记录面板：显示最近 N 条命中关键词的记录。

每行三列：时间 chip（绿底深字）| 关键词 | OCR 文本片段
widget 不持有数据 —— refresh(records) 接收外部 deque/list 全量重绘。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.theme import (
    UI_FONT, FONT_SIZE_BASE, FONT_SIZE_TITLE,
    COLOR_BG_CARD, COLOR_BG_INPUT, COLOR_BORDER,
    COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_CHIP_BG, COLOR_CHIP_FG,
)


class MatchRecords(ttk.Frame):
    """匹配记录面板。

    Record 数据格式（dict）：
        {'time': 'HH:MM:SS', 'keyword': str, 'ocr_text': str}
    """

    MAX_DISPLAY = 10

    def __init__(self, parent, on_clear=None):
        super().__init__(parent, style="Card.TFrame", padding=8)
        self._on_clear = on_clear
        self._row_widgets = []   # list of created Frame for each record row
        self._build()

    def _build(self):
        # 标题栏
        head = ttk.Frame(self, style="Card.TFrame")
        head.pack(fill="x", pady=(0, 6))
        ttk.Label(head, text="匹配记录 (最近 10 条)",
                  style="Header.TLabel").pack(side="left")
        ttk.Button(head, text="清空", command=self._clear).pack(side="right")

        # 内容容器（外加 1px 边框）
        wrap = tk.Frame(self, bg=COLOR_BORDER)
        wrap.pack(fill="both", expand=True)
        self._inner = tk.Frame(wrap, bg=COLOR_BG_INPUT)
        self._inner.pack(fill="both", expand=True, padx=1, pady=1)

        # 空态提示
        self._empty = tk.Label(self._inner, text="暂无匹配记录",
                               bg=COLOR_BG_INPUT, fg=COLOR_TEXT_DIM,
                               font=(UI_FONT, FONT_SIZE_BASE))
        self._empty.pack(expand=True)

    def refresh(self, records):
        """records: 可迭代，每项是 {'time','keyword','ocr_text'} dict。
        最新的记录显示在最上面（按 deque append 语义反转）。"""
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        records = list(records)
        if not records:
            self._empty.pack(expand=True)
            return

        self._empty.pack_forget()

        # 倒序（最新的在最上面）
        for r in reversed(records[-self.MAX_DISPLAY:]):
            self._add_row(r)

    def _add_row(self, record):
        row = tk.Frame(self._inner, bg=COLOR_BG_INPUT)
        row.pack(fill="x", padx=8, pady=4, anchor="w")

        # 时间 chip（绿底深字、圆角靠 padding 模拟）
        chip = tk.Label(row, text=record.get("time", "--:--:--"),
                        bg=COLOR_CHIP_BG, fg=COLOR_CHIP_FG,
                        font=(UI_FONT, FONT_SIZE_BASE - 1, "bold"),
                        padx=8, pady=2)
        chip.pack(side="left")

        # 关键词
        kw = tk.Label(row, text=record.get("keyword", ""),
                      bg=COLOR_BG_INPUT, fg=COLOR_TEXT,
                      font=(UI_FONT, FONT_SIZE_BASE, "bold"))
        kw.pack(side="left", padx=(8, 12))

        # OCR 文本片段（占满剩余宽度）
        ocr = tk.Label(row, text=record.get("ocr_text", ""),
                       bg=COLOR_BG_INPUT, fg=COLOR_TEXT_DIM,
                       font=(UI_FONT, FONT_SIZE_BASE),
                       anchor="w", justify="left", wraplength=400)
        ocr.pack(side="left", fill="x", expand=True)

        self._row_widgets.append(row)

    def _clear(self):
        self.refresh([])
        if self._on_clear:
            self._on_clear()


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from collections import deque
    from src.gui.theme import apply

    # ---- 数据正确性 sanity check ----
    panel_test_records = deque(maxlen=10)
    for i in range(15):
        panel_test_records.append({"time": f"00:00:{i:02d}",
                                    "keyword": f"k{i}",
                                    "ocr_text": f"text {i}"})
    assert len(panel_test_records) == 10, "deque(10) 应自动淘汰"
    assert panel_test_records[0]["keyword"] == "k5", "最早的应是 k5（k0-k4 被挤掉）"
    print("✓ deque 截断行为正确")

    # ---- 视觉演示 ----
    root = tk.Tk()
    root.title("MatchRecords demo")
    root.geometry("600x400")
    apply(root)

    panel = MatchRecords(root)
    panel.pack(fill="both", expand=True, padx=16, pady=16)

    sample = deque(maxlen=10)
    sample.append({"time": "18:03:41", "keyword": "成功",
                   "ocr_text": "操作成功完成"})
    sample.append({"time": "18:03:42", "keyword": "警告",
                   "ocr_text": "系统发出警告：内存不足"})
    sample.append({"time": "18:03:45", "keyword": "错误",
                   "ocr_text": "发生错误，请重试"})
    panel.refresh(sample)

    def add_one():
        from datetime import datetime
        sample.append({"time": datetime.now().strftime("%H:%M:%S"),
                       "keyword": "新词",
                       "ocr_text": "测试追加一条记录"})
        panel.refresh(sample)

    ttk.Button(root, text="追加一条", command=add_one).pack(pady=8)

    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.widgets.match_records
```

视觉检查：
- 终端先输出 `✓ deque 截断行为正确`
- 窗口里 3 行匹配记录，**最新的（错误）在最上面**
- 时间 chip 是绿底深字、紧凑
- 点"追加一条"——顶部新增一行（时间是当前），其它行下移
- 点"清空"——所有行消失，显示"暂无匹配记录"

- [ ] **Step 3：提交**

```powershell
git add src/gui/widgets/match_records.py
git commit -m "feat: 添加 MatchRecords widget"
```

---

## Task 5：抽出 ROI 选择窗

**Files:**
- Create: `src/gui/widgets/roi_overlay.py`

**职责：** 把 `app.py:129-212` 的 `select_roi_interactive(parent)` 函数原样搬过来作为模块函数，签名不变，行为不变。`app.py` 自己保留旧实现直到 Task 17。

- [ ] **Step 1：写 roi_overlay.py 全文**

```python
"""
ROI 交互选择：截屏 + 半透明全屏窗 + 拖拽矩形。

返回 (x1, y1, x2, y2) 或 None（用户按 ESC 取消时）。
"""

import os
import sys
import tkinter as tk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.utils.logger import logger


def select_roi_interactive(parent=None):
    """截屏后显示半透明全屏窗口，让用户拖选 ROI 矩形。

    Args:
        parent: tkinter 根窗口；非 None 时用 Toplevel + wait_window
                None 时独立 Tk + mainloop

    Returns:
        (x1, y1, x2, y2) 或 None
    """
    try:
        from PIL import ImageGrab, ImageTk
    except ImportError:
        logger.error("PIL 未安装，无法交互选择 ROI")
        return None

    screenshot = ImageGrab.grab()
    width, height = screenshot.size

    if parent is not None:
        win = tk.Toplevel(parent)
        use_wait = True
    else:
        win = tk.Tk()
        use_wait = False

    win.title("选择ROI区域 (按住拖动, ESC取消)")
    win.geometry(f"{width}x{height}")
    win.attributes('-fullscreen', True)
    win.attributes('-topmost', True)
    win.attributes('-alpha', 0.5)

    photo = ImageTk.PhotoImage(screenshot)
    canvas = tk.Canvas(win, width=width, height=height, cursor='crosshair')
    canvas.pack(fill='both', expand=True)
    canvas.photo = photo  # prevent GC
    canvas.create_image(0, 0, image=photo, anchor='nw')

    data = {'start': None, 'end': None, 'rect': None, 'done': False}

    def on_down(e):
        data['start'] = (e.x, e.y)
        data['end'] = None
        data['done'] = False

    def on_drag(e):
        if data['start']:
            data['end'] = (e.x, e.y)
            if data['rect']:
                canvas.delete(data['rect'])
            x1, y1 = data['start']
            data['rect'] = canvas.create_rectangle(
                x1, y1, e.x, e.y, outline='red', width=2
            )

    def on_up(e):
        if data['start']:
            data['end'] = (e.x, e.y)
            data['done'] = True
            win.destroy()

    def on_key(e):
        if e.keysym == 'Escape':
            data['done'] = False
            win.destroy()

    canvas.bind('<Button-1>', on_down)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_up)
    win.bind('<Key>', on_key)
    canvas.focus_set()

    if use_wait:
        win.wait_window()
    else:
        win.mainloop()

    try:
        screenshot.close()
    except Exception:
        pass

    if data['done'] and data['start'] and data['end']:
        x1, y1 = data['start']
        x2, y2 = data['end']
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        return (x1, y1, x2, y2)
    return None


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("将出现半透明全屏窗，拖选一个矩形或按 ESC 取消...")
    result = select_roi_interactive()
    if result:
        print(f"选择的 ROI: {result}")
    else:
        print("取消")
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.widgets.roi_overlay
```

视觉检查：
- 全屏半透明遮罩出现
- 鼠标拖动能画出红色矩形
- 松开鼠标关闭，终端打印 `选择的 ROI: (x1, y1, x2, y2)`
- 重新运行，按 ESC 关闭，终端打印 `取消`

- [ ] **Step 3：提交**

```powershell
git add src/gui/widgets/roi_overlay.py
git commit -m "feat: 抽出 select_roi_interactive 到 widgets/roi_overlay.py"
```

---

## Task 6：抽出 ROI 边框可视化

**Files:**
- Create: `src/gui/widgets/roi_border.py`

**职责：** 把 `app.py` 的 `_show_roi_border` / `_hide_roi_border` 抽成 `RoiBorder` 类。构造接收 `parent_root` + `padding`；`show(roi)` 创建可视化边框、`hide()` 销毁。

- [ ] **Step 1：写 roi_border.py 全文**

```python
"""
扫描时 ROI 区域的红色边框可视化（独立顶层窗，置顶、点击穿透）。

show(roi) 创建窗口，hide() 销毁。同时只能有一个边框窗存活。
"""

import os
import sys
import tkinter as tk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.utils.logger import logger


class RoiBorder:
    def __init__(self, parent_root, padding=10):
        self._parent = parent_root
        self._padding = padding
        self._win = None

    def show(self, roi):
        """显示 ROI 边框。roi=None 时按全屏画。"""
        self.hide()  # 幂等：先关旧的
        try:
            import ctypes
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)

            if roi:
                x1, y1, x2, y2 = roi
                x1 = max(0, x1 - self._padding)
                y1 = max(0, y1 - self._padding)
                x2 = min(sw, x2 + self._padding)
                y2 = min(sh, y2 + self._padding)
            else:
                x1, y1, x2, y2 = 0, 0, sw, sh

            w, h = x2 - x1, y2 - y1
            if w <= 0 or h <= 0:
                return

            win = tk.Toplevel(self._parent)
            win.withdraw()
            win.overrideredirect(True)
            win.attributes('-topmost', True)
            win.attributes('-transparentcolor', 'black')
            win.geometry(f'{w}x{h}+{x1}+{y1}')
            win.config(bg='black')

            c = tk.Canvas(win, width=w, height=h, bg='black',
                          highlightthickness=0, bd=0)
            c.pack(fill=tk.BOTH, expand=True)
            c.create_rectangle(1, 1, w - 1, h - 1,
                               outline='#ff3333', width=3, fill='')

            win.deiconify()
            self._win = win
        except Exception as e:
            logger.debug(f"ROI 边框显示失败: {e}")

    def hide(self):
        try:
            if self._win:
                self._win.destroy()
                self._win = None
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    root.title("RoiBorder demo")
    root.geometry("400x200+100+100")

    border = RoiBorder(root, padding=10)
    tk.Button(root, text="显示边框 (300,300)→(800,600)",
              command=lambda: border.show((300, 300, 800, 600))).pack(pady=8)
    tk.Button(root, text="显示全屏边框 (roi=None)",
              command=lambda: border.show(None)).pack(pady=8)
    tk.Button(root, text="隐藏", command=border.hide).pack(pady=8)

    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.widgets.roi_border
```

视觉检查：
- 主窗口左上角弹出，三个按钮
- 点"显示边框 (300,300)→(800,600)"——屏幕上 300,300 到 800,600 区域出现红色细边框（可点穿）
- 点"显示全屏边框"——整个屏幕外缘出现红框
- 点"隐藏"——边框消失
- 重复点"显示"——旧边框先被销毁、新的出现（不叠加）

- [ ] **Step 3：提交**

```powershell
git add src/gui/widgets/roi_border.py
git commit -m "feat: 抽出 ROI 边框可视化为 RoiBorder 类"
```

---

## Task 7：抽出系统托盘

**Files:**
- Create: `src/gui/widgets/tray.py`

**职责：** 把 `app.py:47-122` 的 `_make_tray_icon_image` + `_setup_tray` 抽成模块函数。签名保持兼容：`setup_tray(root, on_show, on_quit, tooltip)` 返回控制对象（含 `.stop()`）或 None。

- [ ] **Step 1：写 tray.py 全文**

```python
"""
系统托盘图标（基于 pystray）。

setup_tray 失败（无 pystray / 无 PIL）时返回 None；调用方应优雅处理。
"""

import os
import sys
import threading

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.utils.logger import logger


def make_tray_icon_image():
    """生成 64x64 托盘图标。失败返回 None。"""
    try:
        from PIL import Image, ImageDraw
        w, h = 64, 64
        cx, cy = w // 2, h // 2
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r_outer = min(cx, cy) - 2
        draw.ellipse(
            [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
            fill=(20, 28, 36), outline=(0, 180, 120)
        )
        for i in range(1, 4):
            r = r_outer * i // 4
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                outline=(0, 200, 140), width=1
            )
        draw.line([cx, cy - r_outer, cx, cy + r_outer], fill=(0, 200, 140), width=1)
        draw.line([cx - r_outer, cy, cx + r_outer, cy], fill=(0, 200, 140), width=1)
        draw.pieslice(
            [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
            start=0, end=90,
            fill=(0, 180, 120, 100), outline=(0, 220, 160)
        )
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(0, 255, 170))
        return img
    except Exception:
        try:
            from PIL import Image
            return Image.new("RGBA", (64, 64), (0, 120, 80))
        except Exception:
            return None


class _TrayCtrl:
    """对外暴露的极小接口；只提供 stop()。"""
    def __init__(self, icon):
        self._icon = icon

    def stop(self):
        try:
            self._icon.stop()
        except Exception:
            pass


def setup_tray(root, on_show, on_quit, tooltip="屏幕扫描OCR识别"):
    """创建并启动系统托盘图标，返回控制对象或 None。"""
    try:
        import pystray
    except ImportError:
        logger.warning("未安装 pystray，托盘图标不可用")
        return None

    def _run_on_main(fn):
        try:
            root.after(0, fn)
        except Exception:
            pass

    image = make_tray_icon_image()
    if image is None:
        return None

    menu = pystray.Menu(
        pystray.MenuItem("显示主窗口", lambda: _run_on_main(on_show), default=True),
        pystray.MenuItem("退出", lambda: _run_on_main(on_quit)),
    )
    icon = pystray.Icon("screen_scan_ocr", image, tooltip, menu=menu)

    threading.Thread(target=icon.run, daemon=True).start()
    return _TrayCtrl(icon)


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.title("Tray demo")
    root.geometry("300x200")

    def show():
        root.deiconify()
        root.lift()

    def quit_():
        if tray:
            tray.stop()
        root.destroy()

    tray = setup_tray(root, on_show=show, on_quit=quit_, tooltip="Demo Tray")

    msg = "托盘已启动" if tray else "pystray 不可用，托盘未启动"
    tk.Label(root, text=msg).pack(pady=20)
    tk.Label(root, text="关窗口 → 主窗口隐藏到托盘\n右键托盘 → 选择「退出」").pack()

    if tray:
        root.protocol("WM_DELETE_WINDOW", lambda: root.withdraw())

    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.widgets.tray
```

视觉检查：
- 主窗口出现 + 系统托盘出现一个圆形雷达图标（鼠标悬停 tooltip "Demo Tray"）
- 关闭主窗口（X）→ 主窗口消失但托盘还在
- 右键托盘 → 弹出菜单 "显示主窗口" / "退出"
- 点"显示主窗口" → 主窗口重现
- 点"退出" → 托盘和主窗口都消失

- [ ] **Step 3：提交**

```powershell
git add src/gui/widgets/tray.py
git commit -m "feat: 抽出系统托盘到 widgets/tray.py"
```

---

# Phase 3：Sidebar + Statusbar（Spec §1 + §3）

## Task 8：Sidebar 导航

**Files:**
- Create: `src/gui/sidebar.py`

**职责：** 4 个图标+文字纵向按钮，点击触发 `on_select(name)` 回调；自管理选中态高亮（通过 `Sidebar.TButton` / `SidebarActive.TButton` 两个 style 切换）。

- [ ] **Step 1：写 sidebar.py 全文**

```python
"""
左侧导航：4 个视图切换按钮。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.theme import (
    UI_FONT, FONT_SIZE_BASE, COLOR_BG_SIDEBAR, COLOR_TEXT_DIM,
)


# 视图键 → (图标 unicode, 显示标签)
VIEW_ITEMS = [
    ("scan",     "◎", "扫描"),
    ("settings", "⚙", "设置"),
    ("hotkey",   "⌨", "热键"),
    ("about",    "ⓘ", "关于"),
]


class Sidebar(ttk.Frame):
    def __init__(self, parent, on_select):
        super().__init__(parent, style="Sidebar.TFrame", padding=(6, 12))
        self._on_select = on_select
        self._buttons = {}
        self._active = None
        self._build()

    def _build(self):
        # 顶部 logo / 标题区（占位）
        title = tk.Label(self, text="✏  屏幕扫描", bg=COLOR_BG_SIDEBAR,
                         fg=COLOR_TEXT_DIM, font=(UI_FONT, FONT_SIZE_BASE))
        title.pack(pady=(0, 16))

        for key, icon, label in VIEW_ITEMS:
            btn = ttk.Button(
                self,
                text=f"{icon}\n{label}",
                style="Sidebar.TButton",
                command=lambda k=key: self._click(k),
                width=8,
            )
            btn.pack(fill="x", pady=2)
            self._buttons[key] = btn

    def set_active(self, key):
        """更新选中态高亮。"""
        if key not in self._buttons:
            return
        if self._active and self._active in self._buttons:
            self._buttons[self._active].configure(style="Sidebar.TButton")
        self._buttons[key].configure(style="SidebarActive.TButton")
        self._active = key

    def _click(self, key):
        self.set_active(key)
        if self._on_select:
            self._on_select(key)


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.gui.theme import apply

    root = tk.Tk()
    root.title("Sidebar demo")
    root.geometry("500x400")
    apply(root)

    # 模拟主区
    sb = Sidebar(root, on_select=lambda k: status.config(text=f"切到: {k}"))
    sb.pack(side="left", fill="y")

    main = tk.Frame(root, bg="#0f1420")
    main.pack(side="left", fill="both", expand=True)
    status = tk.Label(main, text="点击侧栏按钮", bg="#0f1420",
                      fg="white", font=(UI_FONT, 12))
    status.pack(expand=True)

    sb.set_active("scan")

    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.sidebar
```

视觉检查：
- 左侧深色侧栏，顶部 "✏ 屏幕扫描"
- 4 个按钮（扫描/设置/热键/关于），每个有图标 + 标签
- 启动时"扫描"高亮（蓝底白字）、其它三个深底灰字
- 点"设置" → "设置"按钮变蓝、"扫描"恢复深色；右侧文字变 `切到: settings`
- 依次点其它按钮，行为一致

- [ ] **Step 3：提交**

```powershell
git add src/gui/sidebar.py
git commit -m "feat: 添加 Sidebar 导航 widget"
```

---

## Task 9：StatusBar 底栏

**Files:**
- Create: `src/gui/statusbar.py`

**职责：** 底部一行/两行：
- 左侧：●运行中 / 内存:N MB / 版本:1.0.0 / 引擎:PaddleOCR 3.x
- 右侧：[开始扫描] [停止扫描] [声音提醒] [重置配置]

提供 `set_running(bool)` / `set_memory(mb)` / `set_busy(bool)` 三个 setter；按钮回调通过构造注入。也包含 `_get_memory_mb()` 工具函数（从 `app.py:219-263` 搬过来）。

- [ ] **Step 1：写 statusbar.py 全文**

```python
"""
底部状态/控制栏。

左侧：●状态指示 / 内存 / 版本 / 引擎
右侧：开始扫描 / 停止扫描 / 声音提醒切换 / 重置配置

set_running(bool)     → 切换 ●颜色 + 状态文字
set_memory(mb)        → 刷新内存数字
set_busy(starting)    → True：开始按钮 disabled、文字"初始化中..."
"""

import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk
from ctypes import wintypes

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.theme import (
    UI_FONT, FONT_SIZE_BASE, FONT_SIZE_TITLE,
    COLOR_BG_CARD, COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING,
)


APP_VERSION = "1.0.0"
ENGINE_LABEL = "PaddleOCR 3.x"


def get_memory_mb():
    """返回当前进程 RSS (MB)，失败返回 None。Win32 API 实现，无 psutil 依赖。"""
    try:
        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        pmc = PMC()
        pmc.cb = ctypes.sizeof(pmc)
        handle = kernel32.GetCurrentProcess()

        K32 = getattr(kernel32, 'K32GetProcessMemoryInfo', None)
        if K32 is not None:
            K32.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            K32.restype = wintypes.BOOL
            if K32(handle, ctypes.byref(pmc), pmc.cb):
                return pmc.WorkingSetSize / (1024 * 1024)

        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
            return pmc.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return None


class StatusBar(ttk.Frame):
    def __init__(self, parent, on_start, on_stop, on_toggle_sound, on_reset):
        super().__init__(parent, style="Statusbar.TFrame", padding=(14, 8))
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_toggle_sound = on_toggle_sound
        self._on_reset = on_reset
        self._sound_var = tk.BooleanVar(value=True)
        self._build()
        self.set_running(False)

    def _build(self):
        # ----- 左侧元信息 -----
        left = ttk.Frame(self, style="Statusbar.TFrame")
        left.pack(side="left")

        self._dot = tk.Label(left, text="●", bg=COLOR_BG_CARD,
                             fg=COLOR_DANGER, font=(UI_FONT, 14))
        self._dot.pack(side="left", padx=(0, 4))
        self._lbl_status = ttk.Label(left, text="已停止", style="Statusbar.TLabel",
                                      font=(UI_FONT, FONT_SIZE_BASE, "bold"))
        self._lbl_status.pack(side="left", padx=(0, 18))

        ttk.Label(left, text="内存:", style="Dim.TLabel").pack(side="left")
        self._lbl_mem = ttk.Label(left, text="-- MB", style="Statusbar.TLabel")
        self._lbl_mem.pack(side="left", padx=(2, 18))

        ttk.Label(left, text=f"版本: {APP_VERSION}", style="Dim.TLabel").pack(
            side="left", padx=(0, 14))
        ttk.Label(left, text=f"引擎: {ENGINE_LABEL}", style="Dim.TLabel").pack(
            side="left")

        # ----- 右侧操作 -----
        right = ttk.Frame(self, style="Statusbar.TFrame")
        right.pack(side="right")

        ttk.Button(right, text="重置配置",
                   command=self._on_reset).pack(side="right", padx=(6, 0))
        ttk.Checkbutton(right, text="声音提醒", variable=self._sound_var,
                        command=lambda: self._on_toggle_sound(self._sound_var.get()),
                        style="TCheckbutton").pack(side="right", padx=(6, 6))

        # 控制按钮
        self._btn_stop = ttk.Button(right, text="停止 Ctrl+Alt+2",
                                     style="Danger.TButton",
                                     command=self._on_stop, state="disabled")
        self._btn_stop.pack(side="right", padx=(6, 6))
        self._btn_start = ttk.Button(right, text="开始扫描 Ctrl+Alt+1",
                                      style="Primary.TButton",
                                      command=self._on_start)
        self._btn_start.pack(side="right")

    # ----- 状态 setter -----

    def set_running(self, running):
        if running:
            self._dot.config(fg=COLOR_SUCCESS)
            self._lbl_status.config(text="运行中")
            self._btn_start.config(state="disabled")
            self._btn_stop.config(state="normal")
        else:
            self._dot.config(fg=COLOR_DANGER)
            self._lbl_status.config(text="已停止")
            self._btn_start.config(state="normal")
            self._btn_stop.config(state="disabled")

    def set_busy(self, starting):
        """starting=True：OCR 初始化中；按钮全 disabled，状态显示初始化中。"""
        if starting:
            self._dot.config(fg=COLOR_WARNING)
            self._lbl_status.config(text="初始化中...")
            self._btn_start.config(state="disabled")
            self._btn_stop.config(state="disabled")

    def set_memory(self, mb):
        if mb is None:
            self._lbl_mem.config(text="-- MB")
        else:
            self._lbl_mem.config(text=f"{mb:.1f} MB")

    def set_sound(self, enabled):
        """同步声音开关到外部存的真值（启动时调一次）。"""
        self._sound_var.set(bool(enabled))


# ---------------------------------------------------------------------------
# 演示
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.gui.theme import apply

    root = tk.Tk()
    root.title("StatusBar demo")
    root.geometry("900x100")
    apply(root)

    bar = StatusBar(root,
                    on_start=lambda: print("on_start"),
                    on_stop=lambda: print("on_stop"),
                    on_toggle_sound=lambda v: print(f"on_toggle_sound: {v}"),
                    on_reset=lambda: print("on_reset"))
    bar.pack(side="bottom", fill="x")

    # 触发不同状态
    btn_frame = tk.Frame(root, bg="#0f1420")
    btn_frame.pack(fill="x", pady=4)
    tk.Button(btn_frame, text="set_running(False)",
              command=lambda: bar.set_running(False)).pack(side="left", padx=4)
    tk.Button(btn_frame, text="set_busy(True)",
              command=lambda: bar.set_busy(True)).pack(side="left", padx=4)
    tk.Button(btn_frame, text="set_running(True)",
              command=lambda: bar.set_running(True)).pack(side="left", padx=4)
    tk.Button(btn_frame, text="set_memory(83.1)",
              command=lambda: bar.set_memory(83.1)).pack(side="left", padx=4)

    # 真实内存
    mb = get_memory_mb()
    print(f"当前进程 RSS: {mb} MB")
    bar.set_memory(mb)

    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.statusbar
```

视觉检查：
- 终端打印当前进程 RSS（数字）
- 底部状态栏：左侧 ●(红) 已停止 / 内存:数字 MB / 版本 / 引擎；右侧 [开始扫描][停止][☑声音提醒][重置配置]
- 启动时停止按钮灰色（disabled）
- 点"set_busy(True)" → ●变黄、文字"初始化中..."、两个按钮都灰
- 点"set_running(True)" → ●变绿、文字"运行中"、停止按钮变红可点、开始按钮灰
- 点"set_running(False)" → 回到初始
- 点"set_memory(83.1)" → 内存显示 "83.1 MB"
- 点开始/停止/声音提醒/重置 → 终端各打印一行

- [ ] **Step 3：提交**

```powershell
git add src/gui/statusbar.py
git commit -m "feat: 添加 StatusBar widget（含内存监控）"
```

---

# Phase 4：4 个视图（Spec §2）

## Task 10：BaseView

**Files:**
- Create: `src/gui/views/base.py`

**职责：** 视图基类。最小接口：所有 View 是 `ttk.Frame`，构造接收 `parent` + `main_window` 引用，提供 `mount()` / `unmount()` 钩子（默认空实现，子类按需重写——比如 ScanView 在 mount 时刷新匹配记录面板）。

- [ ] **Step 1：写 base.py 全文**

```python
"""
所有视图的基类。

子类构造接收 (parent, main_window)；main_window 用来读 config / 触发全局动作。
mount() / unmount() 是空钩子，需要时重写。
"""

from tkinter import ttk


class BaseView(ttk.Frame):
    """所有视图共享的基类。"""

    VIEW_KEY = ""    # 子类必须覆盖：'scan' / 'settings' / 'hotkey' / 'about'

    def __init__(self, parent, main_window):
        super().__init__(parent, style="Content.TFrame")
        self.main_window = main_window
        self.config = main_window.config_obj  # type: ignore[has-type]
        self._build()

    # ----- 子类 hook -----

    def _build(self):
        """子类在这里构造 widget。"""
        pass

    def mount(self):
        """View 被切到前台时调用。可用于刷新依赖外部状态的 widget。"""
        pass

    def unmount(self):
        """View 被切走时调用。可用于停定时器或保存状态。"""
        pass
```

- [ ] **Step 2：语法检查**

```powershell
python -c "import ast; ast.parse(open('src/gui/views/base.py', encoding='utf-8').read()); print('base.py syntax OK')"
```

期望：`base.py syntax OK`。

- [ ] **Step 3：提交**

```powershell
git add src/gui/views/base.py
git commit -m "feat: 添加 BaseView 视图基类"
```

---

## Task 11：ScanView 扫描视图（最大）

**Files:**
- Create: `src/gui/views/scan_view.py`

**职责：** 扫描视图布局——左侧"扫描配置"卡（ROI / 间隔 / OCR / 词库 / 显示时长），右侧上下两栏（LogPanel + MatchRecords，由 MainWindow 注入）。配置面板内的所有控件 `_load_settings` / `_save_settings` 自管理。

> **注意：** 这是计划里最长的代码块。部分控件（ROI 选择 / 词库浏览-编辑 / 滑块取整）需要触发 MainWindow 的方法或文件对话框。MainWindow 必须提供 `show_message(level, text)` / `do_roi_select_now()` / `do_save_roi_preset()` / `browse_banlist()` / `edit_banlist()` 等方法——这些会在 Task 15-16 实现。

- [ ] **Step 1：写 scan_view.py 全文**

```python
"""
扫描视图：简单/常用配置 + 日志面板 + 匹配记录面板。

布局：
    +------------------------+--------------------+
    |   扫描配置 (cfg panel)  |   运行日志          |
    |   ROI / 间隔 / OCR /    |                    |
    |   词库 / 显示时长       +--------------------+
    |                        |   匹配记录 (最近10)  |
    +------------------------+--------------------+
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.views.base import BaseView
from src.gui.theme import (
    UI_FONT, FONT_SIZE_BASE, FONT_SIZE_TITLE,
    COLOR_BG_CARD, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_PRIMARY,
)
from src.config.config import DEFAULT_BANLIST_FILE


class ScanView(BaseView):
    VIEW_KEY = "scan"

    def _build(self):
        self._init_vars()
        self._create_layout()
        self._load_settings()

    # -----------------------------------------------------------------------
    # Tk 变量
    # -----------------------------------------------------------------------

    def _init_vars(self):
        self.var_enable_roi      = tk.BooleanVar()
        self.var_remember_roi    = tk.BooleanVar(value=True)
        self.var_roi_preset      = tk.StringVar()
        self.var_interval        = tk.DoubleVar(value=2.0)
        self.var_lang            = tk.StringVar(value="ch")
        self.var_gpu             = tk.BooleanVar(value=True)
        self.var_confidence      = tk.DoubleVar(value=0.3)
        self.var_banlist         = tk.StringVar(value=DEFAULT_BANLIST_FILE)
        self.var_duration        = tk.DoubleVar(value=3.0)

    # -----------------------------------------------------------------------
    # 布局
    # -----------------------------------------------------------------------

    def _create_layout(self):
        # 整体 padding
        outer = ttk.Frame(self, style="Content.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        # 左：扫描配置卡
        cfg_card = ttk.Frame(outer, style="Card.TFrame", padding=12)
        cfg_card.pack(side="left", fill="y", padx=(0, 8))
        cfg_card.config(width=320)
        cfg_card.pack_propagate(False)
        self._build_config_panel(cfg_card)

        # 右：日志 + 匹配记录（上下两栏）
        right = ttk.Frame(outer, style="Content.TFrame")
        right.pack(side="left", fill="both", expand=True)

        # MainWindow 持有 LogPanel / MatchRecords 实例；这里只占位
        self._log_slot = ttk.Frame(right, style="Content.TFrame")
        self._log_slot.pack(fill="both", expand=True, pady=(0, 8))
        self._match_slot = ttk.Frame(right, style="Content.TFrame")
        self._match_slot.pack(fill="both", expand=True)

    def attach_panels(self, log_panel, match_panel):
        """MainWindow 在创建本 View 后调用一次，把常驻面板挂进来。

        log_panel / match_panel 的 master 仍是 MainWindow.content（创建时的
        parent）；mount() 里用 pack(in_=self._log_slot) 把它们布局到 ScanView
        的占位 slot 中——这是 tkinter 跨容器布局的标准模式。
        """
        self.log_panel = log_panel
        self.match_panel = match_panel

    def mount(self):
        """切到本视图时把面板 pack 进 slot。"""
        if hasattr(self, "log_panel"):
            self.log_panel.pack(in_=self._log_slot, fill="both", expand=True)
        if hasattr(self, "match_panel"):
            self.match_panel.pack(in_=self._match_slot, fill="both", expand=True)

    def unmount(self):
        if hasattr(self, "log_panel"):
            self.log_panel.pack_forget()
        if hasattr(self, "match_panel"):
            self.match_panel.pack_forget()

    # -----------------------------------------------------------------------
    # 配置面板
    # -----------------------------------------------------------------------

    def _build_config_panel(self, parent):
        ttk.Label(parent, text="扫描配置", style="Header.TLabel").pack(
            anchor="w", pady=(0, 12))

        self._section(parent, "扫描区域")
        r = self._row(parent)
        ttk.Checkbutton(r, text="启用 ROI", variable=self.var_enable_roi,
                        style="TCheckbutton").pack(side="left")
        ttk.Checkbutton(r, text="记住", variable=self.var_remember_roi,
                        style="TCheckbutton").pack(side="left", padx=(10, 0))

        self._sub(parent, "ROI 预设")
        r = self._row(parent)
        self._combo_preset = ttk.Combobox(r, textvariable=self.var_roi_preset,
                                           width=14, state="readonly")
        self._combo_preset.pack(side="left")
        self._combo_preset.bind("<<ComboboxSelected>>", self._on_preset_selected)
        ttk.Button(r, text="保存当前",
                   command=self._save_preset).pack(side="left", padx=(6, 0))

        self._section(parent, "扫描节奏")
        self._sub(parent, "扫描间隔（秒）")
        r = self._row(parent)
        ttk.Scale(r, from_=0.5, to=15, variable=self.var_interval, length=180,
                  command=self._on_interval_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_interval).pack(side="left", padx=(6, 0))

        self._section(parent, "OCR 识别")
        r = self._row(parent)
        ttk.Label(r, text="语言", style="Dim.TLabel").pack(side="left")
        ttk.Combobox(r, textvariable=self.var_lang, width=8, state="readonly",
                     values=("ch", "en", "japan", "korean")).pack(side="left",
                                                                    padx=(6, 14))
        ttk.Checkbutton(r, text="GPU 加速", variable=self.var_gpu,
                        style="TCheckbutton").pack(side="left")

        self._sub(parent, "最小置信度")
        r = self._row(parent)
        ttk.Scale(r, from_=0, to=1, variable=self.var_confidence, length=180,
                  command=self._on_conf_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_confidence).pack(side="left", padx=(6, 0))

        self._section(parent, "关键词匹配")
        self._sub(parent, "词库文件")
        r = self._row(parent)
        ttk.Entry(r, textvariable=self.var_banlist).pack(side="left",
                                                           fill="x", expand=True)
        ttk.Button(r, text="浏览…",
                   command=self._browse_banlist).pack(side="left", padx=(4, 0))
        ttk.Button(r, text="编辑",
                   command=self._edit_banlist).pack(side="left", padx=(4, 0))

        self._sub(parent, "匹配后显示时长（秒）")
        r = self._row(parent)
        ttk.Scale(r, from_=1, to=10, variable=self.var_duration, length=180,
                  command=self._on_dur_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_duration).pack(side="left", padx=(6, 0))

    # ----- 布局辅助 -----

    def _section(self, parent, text):
        ttk.Label(parent, text=text, style="Section.TLabel").pack(
            anchor="w", pady=(12, 4))

    def _sub(self, parent, text):
        ttk.Label(parent, text=text, style="Dim.TLabel").pack(
            anchor="w", pady=(4, 2))

    def _row(self, parent):
        r = ttk.Frame(parent, style="Card.TFrame")
        r.pack(fill="x", pady=2)
        return r

    # -----------------------------------------------------------------------
    # 滑块取整 / 值约束
    # -----------------------------------------------------------------------

    def _on_interval_scale(self, val):
        try:
            v = round(float(val) * 2) / 2
            self.var_interval.set(max(0.5, min(15.0, v)))
        except (ValueError, TypeError):
            pass

    def _on_conf_scale(self, val):
        try:
            v = round(float(val) / 0.05) * 0.05
            self.var_confidence.set(round(v, 2))
        except (ValueError, TypeError):
            pass

    def _on_dur_scale(self, val):
        try:
            v = round(float(val) * 2) / 2
            self.var_duration.set(max(1.0, min(10.0, v)))
        except (ValueError, TypeError):
            pass

    # -----------------------------------------------------------------------
    # ROI 预设
    # -----------------------------------------------------------------------

    def refresh_presets(self):
        presets = self.config.get("scan.roi_presets") or {}
        names = list(presets.keys())
        self._combo_preset["values"] = names
        if names and not self.var_roi_preset.get():
            self._combo_preset.current(0)

    def _on_preset_selected(self, event=None):
        name = self.var_roi_preset.get()
        presets = self.config.get("scan.roi_presets") or {}
        roi = presets.get(name)
        if roi:
            self.main_window.apply_roi_preset(name, tuple(roi))

    def _save_preset(self):
        self.main_window.save_current_roi_preset()

    # -----------------------------------------------------------------------
    # 词库浏览/编辑（委托给 MainWindow）
    # -----------------------------------------------------------------------

    def _browse_banlist(self):
        path = self.main_window.browse_banlist(self.var_banlist.get())
        if path:
            self.var_banlist.set(path)
            self._save_settings()

    def _edit_banlist(self):
        self.main_window.edit_banlist(self.var_banlist.get())

    # -----------------------------------------------------------------------
    # 配置读写
    # -----------------------------------------------------------------------

    def _load_settings(self):
        cfg = self.config
        self.var_enable_roi.set(cfg.get("scan.roi") is not None)
        self.var_remember_roi.set(True)
        self.var_interval.set(cfg.get("scan.interval_seconds"))
        self.var_lang.set(cfg.get("ocr.language"))
        self.var_gpu.set(cfg.get("gpu.enabled"))
        self.var_confidence.set(cfg.get("ocr.min_confidence"))
        self.var_banlist.set(cfg.get("files.banlist_file", DEFAULT_BANLIST_FILE))
        self.var_duration.set(cfg.get("matching.display_duration"))
        self.refresh_presets()

    def _save_settings(self):
        cfg = self.config
        cfg.set("scan.interval_seconds", self.var_interval.get())
        cfg.set("ocr.language", self.var_lang.get())
        cfg.set("gpu.enabled", self.var_gpu.get())
        cfg.set("ocr.min_confidence", round(self.var_confidence.get(), 2))
        cfg.set("files.banlist_file", self.var_banlist.get())
        cfg.set("matching.display_duration", self.var_duration.get())
        cfg.save()

    def save_settings(self):
        """对外公开（MainWindow 在 on_start 前调用）。"""
        self._save_settings()
```

- [ ] **Step 2：语法检查**

```powershell
python -c "import ast; ast.parse(open('src/gui/views/scan_view.py', encoding='utf-8').read()); print('scan_view.py syntax OK')"
```

期望：`scan_view.py syntax OK`。

- [ ] **Step 3：提交**

```powershell
git add src/gui/views/scan_view.py
git commit -m "feat: 添加 ScanView 扫描视图"
```

---

## Task 12：SettingsView 设置视图

**Files:**
- Create: `src/gui/views/settings_view.py`

**职责：** 高级配置——帧差检测阈值、浮窗外观（字号/位置/音效）、图像反色、日志级别、配置文件路径展示。

- [ ] **Step 1：写 settings_view.py 全文**

```python
"""
设置视图：高级配置（一次配好基本不动）。

包含：
- 帧差检测：MSE 阈值（0 = 每次都 OCR）
- 浮窗外观：字号、位置、音效
- OCR 进阶：图像反色
- 日志级别
- 配置文件路径展示（只读）
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.views.base import BaseView
from src.gui.theme import COLOR_TEXT_DIM


POSITION_DISPLAY = {"center": "居中", "top": "顶部", "bottom": "底部"}
POSITION_VALUE = {v: k for k, v in POSITION_DISPLAY.items()}


class SettingsView(BaseView):
    VIEW_KEY = "settings"

    def _build(self):
        self._init_vars()
        self._create_layout()
        self._load_settings()
        self._wire_save()

    def _init_vars(self):
        self.var_diff_threshold = tk.DoubleVar(value=5.0)
        self.var_fontsize = tk.IntVar(value=18)
        self.var_position = tk.StringVar(value="居中")
        self.var_sound = tk.BooleanVar(value=True)
        self.var_invert = tk.BooleanVar(value=False)
        self.var_log_level = tk.StringVar(value="INFO")

    def _create_layout(self):
        outer = ttk.Frame(self, style="Content.TFrame", padding=20)
        outer.pack(fill="both", expand=True)

        card = ttk.Frame(outer, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="设置（高级）", style="Header.TLabel").pack(
            anchor="w", pady=(0, 12))

        # ----- 帧差检测 -----
        self._section(card, "帧差检测")
        self._sub(card, "MSE 阈值（0 = 每次都 OCR）")
        r = self._row(card)
        ttk.Scale(r, from_=0, to=50, variable=self.var_diff_threshold, length=240,
                  command=self._on_diff_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_diff_threshold).pack(side="left", padx=(8, 0))

        # ----- 浮窗外观 -----
        self._section(card, "浮窗外观")
        self._sub(card, "字号（px）")
        r = self._row(card)
        ttk.Scale(r, from_=10, to=36, variable=self.var_fontsize, length=240,
                  command=self._on_fs_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_fontsize).pack(side="left", padx=(8, 0))

        self._sub(card, "位置")
        ttk.Combobox(card, textvariable=self.var_position, width=10,
                     state="readonly",
                     values=("居中", "顶部", "底部")).pack(anchor="w", pady=2)

        ttk.Checkbutton(card, text="音效提醒", variable=self.var_sound,
                        style="TCheckbutton").pack(anchor="w", pady=(8, 0))

        # ----- OCR 进阶 -----
        self._section(card, "OCR 进阶")
        ttk.Checkbutton(card, text="图像反色（黑底白字时启用）",
                        variable=self.var_invert,
                        style="TCheckbutton").pack(anchor="w", pady=2)

        # ----- 日志 -----
        self._section(card, "日志")
        self._sub(card, "日志级别")
        ttk.Combobox(card, textvariable=self.var_log_level, width=10,
                     state="readonly",
                     values=("DEBUG", "INFO", "WARNING", "ERROR")).pack(
            anchor="w", pady=2)

        # ----- 配置文件路径（只读） -----
        self._section(card, "配置文件")
        cfg_path = getattr(self.config, "_path", "(未加载)")
        ttk.Label(card, text=cfg_path, style="Dim.TLabel").pack(
            anchor="w", pady=(0, 8))

    def _section(self, parent, text):
        ttk.Label(parent, text=text, style="Section.TLabel").pack(
            anchor="w", pady=(14, 4))

    def _sub(self, parent, text):
        ttk.Label(parent, text=text, style="Dim.TLabel").pack(
            anchor="w", pady=(4, 2))

    def _row(self, parent):
        r = ttk.Frame(parent, style="Card.TFrame")
        r.pack(fill="x", pady=2)
        return r

    # ----- 滑块取整 -----

    def _on_diff_scale(self, val):
        try:
            self.var_diff_threshold.set(round(float(val), 1))
        except (ValueError, TypeError):
            pass

    def _on_fs_scale(self, val):
        try:
            self.var_fontsize.set(max(10, min(36, round(float(val)))))
        except (ValueError, TypeError):
            pass

    # ----- 配置读写 -----

    def _load_settings(self):
        cfg = self.config
        self.var_diff_threshold.set(cfg.get("scan.diff_threshold"))
        self.var_fontsize.set(cfg.get("matching.font_size"))
        self.var_position.set(POSITION_DISPLAY.get(cfg.get("matching.position"),
                                                     "居中"))
        self.var_sound.set(cfg.get("matching.enable_sound"))
        self.var_invert.set(cfg.get("ocr.enable_image_invert"))
        self.var_log_level.set(cfg.get("logging.level", "INFO"))

    def _save_settings(self, *_):
        cfg = self.config
        cfg.set("scan.diff_threshold", self.var_diff_threshold.get())
        cfg.set("matching.font_size", self.var_fontsize.get())
        cfg.set("matching.position",
                POSITION_VALUE.get(self.var_position.get(), "center"))
        cfg.set("matching.enable_sound", self.var_sound.get())
        cfg.set("ocr.enable_image_invert", self.var_invert.get())
        cfg.set("logging.level", self.var_log_level.get())
        cfg.save()
        # 通知 MainWindow 同步状态栏的声音开关
        if hasattr(self.main_window, "on_settings_changed"):
            self.main_window.on_settings_changed()

    def _wire_save(self):
        """所有变量变化时自动保存（避免依赖外部 save_settings 调用）。"""
        for v in (self.var_diff_threshold, self.var_fontsize, self.var_position,
                  self.var_sound, self.var_invert, self.var_log_level):
            v.trace_add("write", self._save_settings)

    def reload_from_config(self):
        """配置外部被重置时调用（比如 StatusBar 的"重置配置"）。"""
        # 解开 trace 防止重置过程触发 save 反向写
        self._load_settings()
```

- [ ] **Step 2：语法检查**

```powershell
python -c "import ast; ast.parse(open('src/gui/views/settings_view.py', encoding='utf-8').read()); print('settings_view.py syntax OK')"
```

期望：`settings_view.py syntax OK`。

- [ ] **Step 3：提交**

```powershell
git add src/gui/views/settings_view.py
git commit -m "feat: 添加 SettingsView 设置视图"
```

---

## Task 13：HotkeyView 热键视图

**Files:**
- Create: `src/gui/views/hotkey_view.py`

**职责：** Phase 1 只读——展示当前热键 + 启用/禁用开关。改键留作未来。

- [ ] **Step 1：写 hotkey_view.py 全文**

```python
"""
热键视图：当前 phase 1 只读，仅展示热键并允许整体启用/禁用。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.views.base import BaseView


HOTKEYS = [
    ("Ctrl + Alt + 1", "开始扫描"),
    ("Ctrl + Alt + 2", "停止扫描"),
]


class HotkeyView(BaseView):
    VIEW_KEY = "hotkey"

    def _build(self):
        self._create_layout()

    def _create_layout(self):
        outer = ttk.Frame(self, style="Content.TFrame", padding=20)
        outer.pack(fill="both", expand=True)

        card = ttk.Frame(outer, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="热键", style="Header.TLabel").pack(
            anchor="w", pady=(0, 12))

        ttk.Label(card,
                  text="全局热键在 Windows 上需要管理员权限（依赖 keyboard 库）。",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 16))

        for combo, desc in HOTKEYS:
            row = ttk.Frame(card, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=combo, style="Section.TLabel",
                      width=22).pack(side="left")
            ttk.Label(row, text=desc, style="Card.TLabel").pack(side="left")

        ttk.Label(card, text="（修改快捷键功能未来开放）",
                  style="Dim.TLabel").pack(anchor="w", pady=(20, 0))
```

- [ ] **Step 2：语法检查**

```powershell
python -c "import ast; ast.parse(open('src/gui/views/hotkey_view.py', encoding='utf-8').read()); print('hotkey_view.py syntax OK')"
```

期望：`hotkey_view.py syntax OK`。

- [ ] **Step 3：提交**

```powershell
git add src/gui/views/hotkey_view.py
git commit -m "feat: 添加 HotkeyView 热键视图（phase 1 只读）"
```

---

## Task 14：AboutView 关于视图

**Files:**
- Create: `src/gui/views/about_view.py`

**职责：** 项目信息——名称、版本、引擎、简短说明。

- [ ] **Step 1：写 about_view.py 全文**

```python
"""
关于视图：项目信息。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_THIS))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gui.views.base import BaseView
from src.gui.statusbar import APP_VERSION, ENGINE_LABEL


ABOUT_DESCRIPTION = (
    "屏幕扫描 OCR 识别系统：定时截图、PaddleOCR 识别、关键词匹配、"
    "屏幕浮窗弹出提示。支持 ROI 区域、帧差跳过、GPU 加速、全局热键。"
)


class AboutView(BaseView):
    VIEW_KEY = "about"

    def _build(self):
        outer = ttk.Frame(self, style="Content.TFrame", padding=20)
        outer.pack(fill="both", expand=True)

        card = ttk.Frame(outer, style="Card.TFrame", padding=24)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="✏ 屏幕扫描 OCR 识别系统",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(card, text=f"版本 {APP_VERSION}    引擎 {ENGINE_LABEL}",
                  style="Dim.TLabel").pack(anchor="w", pady=(4, 16))

        ttk.Label(card, text=ABOUT_DESCRIPTION, style="Card.TLabel",
                  wraplength=520, justify="left").pack(anchor="w", pady=(0, 12))

        ttk.Label(card, text="模块组成", style="Section.TLabel").pack(
            anchor="w", pady=(12, 4))
        for line in (
            "Pipeline：capture → diff_gate → ocr_stage → matcher",
            "Overlay：持久透明浮窗 + 累积匹配 + 和弦音效",
            "Hotkey：全局 Ctrl+Alt+1/2 启停（依赖管理员权限）",
            "Tray：右下角托盘，关窗缩托盘、右键退出",
        ):
            ttk.Label(card, text=f"·  {line}", style="Card.TLabel").pack(anchor="w")
```

- [ ] **Step 2：语法检查**

```powershell
python -c "import ast; ast.parse(open('src/gui/views/about_view.py', encoding='utf-8').read()); print('about_view.py syntax OK')"
```

期望：`about_view.py syntax OK`。

- [ ] **Step 3：提交**

```powershell
git add src/gui/views/about_view.py
git commit -m "feat: 添加 AboutView 关于视图"
```

---

# Phase 5：MainWindow 协调（Spec §5）

## Task 15：MainWindow 骨架与视图切换

**Files:**
- Create: `src/gui/main_window.py`

**职责（本任务范围）：** MainWindow 类骨架 —— 构造时建 sidebar / statusbar / 4 个 view 实例 + log_panel + match_panel；实现 `_switch_view(name)` + 一些被 view 调用的方法（`apply_roi_preset` / `save_current_roi_preset` / `browse_banlist` / `edit_banlist` / `on_settings_changed` / `show_message`）的占位实现。**不包含 scan_loop / pipeline / tray / hotkey**——下个 Task 接入。

- [ ] **Step 1：写 main_window.py（v1：仅切视图 + view 接口）**

```python
"""
主窗口：组装 sidebar + content + statusbar，管理视图切换与全局动作。

本文件目标超过 600 行，但都是协调/分发逻辑，没有可拆的子单元——
拆出去会让"读完一处看完整流程"的能力变差。
"""

import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

# 项目根入 sys.path（让 from defaults / shared 都能 import）
_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.config.config import config, DEFAULT_BANLIST_FILE, PROJECT_ROOT
from src.utils.logger import logger, configure_from_config
from src.gui import theme
from src.gui.sidebar import Sidebar
from src.gui.statusbar import StatusBar, get_memory_mb
from src.gui.widgets.log_panel import LogPanel
from src.gui.widgets.match_records import MatchRecords
from src.gui.views.scan_view import ScanView
from src.gui.views.settings_view import SettingsView
from src.gui.views.hotkey_view import HotkeyView
from src.gui.views.about_view import AboutView


class MainWindow:
    """协调者：持有所有跨视图状态、调度扫描线程、切视图。"""

    def __init__(self, root):
        self.root = root
        self.root.title("屏幕扫描OCR识别系统")
        self.root.geometry("1100x720")

        # ---- 配置 ----
        config.load()
        configure_from_config(config)
        self.config_obj = config   # 让 BaseView 通过 main_window.config_obj 访问

        # ---- 主题 ----
        theme.apply(self.root)

        # ---- 跨视图常驻状态 ----
        self.log_queue = queue.Queue(maxsize=1000)
        self.match_records = deque(maxlen=10)

        # ---- 扫描相关（Task 16 接入实际逻辑） ----
        self.is_running = False
        self.scan_thread = None
        self.stop_event = threading.Event()
        self.roi = None
        self.pipeline = None       # Task 16 实例化
        self.overlay = None        # Task 16 实例化
        self.roi_border = None     # Task 16 实例化
        self.tray = None           # Task 16 启动
        self.hotkey_mgr = None     # Task 16 启动

        # ---- 构建 UI ----
        self._build_layout()
        self._build_views()
        self._switch_view("scan")

        # ---- 关闭事件（Task 16 加 watchdog 清理） ----
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- 内存定时刷新 ----
        self._schedule_memory_update()

        # ---- 日志队列消费（Task 16 启动） ----
        self._setup_gui_logger()
        self._drain_log_queue()

    # =======================================================================
    # 布局
    # =======================================================================

    def _build_layout(self):
        # 三段式：sidebar | content | (statusbar 在 root 底部)
        self.statusbar = StatusBar(
            self.root,
            on_start=self.on_start,
            on_stop=self.on_stop,
            on_toggle_sound=self._on_toggle_sound,
            on_reset=self._reset_config,
        )
        self.statusbar.pack(side="bottom", fill="x")
        self.statusbar.set_sound(config.get("matching.enable_sound"))

        body = ttk.Frame(self.root, style="TFrame")
        body.pack(side="top", fill="both", expand=True)

        self.sidebar = Sidebar(body, on_select=self._switch_view)
        self.sidebar.pack(side="left", fill="y")

        self.content = ttk.Frame(body, style="Content.TFrame")
        self.content.pack(side="left", fill="both", expand=True)

        # 跨视图常驻 widget
        self.log_panel = LogPanel(self.content, on_clear=lambda: None)
        self.match_panel = MatchRecords(self.content, on_clear=self._clear_match_records)

    def _build_views(self):
        self._views = {
            "scan":     ScanView(self.content, self),
            "settings": SettingsView(self.content, self),
            "hotkey":   HotkeyView(self.content, self),
            "about":    AboutView(self.content, self),
        }
        # 把常驻面板挂给 ScanView（仅 ScanView 显示它们）
        self._views["scan"].attach_panels(self.log_panel, self.match_panel)
        self._current_view = None

    # =======================================================================
    # 视图切换
    # =======================================================================

    def _switch_view(self, name):
        if name not in self._views:
            return
        if self._current_view is not None:
            self._current_view.unmount()
            self._current_view.pack_forget()
        view = self._views[name]
        view.pack(fill="both", expand=True)
        view.mount()
        self.sidebar.set_active(name)
        self._current_view = view

        # 切回扫描视图时把累积的匹配记录刷给面板
        if name == "scan":
            self.match_panel.refresh(self.match_records)

    # =======================================================================
    # 占位回调（Task 16 实现真逻辑）
    # =======================================================================

    def on_start(self):
        self.append_log("（开始扫描）— Task 16 接入 pipeline 后生效", "INFO")

    def on_stop(self):
        self.append_log("（停止扫描）— Task 16 接入 pipeline 后生效", "INFO")

    def _on_toggle_sound(self, enabled):
        config.set("matching.enable_sound", enabled)
        config.save()
        self.append_log(f"声音提醒：{'开' if enabled else '关'}", "INFO")

    def _reset_config(self):
        if messagebox.askyesno("确认", "重置所有配置为默认值?"):
            config.load()
            for v in self._views.values():
                if hasattr(v, "_load_settings"):
                    v._load_settings()
                if hasattr(v, "reload_from_config"):
                    v.reload_from_config()
            self.statusbar.set_sound(config.get("matching.enable_sound"))
            self.append_log("配置已重置", "INFO")

    def on_settings_changed(self):
        """SettingsView 改了某些项后通知（如音效开关）。"""
        self.statusbar.set_sound(config.get("matching.enable_sound"))

    # =======================================================================
    # ScanView 委托：ROI 预设、词库浏览编辑
    # =======================================================================

    def apply_roi_preset(self, name, roi):
        self.roi = roi
        config.set("scan.roi", list(roi))
        config.save()
        self.append_log(f"已应用 ROI 预设 '{name}': {roi}", "INFO")

    def save_current_roi_preset(self):
        if self.roi is None:
            messagebox.showwarning("提示", "当前没有可保存的 ROI 区域")
            return
        name = simpledialog.askstring("保存预设", "请输入预设名称:", parent=self.root)
        if not name:
            return
        presets = config.get("scan.roi_presets") or {}
        presets[name] = list(self.roi)
        config.set("scan.roi_presets", presets)
        config.save()
        self._views["scan"].refresh_presets()
        self.append_log(f"ROI 预设 '{name}' 已保存: {list(self.roi)}", "INFO")

    def browse_banlist(self, current):
        init_dir = os.path.dirname(current) if current else "."
        return filedialog.askopenfilename(
            title="选择关键词文件", initialdir=init_dir,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

    def edit_banlist(self, path):
        if not path:
            messagebox.showwarning("提示", "请先选择关键词文件")
            return

        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)

        if not os.path.exists(path):
            if not messagebox.askyesno("确认", f"文件不存在:\n{path}\n是否创建?"):
                return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("")

        win = tk.Toplevel(self.root)
        win.title(f"编辑关键词 - {os.path.basename(path)}")
        win.geometry("600x400")
        win.attributes("-topmost", True)

        txt = scrolledtext.ScrolledText(win, font=("Consolas", 11), wrap=tk.WORD)
        txt.pack(fill="both", expand=True, padx=5, pady=5)

        with open(path, "r", encoding="utf-8") as f:
            txt.insert("1.0", f.read())

        def save_and_close():
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt.get("1.0", tk.END).rstrip("\n") + "\n")
            self.append_log(f"关键词文件已保存: {path}", "INFO")
            win.destroy()

        btn_fr = ttk.Frame(win)
        btn_fr.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_fr, text="保存并关闭",
                   command=save_and_close).pack(side="right", padx=5)
        ttk.Button(btn_fr, text="取消",
                   command=win.destroy).pack(side="right", padx=5)

    def _clear_match_records(self):
        self.match_records.clear()
        self.append_log("匹配记录已清除", "INFO")

    # =======================================================================
    # 日志（队列 + 主线程消费）
    # =======================================================================

    def append_log(self, message, level="INFO"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self.log_queue.put_nowait((f"{ts} - {message}\n", level))
        except queue.Full:
            pass

    def _setup_gui_logger(self):
        class _QueueHandler(logging.Handler):
            def __init__(self, q):
                super().__init__()
                self._q = q

            def emit(self, record):
                try:
                    msg = self.format(record) + "\n"
                    self._q.put_nowait((msg, record.levelname))
                except Exception:
                    pass

        handler = _QueueHandler(self.log_queue)
        handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s - %(message)s")
        fmt.default_msec_format = "%s.%03d"
        handler.setFormatter(fmt)

        from src.utils.logger import logger as app_logger
        app_logger.addHandler(handler)

    def _drain_log_queue(self):
        count = 0
        while count < 15:
            try:
                msg, lvl = self.log_queue.get_nowait()
                self.log_panel.append(msg.rstrip("\n"), lvl)
                count += 1
            except queue.Empty:
                break
        self.root.after(100, self._drain_log_queue)

    # =======================================================================
    # 内存监控
    # =======================================================================

    def _schedule_memory_update(self):
        mb = get_memory_mb()
        self.statusbar.set_memory(mb)
        self.root.after(5000, self._schedule_memory_update)

    # =======================================================================
    # 关闭（Task 16 加 watchdog） ====
    # =======================================================================

    def _on_close(self):
        self.root.destroy()


# ---------------------------------------------------------------------------
# 演示（独立跑 main_window 看视图切换）
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    win = MainWindow(root)
    root.mainloop()
```

- [ ] **Step 2：运行演示**

```powershell
python -m src.gui.main_window
```

视觉检查：
- 窗口 1100x720，深色主题
- 左侧侧栏 4 个按钮（扫描高亮）
- 中间是扫描视图：左边配置面板、右边上日志下匹配记录（"暂无匹配记录"）
- 底部状态栏：●(红) 已停止 / 内存数字 / 版本 / 引擎 / [开始扫描][停止][声音提醒][重置配置]
- 点"设置"侧栏 → 切到设置视图（高级配置项）
- 点"热键" → 看到 Ctrl+Alt+1/2 列表
- 点"关于" → 看到项目信息
- 点回"扫描" → 配置面板和日志/匹配记录都还在
- 点"开始扫描" → 日志区出现 "（开始扫描）— Task 16 接入 pipeline 后生效"
- 点"停止" → 类似一行日志
- 改 ROI 启用复选 / 滑块 / 改设置 → 不报错
- 关窗 → 程序退出

- [ ] **Step 3：app.py 仍能跑（关键）**

```powershell
python app.py
```

视觉检查：旧版浅色 UI 正常出现、所有控件能用（这一步是确认 `src/gui/` 引入没破坏 app.py 的 import）。关掉旧版。

- [ ] **Step 4：提交**

```powershell
git add src/gui/main_window.py
git commit -m "feat: 添加 MainWindow 骨架（视图切换 + 占位回调）"
```

---

## Task 16：MainWindow 接入 pipeline / tray / hotkey / 看门狗清理

**Files:**
- Modify: `src/gui/main_window.py`

**职责：** 替换 `on_start` / `on_stop` 占位实现为真正的扫描调度；接入 `ScanPipeline` / `Overlay` / `RoiBorder` / 系统托盘 / 全局热键；`_on_close` 加看门狗。

> **重要：** 这一步要 **修改** `main_window.py` 而不是新建文件。每个 Step 给出要改/要加的代码段，最后一个 Step 给完整 diff 验证（diff 中应只看到 `main_window.py` 一处变化）。

- [ ] **Step 1：替换 import 区，加入 pipeline 相关模块**

打开 `src/gui/main_window.py`，在文件头部 import 区追加：

```python
from src.pipeline.pipeline import ScanPipeline
from src.utils.hotkey import HotkeyManager
from shared.overlay import Overlay
from src.gui.widgets.roi_overlay import select_roi_interactive
from src.gui.widgets.roi_border import RoiBorder
from src.gui.widgets.tray import setup_tray
```

- [ ] **Step 2：在 `__init__` 里实例化 pipeline / overlay / roi_border / tray / hotkey_mgr**

定位到 `__init__` 中 `# ---- 扫描相关（Task 16 接入实际逻辑） ----` 这一节，把整段（从 `self.is_running = False` 到 `self.hotkey_mgr = None`）替换为：

```python
        # ---- 扫描相关 ----
        self.is_running = False
        self.scan_thread = None
        self.stop_event = threading.Event()
        self.roi = None
        self.pipeline = ScanPipeline()
        self.overlay = Overlay(parent_root=self.root, config=config, logger=logger)
        self.roi_border = RoiBorder(self.root,
                                     padding=config.get("scan.roi_padding"))
        self.hotkey_mgr = HotkeyManager()
        self.tray = None
```

- [ ] **Step 3：在 `__init__` 末尾加 tray 启动 + 热键注册**

定位到 `__init__` 末尾（`self._drain_log_queue()` 之后），追加：

```python
        # ---- 托盘 ----
        self.tray = setup_tray(
            self.root,
            on_show=self._tray_show,
            on_quit=self._tray_quit,
            tooltip="屏幕扫描OCR识别",
        )
        if self.tray:
            self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
            self.append_log("托盘图标已启用：关闭窗口将缩到托盘，右键托盘可退出", "INFO")
        else:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- 热键 ----
        self.root.after_idle(self._register_hotkeys)
```

- [ ] **Step 4：替换 `on_start` 占位**

定位到 `def on_start(self):`，整个函数体（连同上方 `def on_start` 声明）替换为：

```python
    def on_start(self):
        if self.is_running:
            return

        # 把扫描视图当前的设置存到 config，再触发 pipeline.init
        scan_view = self._views["scan"]
        scan_view.save_settings()
        self.overlay.clear_session()
        self.match_records.clear()
        self.match_panel.refresh(self.match_records)

        self.statusbar.set_busy(True)
        self.append_log("正在初始化 OCR 引擎...", "INFO")

        threading.Thread(target=self._init_and_start, daemon=True).start()

    def _init_and_start(self):
        try:
            self.pipeline.init()
            self.root.after(0, self._after_init_ok)
        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda: self._after_init_fail(msg))

    def _after_init_ok(self):
        self.append_log("OCR 初始化完成", "INFO")

        # ROI
        scan_view = self._views["scan"]
        if scan_view.var_enable_roi.get():
            saved = config.get("scan.roi")
            if scan_view.var_remember_roi.get() and saved:
                self.roi = tuple(saved)
                self.append_log(f"使用已保存 ROI: {self.roi}", "INFO")
                self._start_scanning()
                return
            self.root.iconify()
            self.root.after(300, self._do_roi_select)
            return

        self.roi = None
        self._start_scanning()

    def _do_roi_select(self):
        self.roi = select_roi_interactive(parent=self.root)
        self.root.deiconify()
        if self.roi:
            self.append_log(f"ROI 已选择: {self.roi}", "INFO")
            config.set("scan.roi", list(self.roi))
            config.save()
        else:
            self.append_log("ROI 选择取消，使用全屏", "WARNING")
        self._start_scanning()

    def _start_scanning(self):
        self.pipeline.set_roi(self.roi)
        self.overlay.setup()

        self.is_running = True
        self.stop_event.clear()
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()

        self.statusbar.set_running(True)
        self.append_log("扫描已启动", "INFO")
        self.roi_border.show(self.roi)

    def _after_init_fail(self, msg):
        self.append_log(f"初始化失败: {msg}", "ERROR")
        messagebox.showerror("错误", f"OCR 初始化失败:\n{msg}")
        self.statusbar.set_running(False)
```

- [ ] **Step 5：替换 `on_stop` 占位 + 加 `_scan_loop` / `_on_scan_result`**

定位到 `def on_stop(self):`，整个函数体替换为：

```python
    def on_stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.stop_event.set()
        self.roi_border.hide()
        self.overlay.hide()
        self.statusbar.set_running(False)
        self.append_log("扫描已停止", "INFO")

    # =======================================================================
    # 扫描循环
    # =======================================================================

    def _scan_loop(self):
        try:
            scan_view = self._views["scan"]
            while not self.stop_event.is_set():
                interval = scan_view.var_interval.get()
                start = time.time()

                result = self.pipeline.scan_once()
                self.root.after(0, self._on_scan_result, result)

                elapsed = time.time() - start
                wait = max(0, interval - elapsed)
                waited = 0.0
                while waited < wait and not self.stop_event.is_set():
                    time.sleep(0.3)
                    waited += 0.3
        except Exception as e:
            self.append_log(f"扫描异常: {e}", "ERROR")
        finally:
            self.is_running = False
            self.root.after(0, self._on_scan_thread_exit)

    def _on_scan_result(self, result):
        # 1. 日志一行总结
        if result.skipped:
            status_txt = "跳过(无变化)"
        else:
            status_txt = f"{len(result.ocr_results)}行"
        self.append_log(
            f"OCR: {status_txt}, 匹配: {len(result.matches)}, "
            f"耗时: {result.duration:.3f}s", "INFO"
        )

        # 2. 命中的关键词 + 写入 match_records deque
        for m in result.matches:
            self.append_log(f"  >>> {m['keyword']} | {m['hint']}", "WARNING")
            self.match_records.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "keyword": m["keyword"],
                "ocr_text": m.get("ocr_text", ""),
            })

        # 3. 当前在扫描视图就刷新匹配记录面板
        if self._current_view is self._views["scan"] and result.matches:
            self.match_panel.refresh(self.match_records)

        # 4. Overlay 浮窗（每次扫描都刷，包括 skipped 与无匹配）
        self.overlay.update(result.ocr_results, result.matches)

    def _on_scan_thread_exit(self):
        self.roi_border.hide()
        self.overlay.hide()
        self.statusbar.set_running(False)
```

- [ ] **Step 6：加托盘相关方法**

在 `_on_scan_thread_exit` 之后追加：

```python
    # =======================================================================
    # 托盘 / 关闭
    # =======================================================================

    def _minimize_to_tray(self):
        self.root.withdraw()

    def _tray_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _tray_quit(self):
        self._on_close()

    # =======================================================================
    # 热键
    # =======================================================================

    def _register_hotkeys(self):
        try:
            self.hotkey_mgr.register("ctrl+alt+1",
                                       lambda: self.root.after(0, self.on_start),
                                       "开始扫描")
            self.hotkey_mgr.register("ctrl+alt+2",
                                       lambda: self.root.after(0, self.on_stop),
                                       "停止扫描")
            self.append_log("热键: Ctrl+Alt+1 开始, Ctrl+Alt+2 停止", "INFO")
        except Exception as e:
            self.append_log(f"热键注册失败: {e}", "WARNING")
```

- [ ] **Step 7：替换 `_on_close` 为 watchdog 版本**

定位到 `def _on_close(self):`，整个函数体替换为：

```python
    def _on_close(self):
        """看门狗式清理：3 秒后强杀，保证不卡死。"""
        watchdog = threading.Timer(3.0, lambda: os._exit(0))
        watchdog.daemon = True
        watchdog.start()

        try:
            self.root.withdraw()
        except Exception:
            pass

        for cleanup in (
            lambda: self.roi_border.hide(),
            lambda: self.overlay.destroy(),
            lambda: self.tray and self.tray.stop(),
            lambda: self.hotkey_mgr.unregister_all(),
            lambda: self.pipeline.release(),
        ):
            try:
                cleanup()
            except Exception:
                pass

        os._exit(0)
```

- [ ] **Step 8：运行 main_window 演示，做完整冒烟测试**

```powershell
python -m src.gui.main_window
```

视觉/功能检查（`Spec §6` 冒烟测试清单）：
1. 启动 → 默认在扫描视图，所有控件可见
2. 改"扫描间隔"滑块到 3.0 → 数字显示 3.0
3. 点"开始扫描" → ●变黄"初始化中..."→ 几秒后变绿"运行中"，日志开始滚动
4. 命中关键词时（取决于词库 + 屏幕内容） → 匹配记录新增一行（最新在最上）
5. 切到设置视图改"MSE 阈值"为 10 → 切回扫描视图，日志显示"OCR..." 仍在跑
6. 切到关于视图等几秒 → 切回扫描视图，匹配记录补齐期间的命中
7. 点"停止" → ●变红"已停止"
8. 按 Ctrl+Alt+2 在任意视图都能停（如已停则无变化）
9. 关窗口（有 tray） → 缩托盘；右键托盘"退出" → 干净关闭，PowerShell 进程列表里不再有 python
10. 启用 ROI（取消 "记住"） → 启动会先跑 ROI 选择 → 拖一个矩形或 ESC

PowerShell 验证无 zombie 进程：
```powershell
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName
```
关窗后这条应该返回空（或不含刚才的 PID）。

- [ ] **Step 9：提交**

```powershell
git add src/gui/main_window.py
git commit -m "feat: MainWindow 接入 pipeline / tray / hotkey / 看门狗清理"
```

---

# Phase 6：切换入口（Spec §7 Step 6）

## Task 17：替换 app.py 为薄入口 + 删除旧 GUI 代码

**Files:**
- Modify: `app.py`

**职责：** 把 `app.py` 1264 行替换成 < 50 行的薄入口；旧的 `MainGUI` 类、`_setup_tray` / `select_roi_interactive` / `_get_memory_mb` 等内联辅助一并删除（已被 `src/gui/` 下模块替代）。

- [ ] **Step 1：完整替换 `app.py` 内容**

```python
"""
ScreenScanOCRRecognize — GUI 主程序入口。

实际逻辑在 src/gui/main_window.py 的 MainWindow 类。本入口只负责
建 Tk root + MainWindow 实例 + mainloop。
"""

import os
import sys
import tkinter as tk

# 项目根入 sys.path（src/config/config.py 也会做这一步，但放这里更显式）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.main_window import MainWindow


def main():
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2：行数检查**

```powershell
(Get-Content app.py | Measure-Object -Line).Lines
```

期望：< 50。

- [ ] **Step 3：完整冒烟测试（这是切到新版 GUI 的关键时刻）**

```powershell
python app.py
```

走一遍 Task 16 Step 8 的全部 10 项检查清单。**全部通过**才能进入下一步。

如发现问题：
- 确认 `src/gui/main_window.py` 演示模式（`python -m src.gui.main_window`）也有同样问题——是的话回到 Task 16 修；不是的话差异通常是 import path 或 tk.Tk 初始化时序，仔细对比。

- [ ] **Step 4：cli.py 仍能跑（确认未受影响）**

```powershell
python cli.py
```

启动后看到 "正在初始化 OCR 模型..." → "初始化完成，开始扫描..." 然后开始打印扫描结果。Ctrl+C 中断。期望：CLI 正常工作。

- [ ] **Step 5：gui.bat 仍能跑（关键 Windows 入口）**

PowerShell：
```powershell
./gui.bat
```

期望：新版 GUI 启动（与 `python app.py` 表现相同），无控制台残留。手动关掉 GUI 窗口。

- [ ] **Step 6：提交**

```powershell
git add app.py
git commit -m "feat: app.py 切到 src/gui/MainWindow，删除旧的内联 GUI 代码"
```

---

# Phase 7：清理（Spec §7 Step 7）

## Task 18：删除 mockups/ 与最终验证

**Files:**
- Delete: `mockups/_common.py`, `mockups/mockup_a.py`, `mockups/mockup_b.py`, `mockups/mockup_c.py`, `mockups/mockup_a.png`, `mockups/mockup_b.png`, `mockups/mockup_c.png`, 目录 `mockups/`

> **理由：** 旧的 mockup 是浅色主题，与新 UI 视觉不再一致；保留会误导未来读代码的人。设计参考已经定格在 `docs/superpowers/specs/2026-05-08-ui-redesign-design.md` 与 mockup 截图（commit 历史中可追）。

- [ ] **Step 1：确认 mockups/ 没被代码 import**

```powershell
Get-ChildItem -Recurse -Include *.py -Exclude mockups | Select-String -Pattern "from mockups|import mockups"
```

期望：无输出。如有任何文件 import 它，先去掉那个 import 再继续。

- [ ] **Step 2：删除 mockups/ 整个目录**

```powershell
Remove-Item -Recurse -Force mockups
```

- [ ] **Step 3：最终全量冒烟（与 Task 17 Step 3 相同的 10 项）**

```powershell
python app.py
```

走一遍 Task 16 Step 8 的全部 10 项检查清单。所有功能正常。

- [ ] **Step 4：检查 grep 不到旧的痕迹**

```powershell
Get-ChildItem -Recurse -Include *.py | Select-String -Pattern "scan_count|last_scan_time|_create_topbar|_lbl_count|_lbl_last"
```

期望：无输出（与 Spec §9 删除项一致）。如果 `old_version/` 里命中那是预期保留——只关注 `app.py` / `src/gui/` / `cli.py`。

- [ ] **Step 5：检查不变项的文件没动**

```powershell
git log --pretty=format:"" --name-only main..HEAD | Where-Object { $_ -ne "" } | Sort-Object -Unique
```

期望输出**仅**包含：
- `app.py`
- `docs/superpowers/specs/2026-05-08-ui-redesign-design.md`
- `docs/superpowers/plans/2026-05-08-ui-redesign.md`
- `src/gui/...`（多个新文件）
- 不应包含 `cli.py`、`shared/*`、`src/pipeline/*`、`src/utils/*`、`src/config/*`、`defaults.py`、`config/config.yaml`、`gui.bat`、`old_version/*`

如有意外文件被改动，回去看是哪个 Task 引入的、是否必要。

- [ ] **Step 6：提交**

```powershell
git add -A mockups
git commit -m "chore: 删除 mockups/ 目录（旧浅色版设计参考已被 spec 取代）"
```

---

# 完成检查

- [ ] 所有 18 个 Task 都打勾
- [ ] 最终 `python app.py` 通过 Task 16 Step 8 全部 10 项冒烟测试
- [ ] `python cli.py` 仍正常工作
- [ ] `./gui.bat` 仍正常工作
- [ ] `git log --oneline | head -25` 看到 18 个独立 commit（每 Task 一个），每个 commit message 中文 + 类型前缀

---

# 附：常见问题排查

**症状：`python -m src.gui.xxx` 报 `ModuleNotFoundError: No module named 'defaults'`**
→ 模块顶部的 `_ROOT` 计算错了层数。每个文件层级不同：
- `src/gui/theme.py` → 上溯 3 层
- `src/gui/sidebar.py` / `statusbar.py` → 上溯 3 层
- `src/gui/widgets/*.py` / `views/*.py` → 上溯 4 层

**症状：开始扫描后日志卡住不动**
→ 看 PowerShell 终端有没有 traceback。常见是 PaddleOCR 初始化失败（需要 paddlepaddle / paddleocr 安装；GPU 模式还需 CUDA）。改 `gpu.enabled = false` 试试。

**症状：关窗后进程不退出**
→ 看 watchdog 是否触发：3 秒后必死。如果不死说明 `os._exit(0)` 没执行，可能是 import 时抛了异常导致 `_on_close` 没绑上。`python app.py` 看 traceback。

**症状：热键无效**
→ `keyboard` 库需要管理员权限。PowerShell 启动方式如果不是管理员，热键注册会 warning（但不报错）；改用按钮启停。

**症状：Combobox 下拉项是白底黑字**
→ `theme.apply()` 里的 `root.option_add` 必须在创建 Combobox 之前调。MainWindow 顺序是 `theme.apply` 在 `__init__` 早期，没问题；如果某个 demo 块调反了顺序就会出现。

---
