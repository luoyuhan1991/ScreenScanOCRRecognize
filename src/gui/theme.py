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
COLOR_BG_BTN_DEFAULT       = "#222b40"   # 默认按钮 base（注：与 COLOR_BG_CARD_HOVER 同色，但语义不同）
COLOR_BG_BTN_HOVER         = "#2a3650"   # 默认按钮 hover
COLOR_BG_SIDEBAR_HOVER     = "#1f2538"   # Sidebar 按钮 hover

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
COLOR_PRIMARY_DISABLED_BG  = "#1f4a8c"
COLOR_PRIMARY_DISABLED_FG  = "#9bbfe2"
COLOR_DANGER_DISABLED_BG   = "#7a2828"
COLOR_DANGER_DISABLED_FG   = "#e8b5a8"

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
    _btn_bg       = COLOR_BG_BTN_DEFAULT
    _btn_hover    = COLOR_BG_BTN_HOVER
    _btn_press    = COLOR_BG_CARD
    _btn_disabled = COLOR_BG_SIDEBAR
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
            ("disabled", COLOR_PRIMARY_DISABLED_BG),
            ("pressed", COLOR_PRIMARY_PRESS),
            ("active", COLOR_PRIMARY_HOVER),
        ]})
    style.map("Primary.TButton", foreground=[("disabled", COLOR_PRIMARY_DISABLED_FG)])

    # ---- Danger（停止扫描） ----
    style.configure("Danger.TButton",
                    background=COLOR_DANGER, foreground="white",
                    bordercolor=COLOR_DANGER, lightcolor=COLOR_DANGER, darkcolor=COLOR_DANGER,
                    borderwidth=0, padding=(20, 8), relief="flat",
                    font=(UI_FONT, FONT_SIZE_BASE, "bold"))
    for prop in ("background", "bordercolor", "lightcolor", "darkcolor"):
        style.map("Danger.TButton", **{prop: [
            ("disabled", COLOR_DANGER_DISABLED_BG),
            ("pressed", COLOR_DANGER_PRESS),
            ("active", COLOR_DANGER_HOVER),
        ]})
    style.map("Danger.TButton", foreground=[("disabled", COLOR_DANGER_DISABLED_FG)])

    # ---- Sidebar 导航按钮（基础态 + 选中态由 Sidebar 自己刷 background） ----
    style.configure("Sidebar.TButton",
                    background=COLOR_BG_SIDEBAR, foreground=COLOR_TEXT_DIM,
                    bordercolor=COLOR_BG_SIDEBAR, lightcolor=COLOR_BG_SIDEBAR,
                    darkcolor=COLOR_BG_SIDEBAR,
                    borderwidth=0, padding=(8, 12), relief="flat",
                    font=(UI_FONT, FONT_SIZE_BASE))
    for prop in ("background", "bordercolor", "lightcolor", "darkcolor"):
        style.map("Sidebar.TButton", **{prop: [
            ("active", COLOR_BG_SIDEBAR_HOVER),
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
