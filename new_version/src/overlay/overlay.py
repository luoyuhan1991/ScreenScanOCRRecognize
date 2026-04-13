import io
import math
import struct
import threading
import tkinter as tk
import tkinter.font as tkfont
import wave
import winsound
from ..config.config import config
from ..utils.logger import logger


def _build_chord_wav():
    """生成柔和 C 大三和弦 WAV (C5+E5+G5, 淡入淡出)"""
    sample_rate = 22050
    duration = 0.35
    n_samples = int(sample_rate * duration)
    freqs = [523.25, 659.25, 783.99]  # C5, E5, G5
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        # 淡入淡出包络
        fade = min(t / 0.05, 1.0) * min((duration - t) / 0.08, 1.0)
        val = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
        samples.append(int(val * fade * 16000))
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{n_samples}h', *samples))
    return buf.getvalue()


_CHORD_WAV = _build_chord_wav()


class Overlay:
    """持久透明浮窗"""

    def __init__(self, parent_root=None):
        self.parent_root = parent_root
        self._window = None
        self._canvas = None
        self._visible = False
        self._session_matches = {}  # {keyword: hint}
        self._setup_done = False
        self._hide_timer = None

    def setup(self):
        """创建窗口（只调用一次）"""
        if self._setup_done:
            return
        if self.parent_root:
            self._window = tk.Toplevel(self.parent_root)
        else:
            self._window = tk.Tk()

        self._window.overrideredirect(True)
        self._window.attributes('-topmost', True)
        try:
            self._window.attributes('-toolwindow', True)
        except Exception:
            pass
        self._window.attributes('-transparentcolor', '#010101')
        self._window.config(bg='#010101')

        # 鼠标穿透 (Windows)
        try:
            from ctypes import windll
            hwnd = windll.user32.GetParent(self._window.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            )
        except Exception:
            pass

        self._canvas = tk.Canvas(
            self._window, bg='#010101', highlightthickness=0
        )
        self._canvas.pack(fill='both', expand=True)

        self._window.withdraw()  # 初始隐藏
        self._setup_done = True

    def update(self, ocr_results, matches):
        """
        更新浮窗内容
        Args:
            ocr_results: list of dict with 'text'
            matches: list of dict with 'keyword', 'hint', 'ocr_text'
        """
        if not self._setup_done:
            self.setup()

        # 更新累积匹配记录
        new_matches = []
        for m in matches:
            kw = m['keyword']
            if kw not in self._session_matches:
                self._session_matches[kw] = m['hint']
                new_matches.append(kw)

        # 新匹配时播放柔和和弦提示
        if new_matches and config.get('matching.enable_sound', True):
            threading.Thread(
                target=lambda: winsound.PlaySound(_CHORD_WAV, winsound.SND_MEMORY),
                daemon=True,
            ).start()

        if not ocr_results or not matches:
            return

        # 有匹配 — 重绘并重置自动隐藏计时器
        self._redraw(ocr_results, matches)
        self._reset_hide_timer()

    def _redraw(self, ocr_results, matches):
        """重绘浮窗内容"""
        if not self._window or not self._canvas:
            return

        font_size = config.get('matching.font_size', 18)
        effective_size = max(10, font_size - 2)
        font_tuple = ('Microsoft YaHei', effective_size, 'bold')

        font_obj = None
        try:
            font_obj = tkfont.Font(
                root=self._window, family='Microsoft YaHei',
                size=effective_size, weight='bold'
            )
            line_height = int(font_obj.metrics('linespace') * 1.15)
        except Exception:
            line_height = int(effective_size * 1.5)

        shadow_offset = max(1, effective_size // 30)
        matched_keywords = {m['keyword'] for m in matches}

        # 构建左列: 累积匹配记录
        left_rows = sorted(
            self._session_matches.items(), key=lambda kv: kv[0].casefold()
        )
        # 构建右列: 当前 OCR 结果
        right_rows = []
        for r in ocr_results:
            text = r.get('text', '')
            if not text:
                continue
            is_matched = any(
                kw.casefold() in text.casefold() for kw in matched_keywords
            )
            color = '#ff3333' if is_matched else '#00ff00'
            right_rows.append((text, color))

        if not left_rows:
            left_rows_fmt = [('暂无匹配', '', '#aaaaaa', '#aaaaaa')]
        else:
            left_rows_fmt = [
                (kw, hint, '#ff3333', '#ff3333')
                for kw, hint in left_rows
            ]

        total_rows = max(len(left_rows_fmt), len(right_rows))
        if total_rows == 0:
            self._hide()
            return

        # 测量列宽
        def measure(text):
            try:
                if font_obj is not None:
                    return font_obj.measure(text)
                return len(text) * int(effective_size * 0.6)
            except Exception:
                return len(text) * int(effective_size * 0.6)

        max_kw_w = max(
            (measure(r[0]) for r in left_rows_fmt), default=0
        )
        max_hint_w = max(
            (measure(r[1]) for r in left_rows_fmt), default=0
        )
        max_ocr_w = max(
            (measure(r[0]) for r in right_rows), default=0
        )

        kw_hint_gap = 12
        mid_gap = 28
        padding = 6
        total_width = (
            padding + max_kw_w + kw_hint_gap + max_hint_w
            + mid_gap + max_ocr_w + shadow_offset + padding
        )
        total_height = total_rows * line_height + 8

        # 窗口位置
        screen_w = self._window.winfo_screenwidth()
        screen_h = self._window.winfo_screenheight()
        position = config.get('matching.position', 'center')

        if position == 'top':
            wx = (screen_w - total_width) // 2
            wy = 50
        elif position == 'bottom':
            wx = (screen_w - total_width) // 2
            wy = screen_h - total_height - 50
        else:
            wx = (screen_w - total_width) // 2
            wy = (screen_h - total_height) // 2

        self._window.geometry(f"{total_width}x{total_height}+{wx}+{wy}")
        self._canvas.config(width=total_width, height=total_height)
        self._canvas.delete('all')

        # 绘制
        kw_x = padding
        hint_x = padding + max_kw_w + kw_hint_gap
        ocr_x = padding + max_kw_w + kw_hint_gap + max_hint_w + mid_gap
        start_y = 4 + line_height / 2

        for i in range(total_rows):
            y = start_y + i * line_height

            # 左列
            if i < len(left_rows_fmt):
                kw_t, hint_t, c_kw, c_hint = left_rows_fmt[i]
                self._draw_text(
                    kw_x, y, kw_t, c_kw, font_tuple, shadow_offset
                )
                self._draw_text(
                    hint_x, y, hint_t, c_hint, font_tuple, shadow_offset
                )

            # 右列
            if i < len(right_rows):
                ocr_t, c_ocr = right_rows[i]
                self._draw_text(
                    ocr_x, y, ocr_t, c_ocr, font_tuple, shadow_offset
                )

        self._show()

    def _draw_text(self, x, y, text, color, font, shadow_offset):
        if not text:
            return
        self._canvas.create_text(
            x + shadow_offset, y + shadow_offset,
            text=text, font=font, fill='#000000', anchor='w'
        )
        self._canvas.create_text(
            x, y, text=text, font=font, fill=color, anchor='w'
        )

    def _show(self):
        if not self._visible and self._window:
            self._window.deiconify()
            self._visible = True

    def _reset_hide_timer(self):
        """重置自动隐藏计时器"""
        if self._hide_timer is not None:
            try:
                self._window.after_cancel(self._hide_timer)
            except Exception:
                pass
            self._hide_timer = None
        duration = config.get('matching.display_duration', 3.0)
        self._hide_timer = self._window.after(
            int(duration * 1000), self._hide
        )

    def _hide(self):
        if self._hide_timer is not None:
            try:
                self._window.after_cancel(self._hide_timer)
            except Exception:
                pass
            self._hide_timer = None
        if self._visible and self._window:
            self._window.withdraw()
            self._visible = False

    def clear_session(self):
        """清除累积匹配记录（新一局游戏时调用）"""
        self._session_matches.clear()

    def destroy(self):
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
