"""
ScreenScanOCRRecognize (new_version) - GUI 主程序
tkinter 图形界面，包含扫描控制、参数配置、状态监控、日志显示和透明浮窗
"""

import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from src.config.config import config, DEFAULT_BANLIST_FILE, PROJECT_ROOT
from src.pipeline.pipeline import ScanPipeline
from src.utils.logger import logger, configure_from_config
from src.utils.hotkey import HotkeyManager
from shared.overlay import Overlay


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


# ---------------------------------------------------------------------------
# 托盘图标 (内联，避免额外文件)
# ---------------------------------------------------------------------------

def _make_tray_icon_image():
    """生成 64x64 托盘图标"""
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


def _setup_tray(root, on_show, on_quit, tooltip="屏幕扫描OCR识别"):
    """创建并启动系统托盘图标"""
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

    image = _make_tray_icon_image()
    if image is None:
        return None

    menu = pystray.Menu(
        pystray.MenuItem("显示主窗口", lambda: _run_on_main(on_show), default=True),
        pystray.MenuItem("退出", lambda: _run_on_main(on_quit)),
    )
    icon = pystray.Icon("screen_scan_ocr", image, tooltip, menu=menu)

    def _run():
        try:
            icon.run()
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()

    class _Ctrl:
        def stop(self):
            try:
                icon.stop()
            except Exception:
                pass

    return _Ctrl()


# ---------------------------------------------------------------------------
# ROI 交互选择
# ---------------------------------------------------------------------------

def select_roi_interactive(parent=None):
    """
    截屏后显示半透明全屏窗口，让用户拖选 ROI 矩形。
    Returns (x1, y1, x2, y2) 或 None
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
# 内存占用
# ---------------------------------------------------------------------------

def _get_memory_mb():
    """返回当前进程 RSS (MB)，失败返回 None"""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
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

        # 64 位 Python 必须正确声明 HANDLE 类型，否则伪句柄 -1 会被截断
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE

        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(pmc)
        handle = kernel32.GetCurrentProcess()

        # Windows 7+ 可直接用 kernel32.K32GetProcessMemoryInfo
        K32 = getattr(kernel32, 'K32GetProcessMemoryInfo', None)
        if K32 is not None:
            K32.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
            K32.restype = wintypes.BOOL
            if K32(handle, ctypes.byref(pmc), pmc.cb):
                return pmc.WorkingSetSize / (1024 * 1024)

        # 回退到 psapi.dll
        psapi = ctypes.windll.psapi
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
            return pmc.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# MainGUI
# ---------------------------------------------------------------------------

class MainGUI:
    """主 GUI 界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("屏幕扫描OCR识别系统")
        self.root.geometry("860x680")

        # ---------- 配置 ----------
        config.load()
        configure_from_config(config)

        # ---------- Pipeline & Overlay ----------
        self.pipeline = ScanPipeline()
        self.overlay = Overlay(parent_root=self.root, config=config, logger=logger)

        # ---------- 状态 ----------
        self.is_running = False
        self.scan_thread = None
        self.stop_event = threading.Event()
        self.scan_count = 0
        self.last_scan_time = None
        self.roi = None

        # ROI 可视化边框窗口
        self._roi_border_win = None

        # ---------- 日志队列 ----------
        self.log_queue = queue.Queue(maxsize=1000)

        # ---------- 构建 UI ----------
        self._create_widgets()
        self._load_settings()

        # ---------- 日志 ----------
        self._setup_gui_logger()
        self._drain_log_queue()

        # ---------- 托盘 ----------
        self._tray = _setup_tray(
            self.root,
            on_show=self._tray_show,
            on_quit=self._tray_quit,
            tooltip="屏幕扫描OCR识别"
        )
        if self._tray:
            self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
            self._append_log("托盘图标已启用：关闭窗口将缩到托盘，右键托盘可退出", "INFO")
        else:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---------- 热键 ----------
        self._hotkey_mgr = HotkeyManager()
        self.root.after_idle(self._register_hotkeys)

        # ---------- 内存显示 ----------
        self._schedule_memory_update()

        # ---------- 窗口标题 ----------
        self._update_title("已停止")

    # -----------------------------------------------------------------------
    # UI 构建
    # -----------------------------------------------------------------------

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

        # 默认按钮：浅灰填充、无边框；clam 的 lightcolor/darkcolor 必须一并刷成 bg 才能去掉 3D 边
        _btn_default_bg = "#ebebef"
        _btn_default_hover = "#dcdce0"
        _btn_default_press = "#c8c8cd"
        style.configure("TButton", background=_btn_default_bg, foreground=COLOR_TEXT,
                        bordercolor=_btn_default_bg, lightcolor=_btn_default_bg,
                        darkcolor=_btn_default_bg, borderwidth=0,
                        padding=(12, 6), relief="flat", font=(UI_FONT, 9))
        style.map("TButton",
                  background=[("disabled", "#f3f3f5"),
                              ("pressed", _btn_default_press),
                              ("active", _btn_default_hover)],
                  bordercolor=[("disabled", "#f3f3f5"),
                               ("pressed", _btn_default_press),
                               ("active", _btn_default_hover)],
                  lightcolor=[("disabled", "#f3f3f5"),
                              ("pressed", _btn_default_press),
                              ("active", _btn_default_hover)],
                  darkcolor=[("disabled", "#f3f3f5"),
                             ("pressed", _btn_default_press),
                             ("active", _btn_default_hover)],
                  foreground=[("disabled", "#a0a0a0")])

        # Primary（开始）：实色蓝填充，禁用时保持白字 + 浅蓝
        _primary_press = "#003e80"
        _primary_hover = "#0050a0"
        _primary_disabled = "#9bbfe2"
        style.configure("Primary.TButton", background=COLOR_PRIMARY, foreground="white",
                        bordercolor=COLOR_PRIMARY, lightcolor=COLOR_PRIMARY,
                        darkcolor=COLOR_PRIMARY, borderwidth=0,
                        padding=(24, 10), relief="flat",
                        font=(UI_FONT, 10, "bold"))
        style.map("Primary.TButton",
                  background=[("disabled", _primary_disabled),
                              ("pressed", _primary_press),
                              ("active", _primary_hover)],
                  bordercolor=[("disabled", _primary_disabled),
                               ("pressed", _primary_press),
                               ("active", _primary_hover)],
                  lightcolor=[("disabled", _primary_disabled),
                              ("pressed", _primary_press),
                              ("active", _primary_hover)],
                  darkcolor=[("disabled", _primary_disabled),
                             ("pressed", _primary_press),
                             ("active", _primary_hover)],
                  foreground=[("disabled", "white")])

        # Danger（停止）：从「白底红描边」改为实色红填充，避免 clam 双边框；禁用时浅粉 + 白字
        _danger_press = "#8b2400"
        _danger_hover = "#b53000"
        _danger_disabled = "#e8b5a8"
        style.configure("Danger.TButton", background=COLOR_DANGER, foreground="white",
                        bordercolor=COLOR_DANGER, lightcolor=COLOR_DANGER,
                        darkcolor=COLOR_DANGER, borderwidth=0,
                        padding=(24, 10), relief="flat",
                        font=(UI_FONT, 10, "bold"))
        style.map("Danger.TButton",
                  background=[("disabled", _danger_disabled),
                              ("pressed", _danger_press),
                              ("active", _danger_hover)],
                  bordercolor=[("disabled", _danger_disabled),
                               ("pressed", _danger_press),
                               ("active", _danger_hover)],
                  lightcolor=[("disabled", _danger_disabled),
                              ("pressed", _danger_press),
                              ("active", _danger_hover)],
                  darkcolor=[("disabled", _danger_disabled),
                             ("pressed", _danger_press),
                             ("active", _danger_hover)],
                  foreground=[("disabled", "white")])

        # Tab：所有 tab 粗体；选中态 padding 更大、白底蓝字凸出
        style.configure("TNotebook", background=COLOR_SIDEBAR, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_SIDEBAR, foreground=COLOR_SUBTEXT,
                        padding=(12, 5), font=(UI_FONT, 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD)],
                  foreground=[("selected", COLOR_PRIMARY)],
                  padding=[("selected", (20, 10))],
                  expand=[("selected", (1, 1, 1, 0))])

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

    def _create_widgets(self):
        self._setup_styles()
        self._init_vars()
        self._create_topbar(self.root)
        self._create_bottombar(self.root)        # 先 BOTTOM 占位再 body fill
        body = tk.Frame(self.root, bg=COLOR_BG)
        body.pack(fill=tk.BOTH, expand=True)
        self._create_sidebar(body)
        self._create_main_area(body)

    # -----------------------------------------------------------------------
    # 配置读写
    # -----------------------------------------------------------------------

    def _load_settings(self):
        self._var_enable_roi.set(config.get('scan.roi') is not None)
        self._var_remember_roi.set(True)
        self._var_gpu.set(config.get('gpu.enabled'))
        self._var_interval.set(config.get('scan.interval_seconds'))
        self._var_diff_threshold.set(config.get('scan.diff_threshold'))

        self._var_lang.set(config.get('ocr.language'))
        self._var_confidence.set(config.get('ocr.min_confidence'))
        self._var_invert.set(config.get('ocr.enable_image_invert'))

        self._var_banlist.set(config.get('files.banlist_file', DEFAULT_BANLIST_FILE))
        self._var_duration.set(config.get('matching.display_duration'))
        self._var_fontsize.set(config.get('matching.font_size'))
        self._var_sound.set(config.get('matching.enable_sound'))

        pos_map = {'center': '居中', 'top': '顶部', 'bottom': '底部'}
        self._var_position.set(pos_map.get(config.get('matching.position'), '居中'))

        # ROI 预设下拉
        self._refresh_presets()

    def _save_settings(self):
        config.set('scan.interval_seconds', self._var_interval.get())
        config.set('scan.diff_threshold', self._var_diff_threshold.get())
        config.set('gpu.enabled', self._var_gpu.get())

        config.set('ocr.language', self._var_lang.get())
        config.set('ocr.min_confidence', round(self._var_confidence.get(), 2))
        config.set('ocr.enable_image_invert', self._var_invert.get())

        config.set('files.banlist_file', self._var_banlist.get())
        config.set('matching.display_duration', self._var_duration.get())
        config.set('matching.font_size', self._var_fontsize.get())
        config.set('matching.enable_sound', self._var_sound.get())

        pos_map = {'居中': 'center', '顶部': 'top', '底部': 'bottom'}
        config.set('matching.position', pos_map.get(self._var_position.get(), 'center'))

        config.save()

    # -----------------------------------------------------------------------
    # ROI 预设
    # -----------------------------------------------------------------------

    def _refresh_presets(self):
        presets = config.get('scan.roi_presets') or {}
        names = list(presets.keys())
        self._combo_preset['values'] = names
        if names:
            self._combo_preset.current(0)

    def _on_preset_selected(self, event=None):
        name = self._var_roi_preset.get()
        presets = config.get('scan.roi_presets') or {}
        roi = presets.get(name)
        if roi:
            self.roi = tuple(roi)
            config.set('scan.roi', list(roi))
            config.save()
            self._append_log(f"已应用ROI预设 '{name}': {roi}", "INFO")

    def _save_roi_preset(self):
        if self.roi is None:
            messagebox.showwarning("提示", "当前没有可保存的ROI区域")
            return
        name = simpledialog.askstring("保存预设", "请输入预设名称:", parent=self.root)
        if not name:
            return
        presets = config.get('scan.roi_presets') or {}
        presets[name] = list(self.roi)
        config.set('scan.roi_presets', presets)
        config.save()
        self._refresh_presets()
        self._append_log(f"ROI预设 '{name}' 已保存: {list(self.roi)}", "INFO")

    # -----------------------------------------------------------------------
    # 控件事件回调
    # -----------------------------------------------------------------------

    def _on_interval_scale(self, val):
        try:
            v = round(float(val) * 2) / 2
            self._var_interval.set(max(0.5, min(15.0, v)))
        except (ValueError, TypeError):
            pass

    def _on_diff_scale(self, val):
        try:
            self._var_diff_threshold.set(round(float(val), 1))
        except (ValueError, TypeError):
            pass

    def _on_conf_scale(self, val):
        try:
            v = round(float(val) / 0.05) * 0.05
            self._var_confidence.set(round(v, 2))
        except (ValueError, TypeError):
            pass

    def _on_dur_scale(self, val):
        try:
            v = round(float(val) * 2) / 2
            self._var_duration.set(max(1.0, min(10.0, v)))
        except (ValueError, TypeError):
            pass

    def _on_fs_scale(self, val):
        try:
            self._var_fontsize.set(max(10, min(36, round(float(val)))))
        except (ValueError, TypeError):
            pass

    # -----------------------------------------------------------------------
    # 扫描控制
    # -----------------------------------------------------------------------

    def on_start(self):
        if self.is_running:
            return

        self._save_settings()
        self.overlay.clear_session()

        self._btn_start.config(state=tk.DISABLED)
        self._update_status("初始化中...")
        self._append_log("正在初始化 OCR 引擎...", "INFO")

        threading.Thread(target=self._init_and_start, daemon=True).start()

    def _init_and_start(self):
        try:
            self.pipeline.init()
            self.root.after(0, self._after_init_ok)
        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda: self._after_init_fail(msg))

    def _after_init_ok(self):
        self._append_log("OCR 初始化完成", "INFO")

        # ROI
        if self._var_enable_roi.get():
            saved = config.get('scan.roi')
            if self._var_remember_roi.get() and saved:
                self.roi = tuple(saved)
                self._append_log(f"使用已保存 ROI: {self.roi}", "INFO")
                self._start_scanning()
                return
            else:
                self.root.iconify()
                self.root.after(300, self._do_roi_select)
                return
        else:
            self.roi = None

        self._start_scanning()

    def _do_roi_select(self):
        """延迟执行 ROI 交互选择（避免阻塞主线程）"""
        self.roi = select_roi_interactive(parent=self.root)
        if self.roi:
            self._append_log(f"ROI 已选择: {self.roi}", "INFO")
            config.set('scan.roi', list(self.roi))
            config.save()
        else:
            self._append_log("ROI 选择取消，使用全屏", "WARNING")
        self._start_scanning()

    def _start_scanning(self):
        """设置 ROI、Overlay 并启动扫描线程"""
        self.pipeline.set_roi(self.roi)

        # 设置 Overlay
        self.overlay.setup()

        # 启动扫描
        self.is_running = True
        self.stop_event.clear()
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()

        self._btn_stop.config(state=tk.NORMAL)
        self._update_status("运行中")
        self._append_log("扫描已启动", "INFO")

        self._show_roi_border()

    def _after_init_fail(self, msg):
        self._append_log(f"初始化失败: {msg}", "ERROR")
        messagebox.showerror("错误", f"OCR 初始化失败:\n{msg}")
        self._btn_start.config(state=tk.NORMAL)
        self._update_status("已停止")

    def on_stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.stop_event.set()
        self._hide_roi_border()
        self.overlay.hide()
        self._btn_start.config(state=tk.NORMAL)
        self._btn_stop.config(state=tk.DISABLED)
        self._update_status("已停止")
        self._append_log("扫描已停止", "INFO")

    def _scan_loop(self):
        try:
            while not self.stop_event.is_set():
                interval = self._var_interval.get()
                self.scan_count += 1
                start = time.time()
                self.last_scan_time = datetime.now().strftime('%H:%M:%S')

                result = self.pipeline.scan_once()

                if result.skipped:
                    status_txt = "跳过(无变化)"
                else:
                    status_txt = f"{len(result.ocr_results)}行"

                self._append_log(
                    f"[#{self.scan_count}] OCR: {status_txt}, "
                    f"匹配: {len(result.matches)}, "
                    f"耗时: {result.duration:.3f}s",
                    "INFO"
                )

                if result.matches:
                    for m in result.matches:
                        self._append_log(
                            f"  >>> {m['keyword']} | {m['hint']}", "WARNING"
                        )

                # 更新 Overlay（调度到主线程）— 跳过时复用上次结果，仍需刷新
                ocr = result.ocr_results
                matches = result.matches
                self.root.after(0, lambda o=ocr, m=matches: self.overlay.update(o, m))

                # 更新统计（主线程）
                self.root.after(0, self._update_stats)

                # 等待
                elapsed = time.time() - start
                wait = max(0, interval - elapsed)
                waited = 0.0
                while waited < wait and not self.stop_event.is_set():
                    time.sleep(0.3)
                    waited += 0.3

        except Exception as e:
            self._append_log(f"扫描异常: {e}", "ERROR")
        finally:
            self.is_running = False
            self.root.after(0, self._on_scan_thread_exit)

    def _on_scan_thread_exit(self):
        """扫描线程结束后统一恢复 UI 状态"""
        self._hide_roi_border()
        self.overlay.hide()
        self._btn_start.config(state=tk.NORMAL)
        self._btn_stop.config(state=tk.DISABLED)
        self._update_status("已停止")

    # -----------------------------------------------------------------------
    # 杂项 UI 操作
    # -----------------------------------------------------------------------

    def _browse_banlist(self):
        cur = self._var_banlist.get()
        init_dir = os.path.dirname(cur) if cur else "."
        path = filedialog.askopenfilename(
            title="选择关键词文件", initialdir=init_dir,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if path:
            self._var_banlist.set(path)
            self._save_settings()

    def _edit_banlist(self):
        path = self._var_banlist.get()
        if not path:
            messagebox.showwarning("提示", "请先选择关键词文件")
            return

        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)

        if not os.path.exists(path):
            if not messagebox.askyesno("确认", f"文件不存在:\n{path}\n是否创建?"):
                return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write("")

        # 简单文本编辑窗口
        win = tk.Toplevel(self.root)
        win.title(f"编辑关键词 - {os.path.basename(path)}")
        win.geometry("600x400")
        win.attributes('-topmost', True)

        txt = scrolledtext.ScrolledText(win, font=("Consolas", 11), wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        with open(path, 'r', encoding='utf-8') as f:
            txt.insert('1.0', f.read())

        def save_and_close():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(txt.get('1.0', tk.END).rstrip('\n') + '\n')
            self._append_log(f"关键词文件已保存: {path}", "INFO")
            win.destroy()

        btn_fr = ttk.Frame(win)
        btn_fr.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_fr, text="保存并关闭", command=save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_fr, text="取消", command=win.destroy).pack(side=tk.RIGHT, padx=5)

    def _clear_session(self):
        self.overlay.clear_session()
        self._append_log("累积匹配记录已清除", "INFO")

    def _reset_config(self):
        if messagebox.askyesno("确认", "重置所有配置为默认值?"):
            config.load()
            self._load_settings()
            self._append_log("配置已重置", "INFO")

    def _clear_log(self):
        self._log_text.delete('1.0', tk.END)

    # -----------------------------------------------------------------------
    # ROI 边框可视化
    # -----------------------------------------------------------------------

    def _show_roi_border(self):
        try:
            roi = self.roi
            padding = config.get('scan.roi_padding')

            import ctypes
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)

            if roi:
                x1, y1, x2, y2 = roi
                x1 = max(0, x1 - padding)
                y1 = max(0, y1 - padding)
                x2 = min(sw, x2 + padding)
                y2 = min(sh, y2 + padding)
            else:
                x1, y1, x2, y2 = 0, 0, sw, sh

            w, h = x2 - x1, y2 - y1
            if w <= 0 or h <= 0:
                return

            win = tk.Toplevel(self.root)
            win.withdraw()
            win.overrideredirect(True)
            win.attributes('-topmost', True)
            win.attributes('-transparentcolor', 'black')
            win.geometry(f'{w}x{h}+{x1}+{y1}')
            win.config(bg='black')

            c = tk.Canvas(win, width=w, height=h, bg='black', highlightthickness=0, bd=0)
            c.pack(fill=tk.BOTH, expand=True)
            c.create_rectangle(1, 1, w - 1, h - 1, outline='#ff3333', width=3, fill='')

            win.deiconify()
            self._roi_border_win = win
        except Exception as e:
            logger.debug(f"ROI 边框显示失败: {e}")

    def _hide_roi_border(self):
        try:
            if self._roi_border_win:
                self._roi_border_win.destroy()
                self._roi_border_win = None
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # 状态 / 标题 / 统计
    # -----------------------------------------------------------------------

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

    def _update_title(self, status):
        base = "屏幕扫描OCR识别系统"
        if status == "运行中":
            self.root.title(f"【扫描中】{base}")
        elif "初始化" in status:
            self.root.title(f"【初始化中】{base}")
        else:
            self.root.title(base)

    def _update_stats(self):
        self._lbl_count.config(text=str(self.scan_count))
        self._lbl_last.config(text=self.last_scan_time or '--')

    def _schedule_memory_update(self):
        mb = _get_memory_mb()
        if mb is not None:
            self._lbl_mem.config(text=f"{mb:.1f} MB")
        self.root.after(5000, self._schedule_memory_update)

    # -----------------------------------------------------------------------
    # 日志
    # -----------------------------------------------------------------------

    def _setup_gui_logger(self):
        class _QueueHandler(logging.Handler):
            def __init__(self, q):
                super().__init__()
                self._q = q

            def emit(self, record):
                try:
                    msg = self.format(record) + '\n'
                    self._q.put_nowait((msg, record.levelname))
                except Exception:
                    pass

        handler = _QueueHandler(self.log_queue)
        handler.setLevel(logging.DEBUG)
        queue_formatter = logging.Formatter('%(asctime)s - %(message)s')
        queue_formatter.default_msec_format = '%s.%03d'
        handler.setFormatter(queue_formatter)

        # 添加到 screen_scan logger 而非 root logger，避免日志重复
        from src.utils.logger import logger as app_logger
        app_logger.addHandler(handler)

    def _append_log(self, message, level='INFO'):
        # %f 输出 6 位微秒，截到 3 位毫秒，得到 "2026-05-07 10:56:27.582"，与 logger 输出对齐
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        try:
            self.log_queue.put_nowait((f"{ts} - {message}\n", level))
        except queue.Full:
            pass

    def _drain_log_queue(self):
        count = 0
        while count < 15:
            try:
                msg, lvl = self.log_queue.get_nowait()
                self._log_text.insert(tk.END, msg, lvl)
                count += 1
            except queue.Empty:
                break
        if count > 0:
            self._log_text.see(tk.END)
            # 限制行数
            lines = int(self._log_text.index('end-1c').split('.')[0])
            if lines > 2000:
                self._log_text.delete('1.0', '200.0')
        self.root.after(100, self._drain_log_queue)

    # -----------------------------------------------------------------------
    # 热键
    # -----------------------------------------------------------------------

    def _register_hotkeys(self):
        try:
            self._hotkey_mgr.register('ctrl+alt+1', lambda: self.root.after(0, self.on_start), "开始扫描")
            self._hotkey_mgr.register('ctrl+alt+2', lambda: self.root.after(0, self.on_stop), "停止扫描")
            self._append_log("热键: Ctrl+Alt+1 开始, Ctrl+Alt+2 停止", "INFO")
        except Exception as e:
            self._append_log(f"热键注册失败: {e}", "WARNING")

    # -----------------------------------------------------------------------
    # 托盘 / 关闭
    # -----------------------------------------------------------------------

    def _minimize_to_tray(self):
        self.root.withdraw()

    def _tray_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _tray_quit(self):
        self._on_close()

    def _on_close(self):
        """清理 + 看门狗兜底：跑完所有清理就主动退出；任一步挂死则 3 秒后强杀"""
        import os
        import threading

        # 看门狗：无论清理走到哪一步，3 秒后强制结束进程
        watchdog = threading.Timer(3.0, lambda: os._exit(0))
        watchdog.daemon = True
        watchdog.start()

        # 立刻隐藏窗口，给用户即时反馈
        try:
            self.root.withdraw()
        except Exception:
            pass

        # 依次清理，每个独立 try/except——单步抛错不影响后续
        # 但若某步真"挂死"（不抛错也不返回），主线程会卡在那里，由 watchdog 兜底
        try:
            self._hide_roi_border()
        except Exception:
            pass
        try:
            self.overlay.destroy()
        except Exception:
            pass
        try:
            if getattr(self, '_tray', None):
                self._tray.stop()
        except Exception:
            pass
        try:
            self._hotkey_mgr.unregister_all()
        except Exception:
            pass
        try:
            self.pipeline.release()
        except Exception:
            pass

        os._exit(0)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    app = MainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
