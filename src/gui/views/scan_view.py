"""
扫描视图：简单/常用配置 + 日志面板 + 匹配记录面板。

布局：
    +------------------------+--------------------+
    |   扫描配置 (cfg panel)  |   运行日志          |
    |   ROI / 间隔 / OCR /    |                    |
    |   词库 / 显示时长       +--------------------+
    |                        |   匹配记录 (最近10)  |
    +------------------------+--------------------+
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
from src.config.config import DEFAULT_BANLIST_FILE


class ScanView(BaseView):
    VIEW_KEY = "scan"

    def _build(self):
        self._init_vars()
        self._create_layout()
        self._load_settings()

    # -----------------------------------------------------------------------
    # Tk 变量
    # -----------------------------------------------------------------------

    def _init_vars(self):
        self.var_enable_roi      = tk.BooleanVar()
        self.var_remember_roi    = tk.BooleanVar(value=True)
        self.var_roi_preset      = tk.StringVar()
        self.var_interval        = tk.DoubleVar(value=2.0)
        self.var_lang            = tk.StringVar(value="ch")
        self.var_gpu             = tk.BooleanVar(value=True)
        self.var_confidence      = tk.DoubleVar(value=0.3)
        self.var_banlist         = tk.StringVar(value=DEFAULT_BANLIST_FILE)
        self.var_duration        = tk.DoubleVar(value=3.0)

    # -----------------------------------------------------------------------
    # 布局
    # -----------------------------------------------------------------------

    def _create_layout(self):
        # 整体 padding
        outer = ttk.Frame(self, style="Content.TFrame", padding=12)
        outer.pack(fill="both", expand=True)

        # 左：扫描配置卡
        cfg_card = ttk.Frame(outer, style="Card.TFrame", padding=12)
        cfg_card.pack(side="left", fill="y", padx=(0, 8))
        cfg_card.config(width=320)
        cfg_card.pack_propagate(False)
        self._build_config_panel(cfg_card)

        # 右：日志 + 匹配记录（上下两栏）
        right = ttk.Frame(outer, style="Content.TFrame")
        right.pack(side="left", fill="both", expand=True)

        # MainWindow 持有 LogPanel / MatchRecords 实例；这里只占位
        self._log_slot = ttk.Frame(right, style="Content.TFrame")
        self._log_slot.pack(fill="both", expand=True, pady=(0, 8))
        self._match_slot = ttk.Frame(right, style="Content.TFrame")
        self._match_slot.pack(fill="both", expand=True)

    def attach_panels(self, log_panel, match_panel):
        """MainWindow 在创建本 View 后调用一次，把常驻面板挂进来。

        log_panel / match_panel 的 master 仍是 MainWindow.content（创建时的
        parent）；mount() 里用 pack(in_=self._log_slot) 把它们布局到 ScanView
        的占位 slot 中——这是 tkinter 跨容器布局的标准模式。
        """
        self.log_panel = log_panel
        self.match_panel = match_panel

    def mount(self):
        """切到本视图时把面板 pack 进 slot。"""
        if hasattr(self, "log_panel"):
            self.log_panel.pack(in_=self._log_slot, fill="both", expand=True)
        if hasattr(self, "match_panel"):
            self.match_panel.pack(in_=self._match_slot, fill="both", expand=True)

    def unmount(self):
        if hasattr(self, "log_panel"):
            self.log_panel.pack_forget()
        if hasattr(self, "match_panel"):
            self.match_panel.pack_forget()

    # -----------------------------------------------------------------------
    # 配置面板
    # -----------------------------------------------------------------------

    def _build_config_panel(self, parent):
        ttk.Label(parent, text="扫描配置", style="Header.TLabel").pack(
            anchor="w", pady=(0, 12))

        self._section(parent, "扫描区域")
        r = self._row(parent)
        ttk.Checkbutton(r, text="启用 ROI", variable=self.var_enable_roi,
                        style="TCheckbutton").pack(side="left")
        ttk.Checkbutton(r, text="记住", variable=self.var_remember_roi,
                        style="TCheckbutton").pack(side="left", padx=(10, 0))

        self._sub(parent, "ROI 预设")
        r = self._row(parent)
        self._combo_preset = ttk.Combobox(r, textvariable=self.var_roi_preset,
                                           width=14, state="readonly")
        self._combo_preset.pack(side="left")
        self._combo_preset.bind("<<ComboboxSelected>>", self._on_preset_selected)
        ttk.Button(r, text="保存当前",
                   command=self._save_preset).pack(side="left", padx=(6, 0))

        self._section(parent, "扫描节奏")
        self._sub(parent, "扫描间隔（秒）")
        r = self._row(parent)
        ttk.Scale(r, from_=0.5, to=15, variable=self.var_interval, length=180,
                  command=self._on_interval_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_interval).pack(side="left", padx=(6, 0))

        self._section(parent, "OCR 识别")
        r = self._row(parent)
        ttk.Label(r, text="语言", style="Dim.TLabel").pack(side="left")
        ttk.Combobox(r, textvariable=self.var_lang, width=8, state="readonly",
                     values=("ch", "en", "japan", "korean")).pack(side="left",
                                                                    padx=(6, 14))
        ttk.Checkbutton(r, text="GPU 加速", variable=self.var_gpu,
                        style="TCheckbutton").pack(side="left")

        self._sub(parent, "最小置信度")
        r = self._row(parent)
        ttk.Scale(r, from_=0, to=1, variable=self.var_confidence, length=180,
                  command=self._on_conf_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_confidence).pack(side="left", padx=(6, 0))

        self._section(parent, "关键词匹配")
        self._sub(parent, "词库文件")
        r = self._row(parent)
        ttk.Entry(r, textvariable=self.var_banlist).pack(side="left",
                                                           fill="x", expand=True)
        ttk.Button(r, text="浏览…",
                   command=self._browse_banlist).pack(side="left", padx=(4, 0))
        ttk.Button(r, text="编辑",
                   command=self._edit_banlist).pack(side="left", padx=(4, 0))

        self._sub(parent, "匹配后显示时长（秒）")
        r = self._row(parent)
        ttk.Scale(r, from_=1, to=10, variable=self.var_duration, length=180,
                  command=self._on_dur_scale).pack(side="left")
        ttk.Entry(r, width=5,
                  textvariable=self.var_duration).pack(side="left", padx=(6, 0))

    # ----- 布局辅助 -----

    def _section(self, parent, text):
        ttk.Label(parent, text=text, style="Section.TLabel").pack(
            anchor="w", pady=(12, 4))

    def _sub(self, parent, text):
        ttk.Label(parent, text=text, style="Dim.TLabel").pack(
            anchor="w", pady=(4, 2))

    def _row(self, parent):
        r = ttk.Frame(parent, style="Card.TFrame")
        r.pack(fill="x", pady=2)
        return r

    # -----------------------------------------------------------------------
    # 滑块取整 / 值约束
    # -----------------------------------------------------------------------

    def _on_interval_scale(self, val):
        try:
            v = round(float(val) * 2) / 2
            self.var_interval.set(max(0.5, min(15.0, v)))
        except (ValueError, TypeError):
            pass

    def _on_conf_scale(self, val):
        try:
            v = round(float(val) / 0.05) * 0.05
            self.var_confidence.set(round(v, 2))
        except (ValueError, TypeError):
            pass

    def _on_dur_scale(self, val):
        try:
            v = round(float(val) * 2) / 2
            self.var_duration.set(max(1.0, min(10.0, v)))
        except (ValueError, TypeError):
            pass

    # -----------------------------------------------------------------------
    # ROI 预设
    # -----------------------------------------------------------------------

    def refresh_presets(self):
        presets = self.config.get("scan.roi_presets") or {}
        names = list(presets.keys())
        self._combo_preset["values"] = names
        if names and not self.var_roi_preset.get():
            self._combo_preset.current(0)

    def _on_preset_selected(self, event=None):
        name = self.var_roi_preset.get()
        presets = self.config.get("scan.roi_presets") or {}
        roi = presets.get(name)
        if roi:
            self.main_window.apply_roi_preset(name, tuple(roi))

    def _save_preset(self):
        self.main_window.save_current_roi_preset()

    # -----------------------------------------------------------------------
    # 词库浏览/编辑（委托给 MainWindow）
    # -----------------------------------------------------------------------

    def _browse_banlist(self):
        path = self.main_window.browse_banlist(self.var_banlist.get())
        if path:
            self.var_banlist.set(path)
            self._save_settings()

    def _edit_banlist(self):
        self.main_window.edit_banlist(self.var_banlist.get())

    # -----------------------------------------------------------------------
    # 配置读写
    # -----------------------------------------------------------------------

    def _load_settings(self):
        cfg = self.config
        self.var_enable_roi.set(cfg.get("scan.roi") is not None)
        self.var_remember_roi.set(True)
        self.var_interval.set(cfg.get("scan.interval_seconds"))
        self.var_lang.set(cfg.get("ocr.language"))
        self.var_gpu.set(cfg.get("gpu.enabled"))
        self.var_confidence.set(cfg.get("ocr.min_confidence"))
        self.var_banlist.set(cfg.get("files.banlist_file", DEFAULT_BANLIST_FILE))
        self.var_duration.set(cfg.get("matching.display_duration"))
        self.refresh_presets()

    def _save_settings(self):
        cfg = self.config
        cfg.set("scan.interval_seconds", self.var_interval.get())
        cfg.set("ocr.language", self.var_lang.get())
        cfg.set("gpu.enabled", self.var_gpu.get())
        cfg.set("ocr.min_confidence", round(self.var_confidence.get(), 2))
        cfg.set("files.banlist_file", self.var_banlist.get())
        cfg.set("matching.display_duration", self.var_duration.get())
        cfg.save()

    def save_settings(self):
        """对外公开（MainWindow 在 on_start 前调用）。"""
        self._save_settings()
