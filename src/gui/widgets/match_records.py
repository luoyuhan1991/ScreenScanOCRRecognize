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
    UI_FONT, FONT_SIZE_BASE,
    COLOR_BG_INPUT, COLOR_BORDER,
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
