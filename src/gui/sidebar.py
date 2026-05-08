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
    UI_FONT, FONT_SIZE_BASE, COLOR_BG_WINDOW,
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
        title = ttk.Label(self, text="✏  屏幕扫描", style="Sidebar.TLabel",
                          font=(UI_FONT, FONT_SIZE_BASE))
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

    main = tk.Frame(root, bg=COLOR_BG_WINDOW)
    main.pack(side="left", fill="both", expand=True)
    status = tk.Label(main, text="点击侧栏按钮", bg=COLOR_BG_WINDOW,
                      fg="white", font=(UI_FONT, 12))
    status.pack(expand=True)

    sb.set_active("scan")

    root.mainloop()
