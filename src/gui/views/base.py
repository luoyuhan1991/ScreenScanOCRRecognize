"""
所有视图的基类。

子类构造接收 (parent, main_window)；main_window 用来读 config / 触发全局动作。
mount() / unmount() 是空钩子，需要时重写。
"""

from tkinter import ttk


class BaseView(ttk.Frame):
    """所有视图共享的基类。"""

    VIEW_KEY = ""    # 子类必须覆盖：'scan' / 'settings' / 'hotkey' / 'about'

    def __init__(self, parent, main_window):
        super().__init__(parent, style="Content.TFrame")
        self.main_window = main_window
        self.config = main_window.config_obj  # type: ignore[has-type]
        self._build()

    # ----- 子类 hook -----

    def _build(self):
        """子类在这里构造 widget。"""
        pass

    def mount(self):
        """View 被切到前台时调用。可用于刷新依赖外部状态的 widget。"""
        pass

    def unmount(self):
        """View 被切走时调用。可用于停定时器或保存状态。"""
        pass
