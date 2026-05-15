import logging
import os
from logging.handlers import RotatingFileHandler


def _ensure_root_console_handler(level=logging.INFO):
    """在 root 装一个 console StreamHandler（幂等）。
    旧版 screen_scan 命名 logger 自己装 StreamHandler 又 propagate=True，
    会让 root 上的 LogBridge 再 format 一次同样消息（双重格式化）。
    现在统一让 root 持有 console handler，screen_scan 不再持。"""
    root = logging.getLogger()
    has_stream = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
        for h in root.handlers
    )
    if has_stream:
        return
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    formatter.default_msec_format = '%s.%03d'
    handler.setFormatter(formatter)
    handler.setLevel(level)
    root.addHandler(handler)
    if root.level > level or root.level == logging.WARNING:  # WARNING 是 root 默认
        root.setLevel(level)


_ensure_root_console_handler()

# 业务代码 import 这个别名；它仅 propagate 到 root，handler 全在 root 上。
logger = logging.getLogger('screen_scan')
logger.propagate = True


def configure_from_config(cfg):
    """根据配置调整 root 级别 + 装 RotatingFileHandler。"""
    level_str = cfg.get('logging.level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers:
        h.setLevel(level)

    has_file = any(isinstance(h, RotatingFileHandler) for h in root.handlers)
    if has_file:
        return

    file_path = cfg.get('logging.file', 'logs/app.log')
    max_bytes = int(cfg.get('logging.max_bytes', 10 * 1024 * 1024))
    backup_count = int(cfg.get('logging.backup_count', 5))
    fmt = cfg.get(
        'logging.format',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    log_dir = os.path.dirname(os.path.abspath(file_path))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    fh = RotatingFileHandler(
        file_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
    )
    formatter = logging.Formatter(fmt)
    formatter.default_msec_format = '%s.%03d'
    fh.setFormatter(formatter)
    fh.setLevel(level)
    root.addHandler(fh)
