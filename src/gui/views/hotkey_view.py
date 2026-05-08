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
