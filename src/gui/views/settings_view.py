"""
设置视图：高级配置（一次配好基本不动）。

包含：
- 帧差检测：MSE 阈值（0 = 每次都 OCR）
- 浮窗外观：字号、位置、音效
- OCR 进阶：图像反色
- 日志级别
- 配置文件路径展示（只读）
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


POSITION_DISPLAY = {"center": "居中", "top": "顶部", "bottom": "底部"}
POSITION_VALUE = {v: k for k, v in POSITION_DISPLAY.items()}


class SettingsView(BaseView):
    VIEW_KEY = "settings"

    def _build(self):
        self._init_vars()
        self._create_layout()
        self._load_settings()
        self._wire_save()

    def _init_vars(self):
        self.var_diff_threshold = tk.DoubleVar(value=5.0)
        self.var_fontsize = tk.IntVar(value=18)
        self.var_position = tk.StringVar(value="居中")
        self.var_sound = tk.BooleanVar(value=True)
        self.var_invert = tk.BooleanVar(value=False)
        self.var_log_level = tk.StringVar(value="INFO")

    def _create_layout(self):
        outer = ttk.Frame(self, style="Content.TFrame", padding=20)
        outer.pack(fill="both", expand=True)

        card = ttk.Frame(outer, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="设置（高级）", style="Header.TLabel").pack(
            anchor="w", pady=(0, 12))

        # ----- 帧差检测 -----
        self._section(card, "帧差检测")
        self._sub(card, "MSE 阈值（0 = 每次都 OCR）")
        r = self._row(card)
        ttk.Scale(r, from_=0, to=50, variable=self.var_diff_threshold, length=240,
                  command=self._on_diff_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_diff_threshold).pack(side="left", padx=(8, 0))

        # ----- 浮窗外观 -----
        self._section(card, "浮窗外观")
        self._sub(card, "字号（px）")
        r = self._row(card)
        ttk.Scale(r, from_=10, to=36, variable=self.var_fontsize, length=240,
                  command=self._on_fs_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_fontsize).pack(side="left", padx=(8, 0))

        self._sub(card, "位置")
        ttk.Combobox(card, textvariable=self.var_position, width=10,
                     state="readonly",
                     values=("居中", "顶部", "底部")).pack(anchor="w", pady=2)

        ttk.Checkbutton(card, text="音效提醒", variable=self.var_sound,
                        style="TCheckbutton").pack(anchor="w", pady=(8, 0))

        # ----- OCR 进阶 -----
        self._section(card, "OCR 进阶")
        ttk.Checkbutton(card, text="图像反色（黑底白字时启用）",
                        variable=self.var_invert,
                        style="TCheckbutton").pack(anchor="w", pady=2)

        # ----- 日志 -----
        self._section(card, "日志")
        self._sub(card, "日志级别")
        ttk.Combobox(card, textvariable=self.var_log_level, width=10,
                     state="readonly",
                     values=("DEBUG", "INFO", "WARNING", "ERROR")).pack(
            anchor="w", pady=2)

        # ----- 配置文件路径（只读） -----
        self._section(card, "配置文件")
        cfg_path = getattr(self.config, "_path", "(未加载)")
        ttk.Label(card, text=cfg_path, style="Dim.TLabel").pack(
            anchor="w", pady=(0, 8))

    def _section(self, parent, text):
        ttk.Label(parent, text=text, style="Section.TLabel").pack(
            anchor="w", pady=(14, 4))

    def _sub(self, parent, text):
        ttk.Label(parent, text=text, style="Dim.TLabel").pack(
            anchor="w", pady=(4, 2))

    def _row(self, parent):
        r = ttk.Frame(parent, style="Card.TFrame")
        r.pack(fill="x", pady=2)
        return r

    # ----- 滑块取整 -----

    def _on_diff_scale(self, val):
        try:
            self.var_diff_threshold.set(round(float(val), 1))
        except (ValueError, TypeError):
            pass

    def _on_fs_scale(self, val):
        try:
            self.var_fontsize.set(max(10, min(36, round(float(val)))))
        except (ValueError, TypeError):
            pass

    # ----- 配置读写 -----

    def _load_settings(self):
        cfg = self.config
        self.var_diff_threshold.set(cfg.get("scan.diff_threshold"))
        self.var_fontsize.set(cfg.get("matching.font_size"))
        self.var_position.set(POSITION_DISPLAY.get(cfg.get("matching.position"),
                                                     "居中"))
        self.var_sound.set(cfg.get("matching.enable_sound"))
        self.var_invert.set(cfg.get("ocr.enable_image_invert"))
        self.var_log_level.set(cfg.get("logging.level", "INFO"))

    def _save_settings(self, *_):
        cfg = self.config
        cfg.set("scan.diff_threshold", self.var_diff_threshold.get())
        cfg.set("matching.font_size", self.var_fontsize.get())
        cfg.set("matching.position",
                POSITION_VALUE.get(self.var_position.get(), "center"))
        cfg.set("matching.enable_sound", self.var_sound.get())
        cfg.set("ocr.enable_image_invert", self.var_invert.get())
        cfg.set("logging.level", self.var_log_level.get())
        cfg.save()
        # 通知 MainWindow 同步状态栏的声音开关
        if hasattr(self.main_window, "on_settings_changed"):
            self.main_window.on_settings_changed()

    def _wire_save(self):
        """所有变量变化时自动保存（避免依赖外部 save_settings 调用）。"""
        for v in (self.var_diff_threshold, self.var_fontsize, self.var_position,
                  self.var_sound, self.var_invert, self.var_log_level):
            v.trace_add("write", self._save_settings)

    def reload_from_config(self):
        """配置外部被重置时调用（比如 StatusBar 的"重置配置"）。"""
        # 解开 trace 防止重置过程触发 save 反向写
        self._load_settings()
