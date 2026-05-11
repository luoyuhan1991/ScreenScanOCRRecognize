import logging
import os


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
    """根据配置调整日志级别"""
    level_str = cfg.get('logging.level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
