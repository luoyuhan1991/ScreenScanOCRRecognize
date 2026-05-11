"""命中提示音字节（C 大三和弦 PCM WAV，淡入淡出）。

被 ui/overlay.py（新 PySide6 版）和 shared/overlay.py（旧 tkinter 版）共用，
独立成模块避免新版 import 时被迫拉 tkinter。
"""
import io
import math
import struct
import wave


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


CHORD_WAV = _build_chord_wav()
