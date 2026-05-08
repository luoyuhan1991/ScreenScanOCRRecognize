"""
关于视图：项目信息。
"""

import os
import sys
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
