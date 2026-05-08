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
    UI_FONT, FONT_SIZE_BASE,
    COLOR_BG_CARD, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING,
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
