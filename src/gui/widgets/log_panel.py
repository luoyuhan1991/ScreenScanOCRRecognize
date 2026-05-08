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
