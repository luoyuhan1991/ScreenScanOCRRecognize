import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name='screen_scan', level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        # 把默认的逗号毫秒分隔符（"...27,582"）改成点（"...27.582"），与 GUI 内 _append_log 对齐
        formatter.default_msec_format = '%s.%03d'
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        # propagate=True：让消息向上传到 root logger，新版 PySide6 GUI 在 root
        # 上挂 LogBridge 收日志（所以 pipeline/matcher/hotkey 的输出能进 GUI 日志区）。
        # root 没有 console StreamHandler，不会和这里的 console handler 重复。
        logger.propagate = True
    return logger


logger = setup_logger()


def configure_from_config(cfg):
    """根据配置调整日志级别 + 装 RotatingFileHandler 到 root（让所有模块日志都进文件）。"""
    level_str = cfg.get('logging.level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)

    # 1. 调整 screen_scan logger 和 root 的级别
    logging.getLogger().setLevel(level)
    logger.setLevel(level)
    for h in logger.handlers:
        h.setLevel(level)

    # 2. 装 RotatingFileHandler 到 root，避免重复装
    root = logging.getLogger()
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
