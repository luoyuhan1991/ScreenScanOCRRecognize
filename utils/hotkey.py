import threading

from .logger import logger


class HotkeyManager:
    def __init__(self):
        self._hooks = []
        self._running = False

    def register(self, hotkey, callback, description=""):
        """注册热键 如 'ctrl+alt+1'"""
        try:
            import keyboard
            keyboard.add_hotkey(hotkey, callback)
            self._hooks.append(hotkey)
            logger.info(f"热键已注册: {hotkey} - {description}")
        except ImportError:
            logger.warning("keyboard 库未安装，热键不可用")
        except Exception:
            logger.exception(f"注册热键失败 {hotkey}")

    def unregister_all(self):
        try:
            import keyboard
            for h in self._hooks:
                try:
                    keyboard.remove_hotkey(h)
                except Exception:
                    pass
            self._hooks.clear()
        except Exception:
            pass
