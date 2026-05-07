# GUI 重做 · 方案 C 落地 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `app.py` 的 GUI 从「单列 4 个 LabelFrame」重做成「顶部状态栏 + 左侧 Notebook tab + 右侧日志 + 底部按钮栏」布局，窗口保持 860×680，所有现有控件功能与交互不变。

**Architecture:** 单文件改动（`app.py`），通过新增容器方法替换 `_create_widgets` 的 6 个旧子方法。控件背后的 Tk 变量、回调、扫描逻辑、托盘/热键/日志通通保留。新增彩色状态指示灯 `●`。

**Tech Stack:** tkinter / ttk（clam 主题）、PIL ImageGrab、pystray、keyboard。无新增依赖。

**Spec:** `docs/superpowers/specs/2026-05-07-gui-mockup-c-redesign-design.md`

**关于 commit：** 按项目约定，本计划**不含 commit 步骤**。所有任务完成且手测通过后由用户决定是否提交。

---

## 文件结构

只改 `app.py`，其它文件零改动。最终 `app.py` 内 `MainGUI` 类的方法布局（增量与删除）：

| 方法 | 状态 |
|---|---|
| `_setup_styles` | **新增** |
| `_init_vars` | **新增**（把分散在旧 `_create_*` 里的 14 个 `tk.*Var` 集中创建） |
| `_create_topbar` | **新增**（替代 `_create_status_bar`） |
| `_create_bottombar` | **新增**（替代 `_create_buttons`） |
| `_create_sidebar` / `_create_tab_common` / `_create_tab_advanced` | **新增**（替代 `_create_scan_config` + `_create_ocr_config` + `_create_match_config`） |
| `_create_main_area` | **新增**（替代 `_create_log_area`） |
| `_create_widgets` | **重写**（调用上述新方法） |
| `_update_status` | **小改**（增加灯色切换） |
| `_update_stats` / `_schedule_memory_update` | **小改**（label 文本格式调整） |
| `_create_status_bar` / `_create_scan_config` / `_create_ocr_config` / `_create_match_config` / `_create_log_area` / `_create_buttons` | **删除** |
| 其它所有方法（回调、扫描线程、托盘、热键、ROI、日志队列、`_load_settings`/`_save_settings` 等） | **不动** |

新增模块级常量（color/font）放在 imports 之后、`_make_tray_icon_image` 之前。

---

## Task 1: 添加配色常量与样式方法

**Files:**
- Modify: `app.py`（新增模块级常量 + 类方法 `_setup_styles`）

- [ ] **Step 1: 在 `app.py` 的 imports 之后、`_make_tray_icon_image` 之前插入配色常量块**

定位：第 23-24 行之间（`from shared.overlay import Overlay` 之后、`# ---- 托盘图标` 之前）。

```python
# ---------------------------------------------------------------------------
# UI 配色与字体（clam 主题，与 mockups/mockup_c.py 一致）
# ---------------------------------------------------------------------------

UI_FONT = "Microsoft YaHei"
COLOR_BG = "#fafafa"
COLOR_SIDEBAR = "#eef0f3"
COLOR_CARD = "#ffffff"
COLOR_PRIMARY = "#0066cc"
COLOR_DANGER = "#d83b01"
COLOR_SUCCESS = "#107c10"
COLOR_WARNING = "#d8a200"
COLOR_TEXT = "#222222"
COLOR_SUBTEXT = "#777777"
COLOR_BORDER = "#d8dade"
```

- [ ] **Step 2: 在 `MainGUI` 类内 `_create_widgets` 方法之前插入 `_setup_styles` 方法**

```python
    def _setup_styles(self):
        """配置 ttk 主题与各样式。clam 主题对 Combobox/Scale/Notebook 配色支持最完整。"""
        self.root.configure(bg=COLOR_BG)
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, font=(UI_FONT, 9))
        style.configure("TFrame", background=COLOR_BG)
        style.configure("Sidebar.TFrame", background=COLOR_SIDEBAR)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("Sidebar.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT)
        style.configure("SubSidebar.TLabel", background=COLOR_SIDEBAR,
                        foreground=COLOR_SUBTEXT, font=(UI_FONT, 8))
        style.configure("Section.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT,
                        font=(UI_FONT, 10, "bold"))

        style.configure("TCheckbutton", background=COLOR_BG)
        style.configure("Sidebar.TCheckbutton", background=COLOR_SIDEBAR)
        style.configure("TCombobox", fieldbackground=COLOR_CARD)
        style.configure("TEntry", fieldbackground=COLOR_CARD)
        style.configure("TScale", background=COLOR_BG, troughcolor=COLOR_BORDER)

        style.configure("TButton", background=COLOR_CARD, foreground=COLOR_TEXT,
                        bordercolor=COLOR_BORDER, borderwidth=1, padding=(10, 5),
                        relief="flat")
        style.map("TButton",
                  background=[("active", "#e8e8eb"), ("pressed", "#d8d8db")])
        style.configure("Primary.TButton", background=COLOR_PRIMARY, foreground="white",
                        bordercolor=COLOR_PRIMARY, padding=(20, 8),
                        font=(UI_FONT, 10, "bold"))
        style.map("Primary.TButton",
                  background=[("active", "#0050a0"), ("pressed", "#003e80")])
        style.configure("Danger.TButton", background=COLOR_CARD, foreground=COLOR_DANGER,
                        bordercolor=COLOR_DANGER, padding=(20, 8),
                        font=(UI_FONT, 10, "bold"))
        style.map("Danger.TButton",
                  background=[("active", "#fef0ec"), ("pressed", "#fbe2db")])

        style.configure("TNotebook", background=COLOR_SIDEBAR, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_SIDEBAR, foreground=COLOR_SUBTEXT,
                        padding=(12, 6), font=(UI_FONT, 9))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD)],
                  foreground=[("selected", COLOR_PRIMARY)])
```

- [ ] **Step 3: 验证 import 正常**

Run: `python -c "import app; print('ok')"`
Expected: `ok`，无 SyntaxError、无 NameError。

---

## Task 2: 添加变量初始化方法

旧版本在 6 个 `_create_*` 子方法里散布创建 `tk.*Var`，新版本集中创建。

**Files:**
- Modify: `app.py`（新增 `_init_vars` 方法）

- [ ] **Step 1: 在 `MainGUI._setup_styles` 之后插入 `_init_vars` 方法**

```python
    def _init_vars(self):
        """集中创建所有 Tk 变量。值由后续 _load_settings 覆盖，这里写默认值。"""
        # 扫描配置
        self._var_enable_roi = tk.BooleanVar()
        self._var_remember_roi = tk.BooleanVar(value=True)
        self._var_roi_preset = tk.StringVar()
        self._var_gpu = tk.BooleanVar(value=True)
        self._var_interval = tk.DoubleVar(value=2.0)
        self._var_diff_threshold = tk.DoubleVar(value=5.0)
        # OCR
        self._var_lang = tk.StringVar(value='ch')
        self._var_confidence = tk.DoubleVar(value=0.3)
        self._var_invert = tk.BooleanVar()
        # 关键词 / 浮窗
        self._var_banlist = tk.StringVar(value=DEFAULT_BANLIST_FILE)
        self._var_duration = tk.DoubleVar(value=3.0)
        self._var_fontsize = tk.IntVar(value=18)
        self._var_position = tk.StringVar(value='居中')
        self._var_sound = tk.BooleanVar(value=True)
```

- [ ] **Step 2: 验证 import 正常**

Run: `python -c "import app; print('ok')"`
Expected: `ok`。

---

## Task 3: 添加顶部状态栏方法

**Files:**
- Modify: `app.py`（新增 `_create_topbar` 方法）

- [ ] **Step 1: 在 `_init_vars` 之后插入 `_create_topbar` 方法**

```python
    def _create_topbar(self, parent):
        """顶部状态栏：左侧 ● + 状态文字，右侧 3 个统计 cell。"""
        bar = tk.Frame(parent, bg=COLOR_CARD, height=56,
                       highlightbackground=COLOR_BORDER, highlightthickness=1)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        inner = tk.Frame(bar, bg=COLOR_CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        # 左侧：● + 状态
        left = tk.Frame(inner, bg=COLOR_CARD)
        left.pack(side=tk.LEFT)
        self._lbl_dot = tk.Label(left, text="●", fg=COLOR_DANGER, bg=COLOR_CARD,
                                 font=(UI_FONT, 14))
        self._lbl_dot.pack(side=tk.LEFT)
        cell = tk.Frame(left, bg=COLOR_CARD)
        cell.pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(cell, text="状态", bg=COLOR_CARD, fg=COLOR_SUBTEXT,
                 font=(UI_FONT, 8)).pack(anchor=tk.W)
        self._lbl_status = tk.Label(cell, text="已停止", bg=COLOR_CARD, fg=COLOR_TEXT,
                                     font=(UI_FONT, 11, "bold"))
        self._lbl_status.pack(anchor=tk.W)

        # 右侧：3 个统计 cell
        right = tk.Frame(inner, bg=COLOR_CARD)
        right.pack(side=tk.RIGHT)

        def _stat_cell(caption, initial):
            c = tk.Frame(right, bg=COLOR_CARD)
            c.pack(side=tk.LEFT, padx=14)
            tk.Label(c, text=caption, bg=COLOR_CARD, fg=COLOR_SUBTEXT,
                     font=(UI_FONT, 8)).pack(anchor=tk.E)
            v = tk.Label(c, text=initial, bg=COLOR_CARD, fg=COLOR_TEXT,
                         font=(UI_FONT, 11, "bold"))
            v.pack(anchor=tk.E)
            return v

        self._lbl_count = _stat_cell("扫描次数", "0")
        self._lbl_last = _stat_cell("最近扫描", "--")
        self._lbl_mem = _stat_cell("内存", "-- MB")
```

- [ ] **Step 2: 验证 import 正常**

Run: `python -c "import app; print('ok')"`
Expected: `ok`。

---

## Task 4: 添加底部按钮栏方法

**Files:**
- Modify: `app.py`（新增 `_create_bottombar` 方法）

- [ ] **Step 1: 在 `_create_topbar` 之后插入 `_create_bottombar` 方法**

```python
    def _create_bottombar(self, parent):
        """底部按钮栏：左侧 开始/停止；右侧 清除/重置。"""
        bar = tk.Frame(parent, bg=COLOR_CARD, height=56,
                       highlightbackground=COLOR_BORDER, highlightthickness=1)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)
        inner = tk.Frame(bar, bg=COLOR_CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        self._btn_start = ttk.Button(inner, text="开始扫描", style="Primary.TButton",
                                      command=self.on_start)
        self._btn_start.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_stop = ttk.Button(inner, text="停止扫描", style="Danger.TButton",
                                     command=self.on_stop, state=tk.DISABLED)
        self._btn_stop.pack(side=tk.LEFT)

        ttk.Button(inner, text="重置配置",
                   command=self._reset_config).pack(side=tk.RIGHT)
        ttk.Button(inner, text="清除匹配记录",
                   command=self._clear_session).pack(side=tk.RIGHT, padx=(0, 6))
```

- [ ] **Step 2: 验证 import 正常**

Run: `python -c "import app; print('ok')"`
Expected: `ok`。

---

## Task 5: 添加侧边栏与两个 tab 方法

**Files:**
- Modify: `app.py`（新增 `_create_sidebar`、`_create_tab_common`、`_create_tab_advanced` 三个方法）

- [ ] **Step 1: 在 `_create_bottombar` 之后插入 `_create_sidebar`**

```python
    def _create_sidebar(self, parent):
        """左侧 300px 配置面板，含两个 Notebook 标签。"""
        sb = tk.Frame(parent, bg=COLOR_SIDEBAR, width=300,
                       highlightbackground=COLOR_BORDER, highlightthickness=1)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        nb = ttk.Notebook(sb)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        common = ttk.Frame(nb, style="Sidebar.TFrame", padding=(10, 8))
        nb.add(common, text="  常用配置  ")
        self._create_tab_common(common)

        adv = ttk.Frame(nb, style="Sidebar.TFrame", padding=(10, 8))
        nb.add(adv, text="  高级  ")
        self._create_tab_advanced(adv)
```

- [ ] **Step 2: 在 `_create_sidebar` 之后插入 `_create_tab_common`**

```python
    def _create_tab_common(self, parent):
        """常用配置 tab：扫描区域 / 扫描节奏 / OCR / 关键词。"""

        def header(text):
            ttk.Label(parent, text=text, style="Section.TLabel").pack(
                anchor=tk.W, pady=(8, 2))

        def sub(text):
            ttk.Label(parent, text=text, style="SubSidebar.TLabel").pack(
                anchor=tk.W, pady=(4, 2))

        def row():
            r = tk.Frame(parent, bg=COLOR_SIDEBAR)
            r.pack(fill=tk.X, pady=2)
            return r

        # ----- 扫描区域 -----
        header("扫描区域")
        r = row()
        tk.Checkbutton(r, text="启用 ROI", bg=COLOR_SIDEBAR,
                       variable=self._var_enable_roi).pack(side=tk.LEFT)
        tk.Checkbutton(r, text="记住", bg=COLOR_SIDEBAR,
                       variable=self._var_remember_roi).pack(side=tk.LEFT, padx=(10, 0))

        sub("ROI 预设")
        r = row()
        self._combo_preset = ttk.Combobox(r, textvariable=self._var_roi_preset,
                                           width=16, state='readonly')
        self._combo_preset.pack(side=tk.LEFT)
        self._combo_preset.bind('<<ComboboxSelected>>', self._on_preset_selected)
        ttk.Button(r, text="保存当前",
                   command=self._save_roi_preset).pack(side=tk.LEFT, padx=(6, 0))

        # ----- 扫描节奏 -----
        header("扫描节奏")
        sub("扫描间隔（秒）")
        r = row()
        ttk.Scale(r, from_=0.5, to=15, variable=self._var_interval, length=180,
                  command=self._on_interval_scale).pack(side=tk.LEFT)
        ttk.Entry(r, width=5,
                  textvariable=self._var_interval).pack(side=tk.LEFT, padx=(6, 0))

        # ----- OCR -----
        header("OCR")
        r = row()
        tk.Label(r, text="语言", bg=COLOR_SIDEBAR, fg=COLOR_SUBTEXT,
                 font=(UI_FONT, 8)).pack(side=tk.LEFT)
        ttk.Combobox(r, textvariable=self._var_lang, width=8, state='readonly',
                     values=('ch', 'en', 'japan', 'korean')).pack(side=tk.LEFT, padx=(6, 14))
        tk.Checkbutton(r, text="GPU 加速", bg=COLOR_SIDEBAR,
                       variable=self._var_gpu).pack(side=tk.LEFT)

        sub("最小置信度")
        r = row()
        ttk.Scale(r, from_=0, to=1, variable=self._var_confidence, length=180,
                  command=self._on_conf_scale).pack(side=tk.LEFT)
        ttk.Entry(r, width=5,
                  textvariable=self._var_confidence).pack(side=tk.LEFT, padx=(6, 0))

        # ----- 关键词 -----
        header("关键词")
        sub("词表文件")
        r = row()
        ttk.Entry(r, textvariable=self._var_banlist).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(r, text="浏览…",
                   command=self._browse_banlist).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(r, text="编辑",
                   command=self._edit_banlist).pack(side=tk.LEFT, padx=(4, 0))

        sub("匹配后显示时长（秒）")
        r = row()
        ttk.Scale(r, from_=1, to=10, variable=self._var_duration, length=180,
                  command=self._on_dur_scale).pack(side=tk.LEFT)
        ttk.Entry(r, width=5,
                  textvariable=self._var_duration).pack(side=tk.LEFT, padx=(6, 0))
```

- [ ] **Step 3: 在 `_create_tab_common` 之后插入 `_create_tab_advanced`**

```python
    def _create_tab_advanced(self, parent):
        """高级 tab：帧差检测 / 浮窗外观 / OCR 进阶。"""

        def header(text):
            ttk.Label(parent, text=text, style="Section.TLabel").pack(
                anchor=tk.W, pady=(8, 2))

        def sub(text):
            ttk.Label(parent, text=text, style="SubSidebar.TLabel").pack(
                anchor=tk.W, pady=(4, 2))

        def row():
            r = tk.Frame(parent, bg=COLOR_SIDEBAR)
            r.pack(fill=tk.X, pady=2)
            return r

        # ----- 帧差检测 -----
        header("帧差检测")
        sub("MSE 阈值（0=每次都 OCR）")
        r = row()
        ttk.Scale(r, from_=0, to=50, variable=self._var_diff_threshold, length=180,
                  command=self._on_diff_scale).pack(side=tk.LEFT)
        ttk.Entry(r, width=5,
                  textvariable=self._var_diff_threshold).pack(side=tk.LEFT, padx=(6, 0))

        # ----- 浮窗外观 -----
        header("浮窗外观")
        sub("字号（px）")
        r = row()
        ttk.Scale(r, from_=10, to=36, variable=self._var_fontsize, length=180,
                  command=self._on_fs_scale).pack(side=tk.LEFT)
        ttk.Entry(r, width=5,
                  textvariable=self._var_fontsize).pack(side=tk.LEFT, padx=(6, 0))

        sub("位置")
        ttk.Combobox(parent, textvariable=self._var_position, width=10,
                     state='readonly',
                     values=('居中', '顶部', '底部')).pack(anchor=tk.W, pady=2)

        tk.Checkbutton(parent, text="音效提醒", bg=COLOR_SIDEBAR,
                       variable=self._var_sound).pack(anchor=tk.W, pady=(8, 0))

        # ----- OCR 进阶 -----
        header("OCR 进阶")
        tk.Checkbutton(parent, text="图像反色（黑底白字时启用）", bg=COLOR_SIDEBAR,
                       variable=self._var_invert).pack(anchor=tk.W, pady=2)
```

- [ ] **Step 4: 验证 import 正常**

Run: `python -c "import app; print('ok')"`
Expected: `ok`。

---

## Task 6: 添加主区方法（日志）

**Files:**
- Modify: `app.py`（新增 `_create_main_area` 方法）

- [ ] **Step 1: 在 `_create_tab_advanced` 之后插入 `_create_main_area`**

```python
    def _create_main_area(self, parent):
        """右侧主区：日志 header + 日志 ScrolledText（占满剩余空间）。"""
        main = tk.Frame(parent, bg=COLOR_BG)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 日志 header
        head = tk.Frame(main, bg=COLOR_BG)
        head.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(head, text="运行日志", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=(UI_FONT, 11, "bold")).pack(side=tk.LEFT)
        ttk.Button(head, text="清空", command=self._clear_log).pack(side=tk.RIGHT)

        # 日志框（外层加 1px 边框）
        wrap = tk.Frame(main, bg=COLOR_BORDER)
        wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self._log_text = scrolledtext.ScrolledText(
            wrap, wrap=tk.WORD, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
            borderwidth=0, highlightthickness=0,
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self._log_text.tag_config("INFO", foreground="#4ec9b0")
        self._log_text.tag_config("WARNING", foreground="#dcdcaa")
        self._log_text.tag_config("ERROR", foreground="#f48771")
        self._log_text.tag_config("DEBUG", foreground="#569cd6")
```

- [ ] **Step 2: 验证 import 正常**

Run: `python -c "import app; print('ok')"`
Expected: `ok`。

---

## Task 7: 重写 `_create_widgets`，删除 6 个旧 `_create_*` 方法

这是切换的关键一步。完成后界面就变成新版。

**Files:**
- Modify: `app.py`（重写 `_create_widgets`，删除 6 个旧方法）

- [ ] **Step 1: 重写 `_create_widgets` 方法**

定位：原 `_create_widgets`（约第 318-327 行）。

旧实现：

```python
    def _create_widgets(self):
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        self._create_status_bar(main)
        self._create_scan_config(main)
        self._create_ocr_config(main)
        self._create_match_config(main)
        self._create_log_area(main)
        self._create_buttons(main)
```

替换为：

```python
    def _create_widgets(self):
        self._setup_styles()
        self._init_vars()
        self._create_topbar(self.root)
        self._create_bottombar(self.root)        # 先 BOTTOM 占位再 body fill
        body = tk.Frame(self.root, bg=COLOR_BG)
        body.pack(fill=tk.BOTH, expand=True)
        self._create_sidebar(body)
        self._create_main_area(body)
```

- [ ] **Step 2: 删除 6 个旧 `_create_*` 方法**

删除整段：
- `_create_status_bar`（约第 331-345 行）
- `_create_scan_config`（约第 349-396 行）
- `_create_ocr_config`（约第 400-424 行）
- `_create_match_config`（约第 428-469 行）
- `_create_log_area`（约第 473-508 行，含 `_reposition_clear` 内部函数与 `<Configure>` 绑定）
- `_create_buttons`（约第 512-524 行）

提示：使用 grep 验证删除完整。

Run: `python -c "import app; assert not hasattr(app.MainGUI, '_create_status_bar'); assert not hasattr(app.MainGUI, '_create_scan_config'); assert not hasattr(app.MainGUI, '_create_ocr_config'); assert not hasattr(app.MainGUI, '_create_match_config'); assert not hasattr(app.MainGUI, '_create_log_area'); assert not hasattr(app.MainGUI, '_create_buttons'); print('all six removed')"`
Expected: `all six removed`。

- [ ] **Step 3: 启动应用验证新布局**

Run: `python app.py`
Expected:
- 窗口 860×680 打开
- 顶部有白色状态栏：左侧红 ●「已停止」，右侧三个 cell（扫描次数 0、最近扫描 --、内存 X.X MB）
- 左侧 300px 浅灰侧边栏，两个 tab：「常用配置」「高级」
- 「常用配置」可见 4 个分组：扫描区域、扫描节奏、OCR、关键词，控件齐全
- 切到「高级」可见 3 个分组：帧差检测、浮窗外观、OCR 进阶
- 右侧大日志区（黑底彩字）
- 底部按钮栏：左 蓝填充「开始扫描」+ 红描边「停止扫描」，右 「清除匹配记录」「重置配置」

关闭窗口（缩到托盘）/ 右键托盘退出。

---

## Task 8: 状态指示灯三态 + 统计 label 文本格式

`_update_status` 当前只更新文字与窗口标题，新版需要根据状态切灯色。`_update_stats` 与 `_schedule_memory_update` 当前 set 的文本带前缀（"扫描: 28"），新布局已把前缀作为 cell 副标题，值 label 只放裸数值。

**Files:**
- Modify: `app.py`（改 `_update_status`、`_update_stats`、`_schedule_memory_update` 三处）

- [ ] **Step 1: 重写 `_update_status` 方法**

定位：原 `_update_status`（约第 917-919 行）。

旧实现：

```python
    def _update_status(self, text):
        self._lbl_status.config(text=f"状态: {text}")
        self._update_title(text)
```

替换为：

```python
    def _update_status(self, text):
        self._lbl_status.config(text=text)
        if '初始化' in text:
            color = COLOR_WARNING            # 黄
        elif text == '运行中':
            color = COLOR_SUCCESS            # 绿
        else:
            color = COLOR_DANGER             # 红：已停止 / 其它
        self._lbl_dot.config(fg=color)
        self._update_title(text)
```

- [ ] **Step 2: 重写 `_update_stats` 方法**

定位：原 `_update_stats`（约第 930-932 行）。

旧实现：

```python
    def _update_stats(self):
        self._lbl_count.config(text=f"扫描: {self.scan_count}")
        self._lbl_last.config(text=f"最后: {self.last_scan_time or '--'}")
```

替换为：

```python
    def _update_stats(self):
        self._lbl_count.config(text=str(self.scan_count))
        self._lbl_last.config(text=self.last_scan_time or '--')
```

- [ ] **Step 3: 改 `_schedule_memory_update` 中的 label 文本**

定位：原 `_schedule_memory_update`（约第 934-938 行）。`mb` 取到后的赋值行。

```python
        if mb is not None:
            self._lbl_mem.config(text=f"内存: {mb:.1f} MB")
```

替换为：

```python
        if mb is not None:
            self._lbl_mem.config(text=f"{mb:.1f} MB")
```

- [ ] **Step 4: 启动应用验证灯色与统计**

Run: `python app.py`
Expected:
- 启动时灯红，文字「已停止」
- 点「开始扫描」：灯先变黄（初始化中，可能很快），OCR 加载好后变绿（运行中），右侧三个 cell 数字开始更新
- 点「停止扫描」：灯回红，文字「已停止」
- OCR 失败场景（可选验证：临时把 banlist_file 设个不存在路径再启动）：灯回红，弹 messagebox

---

## Task 9: 全量手测

跑一遍所有交互，确认没遗漏。

**Files:**
- 无（仅手测）

- [ ] **Step 1: 启动并切 tab**

Run: `python app.py`
- [ ] 窗口大小 860×680
- [ ] 「常用配置」/「高级」切换控件齐全，状态保留
- [ ] 状态栏 ●、状态文字、3 个 cell 全部可见
- [ ] 底部 4 个按钮可见

- [ ] **Step 2: 控件持久化**

- [ ] 改「扫描间隔」滑块到 5.5（看 entry 同步显示）
- [ ] 改「字号」到 24
- [ ] 改「位置」到「顶部」
- [ ] 关闭应用 → 重启 → 确认这三项保留

- [ ] **Step 3: ROI 流程**

- [ ] 取消勾选「记住」，勾选「启用 ROI」，启动扫描 → 应弹半透明全屏选择窗口 → 拖框 → 释放 → 看到红色 ROI 边框 + 浮窗
- [ ] 停止 → 重新点开始 → 复用 saved_roi → 直接进运行
- [ ] 「保存当前」无 ROI 时弹 warning（先 取消「启用 ROI」清空 self.roi 测）
- [ ] 选预设：从 combobox 选「4+2」→ ROI 切换 + log 提示

- [ ] **Step 4: 关键词文件**

- [ ] 「浏览…」→ 选个 .txt → entry 更新
- [ ] 「编辑」→ Toplevel 编辑器打开 → 改内容 → 保存并关闭 → 日志确认
- [ ] 选不存在的文件路径 → 「编辑」→ askyesno 是否创建 → 取消/确认两条路径

- [ ] **Step 5: 状态灯三态**

- [ ] 已停止 = 红
- [ ] 点开始 → 「初始化中...」期间 = 黄
- [ ] OCR 加载完 + ROI 完事 → 「运行中」 = 绿
- [ ] 点停止 → 红

- [ ] **Step 6: 扫描运行**

- [ ] 顶部「扫描次数」「最近扫描」每次扫描后递增/更新
- [ ] 「内存」每 5 秒刷新
- [ ] 日志滚动，颜色（INFO 青绿、WARNING 黄、ERROR 红）正确
- [ ] 命中关键词时浮窗弹出 + 音效（如「音效提醒」开启）

- [ ] **Step 7: 日志清空与配置重置**

- [ ] 点日志 header「清空」按钮 → 日志区清空
- [ ] 点底部「清除匹配记录」→ overlay 累积匹配清空（再扫描时只显示新匹配）
- [ ] 点「重置配置」→ askyesno → 确认 → 控件回 defaults

- [ ] **Step 8: 热键**

- [ ] Ctrl+Alt+1 → 启动扫描
- [ ] Ctrl+Alt+2 → 停止扫描
- [ ] 主窗口 minimize 到托盘后热键仍工作

- [ ] **Step 9: 托盘**

- [ ] 关闭窗口（X）→ 隐藏到托盘
- [ ] 托盘左键 → 主窗口出现
- [ ] 托盘右键「退出」→ 进程退出（< 3 秒）

- [ ] **Step 10: CLI 入口未受影响**

Run: `python cli.py`
Expected: 进入 CLI 交互循环，无 import 错误。Ctrl+C 退出。

---

## 完成

所有任务完成且 Step 9 全打钩后，UI 重做完毕。是否提交：

```bash
git status
# 期望只有 app.py 和 docs/ 下的 spec/plan 是新增/修改
```

由用户决定 commit 时机与 message。
