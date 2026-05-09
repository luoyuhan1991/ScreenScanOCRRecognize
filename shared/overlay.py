"""
持久透明浮窗 + 累积匹配显示 + 新匹配音效。
两个版本共享：构造时注入 config 对象（duck-typed，只用 .get(key, default)）。
"""

import io
import math
import struct
import threading
import tkinter as tk
import tkinter.font as tkfont
import wave

try:
    import winsound
    _SOUND_AVAILABLE = True
except ImportError:
    _SOUND_AVAILABLE = False


def _build_chord_wav():
    """生成柔和 C 大三和弦 WAV (C5+E5+G5, 淡入淡出)。"""
    sample_rate = 22050
    duration = 0.35
    n_samples = int(sample_rate * duration)
    freqs = [523.25, 659.25, 783.99]  # C5, E5, G5
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
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
    """持久透明浮窗，左列累计匹配，右列本次 OCR。新匹配触发柔和和弦音效。"""

    def __init__(self, parent_root=None, config=None, logger=None):
        """
        Args:
            parent_root: tkinter 根窗口；为 None 时使用独立 Tk（不推荐用于无主循环场景）
            config: 提供 .get(key, default) 接口的配置对象，用于读取 matching.* 项
            logger: 可选 logger
        """
        self.parent_root = parent_root
        self._config = config
        self._logger = logger
        self._window = None
        self._canvas = None
        self._visible = False
        self._session_matches = {}  # {keyword: hint}
        self._setup_done = False
        self._hide_timer = None

    def setup(self):
        """创建窗口（幂等，只执行一次）。"""
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

        try:
            from ctypes import windll
            hwnd = windll.user32.GetParent(self._window.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_LAYERED | WS_EX_TRANSPARENT,
            )
        except Exception:
            pass

        self._canvas = tk.Canvas(
            self._window, bg='#010101', highlightthickness=0,
        )
        self._canvas.pack(fill='both', expand=True)
        self._window.withdraw()
        self._setup_done = True

    def update(self, ocr_results, matches):
        """
        更新浮窗内容。每次扫描调用，无匹配也会刷新（保持显示连续）。

        Args:
            ocr_results: list of dict，含 'text' 字段
            matches: list of dict，含 'keyword'/'hint'/'ocr_text' 字段
        """
        if not self._setup_done:
            self.setup()

        new_keywords = []
        for m in matches:
            kw = m.get('keyword', '')
            if kw and kw not in self._session_matches:
                self._session_matches[kw] = m.get('hint', '')
                new_keywords.append(kw)

        if new_keywords and self._cfg('matching.enable_sound', True) and _SOUND_AVAILABLE:
            threading.Thread(
                target=lambda: winsound.PlaySound(_CHORD_WAV, winsound.SND_MEMORY),
                daemon=True,
            ).start()

        self._redraw(ocr_results, matches)
        self._reset_hide_timer()

    def clear_session(self):
        """清空累积匹配记录（新一轮扫描开始时调用）。"""
        self._session_matches.clear()

    def hide(self):
        """立即隐藏浮窗。"""
        self._hide()

    def destroy(self):
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None
            self._canvas = None
            self._setup_done = False
            self._visible = False

    def _redraw(self, ocr_results, matches):
        if not self._window or not self._canvas:
            return

        font_size = int(self._cfg('matching.font_size', 18))
        effective_size = max(10, font_size - 2)
        font_tuple = ('Microsoft YaHei', effective_size, 'bold')

        font_obj = None
        try:
            font_obj = tkfont.Font(
                root=self._window, family='Microsoft YaHei',
                size=effective_size, weight='bold',
            )
            line_height = int(font_obj.metrics('linespace') * 1.15)
        except Exception:
            line_height = int(effective_size * 1.5)

        shadow_offset = max(1, effective_size // 30)
        matched_keywords = {m['keyword'] for m in matches if m.get('keyword')}

        # 屏幕封顶：浮窗最大不超过这些值，超出部分由 Canvas 自动裁剪（不再算字符截断）
        screen_w = self._window.winfo_screenwidth()
        screen_h = self._window.winfo_screenheight()
        kw_cap = int(screen_w * 0.20)
        hint_cap = int(screen_w * 0.20)
        ocr_cap = int(screen_w * 0.40)
        height_cap = int(screen_h * 0.50)

        # ===== 左栏：累计匹配 =====
        left_rows = sorted(
            self._session_matches.items(), key=lambda kv: kv[0].casefold(),
        )
        if not left_rows:
            left_rows_fmt = [('暂无匹配', '', '#aaaaaa', '#aaaaaa')]
        else:
            left_rows_fmt = [
                (kw, hint, '#ff3333', '#ff3333')
                for kw, hint in left_rows
            ]

        # ===== 右栏：命中行（红）+ 最多 10 条无命中行（绿）+ 摘要（灰） =====
        right_rows = []
        unmatched_lines = []
        for r in ocr_results:
            text = r.get('text', '') if isinstance(r, dict) else ''
            if not text:
                continue
            text_cf = text.casefold()
            if any(kw.casefold() in text_cf for kw in matched_keywords):
                right_rows.append((text, '#ff3333'))
            else:
                unmatched_lines.append(text)

        for text in unmatched_lines[:10]:
            right_rows.append((text, '#00ff00'))
        extra = len(unmatched_lines) - 10
        if extra > 0:
            right_rows.append((f'+ {extra} 行未显示', '#888888'))
        if not right_rows:
            right_rows.append(('暂无识别结果', '#aaaaaa'))

        # ===== 行数封顶：超过则截断并加「+ N 已隐藏」尾行 =====
        max_visible_rows = max(1, (height_cap - 8) // line_height)
        natural_rows = max(len(left_rows_fmt), len(right_rows))
        if natural_rows > max_visible_rows:
            visible_n = max(1, max_visible_rows - 1)
            if len(left_rows_fmt) > visible_n:
                hidden_l = len(left_rows_fmt) - visible_n
                left_rows_fmt = left_rows_fmt[:visible_n]
                left_rows_fmt.append(
                    (f'+ {hidden_l} 项已隐藏', '', '#888888', '#888888')
                )
            if len(right_rows) > visible_n:
                hidden_r = len(right_rows) - visible_n
                right_rows = right_rows[:visible_n]
                right_rows.append((f'+ {hidden_r} 行已隐藏', '#888888'))

        total_rows = max(len(left_rows_fmt), len(right_rows))

        # ===== 列宽：取自然最大宽度，但封顶到 cap；超出 Canvas 边界由窗口裁剪 =====
        def measure(text):
            try:
                if font_obj is not None:
                    return font_obj.measure(text)
                return len(text) * int(effective_size * 0.6)
            except Exception:
                return len(text) * int(effective_size * 0.6)

        max_kw_w = min(max((measure(r[0]) for r in left_rows_fmt), default=0), kw_cap)
        max_hint_w = min(max((measure(r[1]) for r in left_rows_fmt), default=0), hint_cap)
        max_ocr_w = min(max((measure(r[0]) for r in right_rows), default=0), ocr_cap)

        kw_hint_gap = 12
        mid_gap = 28
        padding = 6
        total_width = (
            padding + max_kw_w + kw_hint_gap + max_hint_w
            + mid_gap + max_ocr_w + shadow_offset + padding
        )
        total_height = total_rows * line_height + 8

        # 兜底：理论上 cap + 行截断已经控制住了，这里再夹一次
        total_width = min(total_width, int(screen_w * 0.95))
        total_height = min(total_height, int(screen_h * 0.95))

        position = self._cfg('matching.position', 'center')
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

        kw_x = padding
        hint_x = padding + max_kw_w + kw_hint_gap
        ocr_x = padding + max_kw_w + kw_hint_gap + max_hint_w + mid_gap
        start_y = 4 + line_height / 2

        for i in range(total_rows):
            y = start_y + i * line_height

            if i < len(left_rows_fmt):
                kw_t, hint_t, c_kw, c_hint = left_rows_fmt[i]
                self._draw_text(kw_x, y, kw_t, c_kw, font_tuple, shadow_offset)
                self._draw_text(hint_x, y, hint_t, c_hint, font_tuple, shadow_offset)

            if i < len(right_rows):
                ocr_t, c_ocr = right_rows[i]
                self._draw_text(ocr_x, y, ocr_t, c_ocr, font_tuple, shadow_offset)

        self._show()

    def _draw_text(self, x, y, text, color, font, shadow_offset):
        if not text:
            return
        self._canvas.create_text(
            x + shadow_offset, y + shadow_offset,
            text=text, font=font, fill='#000000', anchor='w',
        )
        self._canvas.create_text(
            x, y, text=text, font=font, fill=color, anchor='w',
        )

    def _show(self):
        if not self._visible and self._window:
            self._window.deiconify()
            self._visible = True

    def _reset_hide_timer(self):
        if self._hide_timer is not None:
            try:
                self._window.after_cancel(self._hide_timer)
            except Exception:
                pass
            self._hide_timer = None
        duration = float(self._cfg('matching.display_duration', 3))
        self._hide_timer = self._window.after(
            int(duration * 1000), self._hide,
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

    def _cfg(self, key, default):
        if self._config is None:
            return default
        try:
            v = self._config.get(key, default)
        except TypeError:
            v = self._config.get(key)
        return v if v is not None else default
