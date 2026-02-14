"""
系统全局热键模块（Windows）
Ctrl+Alt+1：开始扫描（小键盘1 或 主键盘数字1）
Ctrl+Alt+2：停止扫描（小键盘2 或 主键盘数字2）
使用 keyboard 库（底层钩子，全局有效）。若无效可尝试以管理员身份运行程序。
"""

import logging
import platform
import subprocess
import sys

logger = logging.getLogger(__name__)

# 热键字符串（keyboard 库格式；小键盘1/2 与主键盘数字1/2 均可触发）
HOTKEY_START = "ctrl+alt+1"
HOTKEY_STOP = "ctrl+alt+2"


def _is_windows():
    return platform.system() == "Windows"


def _run_on_main(root, callback):
    """在 Tk 主线程执行 callback（keyboard 的回调在钩子线程中）"""
    try:
        root.after(0, callback)
    except Exception:
        pass


def register_scan_hotkeys(root, on_start, on_stop):
    """
    注册全局热键：Ctrl+Alt+1 开始，Ctrl+Alt+2 停止。
    使用 keyboard 库，需 pip install keyboard。
    """
    if not _is_windows():
        return None

    try:
        import keyboard
    except ImportError:
        # 使用当前解释器自动安装，确保装到运行本程序所在环境
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "keyboard", "-q"],
                timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
            )
            import keyboard
        except Exception as e:
            logger.warning(
                "未安装 keyboard 库，全局热键不可用。请在当前 Python 环境中执行: pip install keyboard（错误: %s）",
                e,
            )
            return None

    class _Manager:
        def __init__(self):
            self._root = root
            self._on_start = on_start
            self._on_stop = on_stop
            self._remove_start = None
            self._remove_stop = None

        def _safe_start(self):
            try:
                self._on_start()
            except Exception:
                pass

        def _safe_stop(self):
            try:
                self._on_stop()
            except Exception:
                pass

        def start(self):
            try:
                # add_hotkey 返回的移除函数，用于 stop 时注销
                self._remove_start = keyboard.add_hotkey(
                    HOTKEY_START,
                    lambda: _run_on_main(self._root, self._safe_start),
                    suppress=False,
                )
                self._remove_stop = keyboard.add_hotkey(
                    HOTKEY_STOP,
                    lambda: _run_on_main(self._root, self._safe_stop),
                    suppress=False,
                )
            except Exception as e:
                logger.warning("热键注册失败: %s（若需管理员权限请以管理员运行）", e)

        def stop(self):
            try:
                if self._remove_start is not None:
                    self._remove_start()
                    self._remove_start = None
                if self._remove_stop is not None:
                    self._remove_stop()
                    self._remove_stop = None
            except Exception:
                pass

    manager = _Manager()
    manager.start()
    return manager
