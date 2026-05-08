"""
主窗口：组装 sidebar + content + statusbar，管理视图切换与全局动作。

本文件目标超过 600 行，但都是协调/分发逻辑，没有可拆的子单元——
拆出去会让"读完一处看完整流程"的能力变差。
"""

import logging
import os
import queue
import sys
import threading
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

# 项目根入 sys.path（让 from defaults / shared 都能 import）
_THIS = os.path.abspath(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time

from src.config.config import config, PROJECT_ROOT
from src.utils.logger import logger, configure_from_config
from src.gui import theme
from src.pipeline.pipeline import ScanPipeline
from src.utils.hotkey import HotkeyManager
from shared.overlay import Overlay
from src.gui.widgets.roi_overlay import select_roi_interactive
from src.gui.widgets.roi_border import RoiBorder
from src.gui.widgets.tray import setup_tray
from src.gui.sidebar import Sidebar
from src.gui.statusbar import StatusBar, get_memory_mb
from src.gui.widgets.log_panel import LogPanel
from src.gui.widgets.match_records import MatchRecords
from src.gui.views.scan_view import ScanView
from src.gui.views.settings_view import SettingsView
from src.gui.views.hotkey_view import HotkeyView
from src.gui.views.about_view import AboutView


class MainWindow:
    """协调者：持有所有跨视图状态、调度扫描线程、切视图。"""

    def __init__(self, root):
        self.root = root
        self.root.title("屏幕扫描OCR识别系统")
        self.root.geometry("1100x720")

        # ---- 配置 ----
        config.load()
        configure_from_config(config)
        self.config_obj = config   # 让 BaseView 通过 main_window.config_obj 访问

        # ---- 主题 ----
        theme.apply(self.root)

        # ---- 跨视图常驻状态 ----
        self.log_queue = queue.Queue(maxsize=1000)
        self.match_records = deque(maxlen=10)

        # ---- 扫描相关 ----
        self.is_running = False
        self.scan_thread = None
        self.stop_event = threading.Event()
        self.roi = None
        self.pipeline = ScanPipeline()
        self.overlay = Overlay(parent_root=self.root, config=config, logger=logger)
        self.roi_border = RoiBorder(self.root,
                                     padding=config.get("scan.roi_padding"))
        self.hotkey_mgr = HotkeyManager()
        self.tray = None

        # ---- 构建 UI ----
        self._build_layout()
        self._build_views()
        self._switch_view("scan")

        # ---- 关闭事件（Task 16 加 watchdog 清理） ----
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- 内存定时刷新 ----
        self._schedule_memory_update()

        # ---- 日志队列消费（Task 16 启动） ----
        self._setup_gui_logger()
        self._drain_log_queue()

        # ---- 托盘 ----
        self.tray = setup_tray(
            self.root,
            on_show=self._tray_show,
            on_quit=self._tray_quit,
            tooltip="屏幕扫描OCR识别",
        )
        if self.tray:
            self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
            self.append_log("托盘图标已启用：关闭窗口将缩到托盘，右键托盘可退出", "INFO")
        else:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- 热键 ----
        self.root.after_idle(self._register_hotkeys)

    # =======================================================================
    # 布局
    # =======================================================================

    def _build_layout(self):
        # 三段式：sidebar | content | (statusbar 在 root 底部)
        self.statusbar = StatusBar(
            self.root,
            on_start=self.on_start,
            on_stop=self.on_stop,
            on_toggle_sound=self._on_toggle_sound,
            on_reset=self._reset_config,
        )
        self.statusbar.pack(side="bottom", fill="x")
        self.statusbar.set_sound(config.get("matching.enable_sound"))

        body = ttk.Frame(self.root, style="TFrame")
        body.pack(side="top", fill="both", expand=True)

        self.sidebar = Sidebar(body, on_select=self._switch_view)
        self.sidebar.pack(side="left", fill="y")

        self.content = ttk.Frame(body, style="Content.TFrame")
        self.content.pack(side="left", fill="both", expand=True)

        # 跨视图常驻 widget
        self.log_panel = LogPanel(self.content, on_clear=lambda: None)
        self.match_panel = MatchRecords(self.content, on_clear=self._clear_match_records)

    def _build_views(self):
        self._views = {
            "scan":     ScanView(self.content, self),
            "settings": SettingsView(self.content, self),
            "hotkey":   HotkeyView(self.content, self),
            "about":    AboutView(self.content, self),
        }
        # 把常驻面板挂给 ScanView（仅 ScanView 显示它们）
        self._views["scan"].attach_panels(self.log_panel, self.match_panel)
        self._current_view = None

    # =======================================================================
    # 视图切换
    # =======================================================================

    def _switch_view(self, name):
        if name not in self._views:
            return
        if self._current_view is not None:
            self._current_view.unmount()
            self._current_view.pack_forget()
        view = self._views[name]
        view.pack(fill="both", expand=True)
        view.mount()
        self.sidebar.set_active(name)
        self._current_view = view

        # 切回扫描视图时把累积的匹配记录刷给面板
        if name == "scan":
            self.match_panel.refresh(self.match_records)

    # =======================================================================
    # 占位回调（Task 16 实现真逻辑）
    # =======================================================================

    def on_start(self):
        if self.is_running:
            return

        # 把扫描视图当前的设置存到 config，再触发 pipeline.init
        scan_view = self._views["scan"]
        scan_view.save_settings()
        self.overlay.clear_session()
        self.match_records.clear()
        self.match_panel.refresh(self.match_records)

        self.statusbar.set_busy(True)
        self.append_log("正在初始化 OCR 引擎...", "INFO")

        threading.Thread(target=self._init_and_start, daemon=True).start()

    def _init_and_start(self):
        try:
            self.pipeline.init()
            self.root.after(0, self._after_init_ok)
        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda: self._after_init_fail(msg))

    def _after_init_ok(self):
        self.append_log("OCR 初始化完成", "INFO")

        # ROI
        scan_view = self._views["scan"]
        if scan_view.var_enable_roi.get():
            saved = config.get("scan.roi")
            if scan_view.var_remember_roi.get() and saved:
                self.roi = tuple(saved)
                self.append_log(f"使用已保存 ROI: {self.roi}", "INFO")
                self._start_scanning()
                return
            self.root.iconify()
            self.root.after(300, self._do_roi_select)
            return

        self.roi = None
        self._start_scanning()

    def _do_roi_select(self):
        self.roi = select_roi_interactive(parent=self.root)
        self.root.deiconify()
        if self.roi:
            self.append_log(f"ROI 已选择: {self.roi}", "INFO")
            config.set("scan.roi", list(self.roi))
            config.save()
        else:
            self.append_log("ROI 选择取消，使用全屏", "WARNING")
        self._start_scanning()

    def _start_scanning(self):
        self.pipeline.set_roi(self.roi)
        self.overlay.setup()

        self.is_running = True
        self.stop_event.clear()
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()

        self.statusbar.set_running(True)
        self.append_log("扫描已启动", "INFO")
        self.roi_border.show(self.roi)

    def _after_init_fail(self, msg):
        self.append_log(f"初始化失败: {msg}", "ERROR")
        messagebox.showerror("错误", f"OCR 初始化失败:\n{msg}")
        self.statusbar.set_running(False)

    def on_stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.stop_event.set()
        self.roi_border.hide()
        self.overlay.hide()
        self.statusbar.set_running(False)
        self.append_log("扫描已停止", "INFO")

    # =======================================================================
    # 扫描循环
    # =======================================================================

    def _scan_loop(self):
        try:
            scan_view = self._views["scan"]
            while not self.stop_event.is_set():
                interval = scan_view.var_interval.get()
                start = time.time()

                result = self.pipeline.scan_once()
                self.root.after(0, self._on_scan_result, result)

                elapsed = time.time() - start
                wait = max(0, interval - elapsed)
                waited = 0.0
                while waited < wait and not self.stop_event.is_set():
                    time.sleep(0.3)
                    waited += 0.3
        except Exception as e:
            self.append_log(f"扫描异常: {e}", "ERROR")
        finally:
            self.is_running = False
            self.root.after(0, self._on_scan_thread_exit)

    def _on_scan_result(self, result):
        # 1. 日志一行总结
        if result.skipped:
            status_txt = "跳过(无变化)"
        else:
            status_txt = f"{len(result.ocr_results)}行"
        self.append_log(
            f"OCR: {status_txt}, 匹配: {len(result.matches)}, "
            f"耗时: {result.duration:.3f}s", "INFO"
        )

        # 2. 命中的关键词 + 写入 match_records deque
        for m in result.matches:
            self.append_log(f"  >>> {m['keyword']} | {m['hint']}", "WARNING")
            self.match_records.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "keyword": m["keyword"],
                "ocr_text": m.get("ocr_text", ""),
            })

        # 3. 当前在扫描视图就刷新匹配记录面板
        if self._current_view is self._views["scan"] and result.matches:
            self.match_panel.refresh(self.match_records)

        # 4. Overlay 浮窗（每次扫描都刷，包括 skipped 与无匹配）
        self.overlay.update(result.ocr_results, result.matches)

    def _on_scan_thread_exit(self):
        self.roi_border.hide()
        self.overlay.hide()
        self.statusbar.set_running(False)

    # =======================================================================
    # 托盘 / 关闭
    # =======================================================================

    def _minimize_to_tray(self):
        self.root.withdraw()

    def _tray_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _tray_quit(self):
        self._on_close()

    # =======================================================================
    # 热键
    # =======================================================================

    def _register_hotkeys(self):
        try:
            self.hotkey_mgr.register("ctrl+alt+1",
                                       lambda: self.root.after(0, self.on_start),
                                       "开始扫描")
            self.hotkey_mgr.register("ctrl+alt+2",
                                       lambda: self.root.after(0, self.on_stop),
                                       "停止扫描")
            self.append_log("热键: Ctrl+Alt+1 开始, Ctrl+Alt+2 停止", "INFO")
        except Exception as e:
            self.append_log(f"热键注册失败: {e}", "WARNING")

    def _on_toggle_sound(self, enabled):
        config.set("matching.enable_sound", enabled)
        config.save()
        self.append_log(f"声音提醒：{'开' if enabled else '关'}", "INFO")

    def _reset_config(self):
        if messagebox.askyesno("确认", "重置所有配置为默认值?"):
            config.load()
            for v in self._views.values():
                if hasattr(v, "_load_settings"):
                    v._load_settings()
                if hasattr(v, "reload_from_config"):
                    v.reload_from_config()
            self.statusbar.set_sound(config.get("matching.enable_sound"))
            self.append_log("配置已重置", "INFO")

    def on_settings_changed(self):
        """SettingsView 改了某些项后通知（如音效开关）。"""
        self.statusbar.set_sound(config.get("matching.enable_sound"))

    # =======================================================================
    # ScanView 委托：ROI 预设、词库浏览编辑
    # =======================================================================

    def apply_roi_preset(self, name, roi):
        self.roi = roi
        config.set("scan.roi", list(roi))
        config.save()
        self.append_log(f"已应用 ROI 预设 '{name}': {roi}", "INFO")

    def save_current_roi_preset(self):
        if self.roi is None:
            messagebox.showwarning("提示", "当前没有可保存的 ROI 区域")
            return
        name = simpledialog.askstring("保存预设", "请输入预设名称:", parent=self.root)
        if not name:
            return
        presets = config.get("scan.roi_presets") or {}
        presets[name] = list(self.roi)
        config.set("scan.roi_presets", presets)
        config.save()
        self._views["scan"].refresh_presets()
        self.append_log(f"ROI 预设 '{name}' 已保存: {list(self.roi)}", "INFO")

    def browse_banlist(self, current):
        init_dir = os.path.dirname(current) if current else "."
        return filedialog.askopenfilename(
            title="选择关键词文件", initialdir=init_dir,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

    def edit_banlist(self, path):
        if not path:
            messagebox.showwarning("提示", "请先选择关键词文件")
            return

        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)

        if not os.path.exists(path):
            if not messagebox.askyesno("确认", f"文件不存在:\n{path}\n是否创建?"):
                return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("")

        win = tk.Toplevel(self.root)
        win.title(f"编辑关键词 - {os.path.basename(path)}")
        win.geometry("600x400")
        win.attributes("-topmost", True)

        txt = scrolledtext.ScrolledText(win, font=("Consolas", 11), wrap=tk.WORD)
        txt.pack(fill="both", expand=True, padx=5, pady=5)

        with open(path, "r", encoding="utf-8") as f:
            txt.insert("1.0", f.read())

        def save_and_close():
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt.get("1.0", tk.END).rstrip("\n") + "\n")
            self.append_log(f"关键词文件已保存: {path}", "INFO")
            win.destroy()

        btn_fr = ttk.Frame(win)
        btn_fr.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_fr, text="保存并关闭",
                   command=save_and_close).pack(side="right", padx=5)
        ttk.Button(btn_fr, text="取消",
                   command=win.destroy).pack(side="right", padx=5)

    def _clear_match_records(self):
        self.match_records.clear()
        self.append_log("匹配记录已清除", "INFO")

    # =======================================================================
    # 日志（队列 + 主线程消费）
    # =======================================================================

    def append_log(self, message, level="INFO"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self.log_queue.put_nowait((f"{ts} - {message}\n", level))
        except queue.Full:
            pass

    def _setup_gui_logger(self):
        class _QueueHandler(logging.Handler):
            def __init__(self, q):
                super().__init__()
                self._q = q

            def emit(self, record):
                try:
                    msg = self.format(record) + "\n"
                    self._q.put_nowait((msg, record.levelname))
                except Exception:
                    pass

        handler = _QueueHandler(self.log_queue)
        handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s - %(message)s")
        fmt.default_msec_format = "%s.%03d"
        handler.setFormatter(fmt)

        from src.utils.logger import logger as app_logger
        app_logger.addHandler(handler)

    def _drain_log_queue(self):
        count = 0
        while count < 15:
            try:
                msg, lvl = self.log_queue.get_nowait()
                self.log_panel.append(msg.rstrip("\n"), lvl)
                count += 1
            except queue.Empty:
                break
        self.root.after(100, self._drain_log_queue)

    # =======================================================================
    # 内存监控
    # =======================================================================

    def _schedule_memory_update(self):
        mb = get_memory_mb()
        self.statusbar.set_memory(mb)
        self.root.after(5000, self._schedule_memory_update)

    # =======================================================================
    # 关闭（Task 16 加 watchdog） ====
    # =======================================================================

    def _on_close(self):
        """看门狗式清理：3 秒后强杀，保证不卡死。"""
        watchdog = threading.Timer(3.0, lambda: os._exit(0))
        watchdog.daemon = True
        watchdog.start()

        try:
            self.root.withdraw()
        except Exception:
            pass

        for cleanup in (
            lambda: self.roi_border.hide(),
            lambda: self.overlay.destroy(),
            lambda: self.tray and self.tray.stop(),
            lambda: self.hotkey_mgr.unregister_all(),
            lambda: self.pipeline.release(),
        ):
            try:
                cleanup()
            except Exception:
                pass

        os._exit(0)


# ---------------------------------------------------------------------------
# 演示（独立跑 main_window 看视图切换）
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    win = MainWindow(root)
    root.mainloop()
