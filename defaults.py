"""
项目级默认值（唯一来源）。

设计：
- 这里的值是"默认值"——代码层面唯一来源。
- 用户在 GUI 里改动后，新值会被写入 config/config.yaml；加载时 yaml 优先、defaults 兜底。
- yaml 里没有的项 = 用户未改动 = 用 defaults。
- 新旧两版 Config 类都从这里取默认，保持实现逻辑统一。

新增配置项的步骤：
1. 在 DEFAULT_CONFIG 加默认值
2. 业务代码用 config.get('key.path') 读取（无需传 fallback）
3. GUI 改动会自动 config.set + config.save
"""

DEFAULT_BANLIST_FILE = 'C:/Users/Administrator/Desktop/banlist.txt'

DEFAULT_CONFIG = {
    'scan': {
        'interval_seconds': 5.0,
        'roi_padding': 10,
        'enable_roi': True,
        'remember_roi': True,
        'enable_diff_skip': True,
        'diff_threshold': 5.0,
        # 旧版 ROI 持久化
        'saved_roi': None,
        # 新版 ROI 持久化（与 saved_roi 含义重叠，新版用这套）
        'roi': None,
        'roi_presets': {},
    },
    'ocr': {
        'default_engine': 'paddle',
        # 旧版多语言列表
        'languages': ['ch', 'en'],
        # 新版单语言
        'language': 'ch',
        'min_confidence': 0.3,
        'save_processed_image': False,
        'enable_image_invert': False,
        'auto_detect_invert': False,
        'easyocr': {
            'canvas_size': 1920,
            'mag_ratio': 1.5,
            'dynamic_params': True,
        },
    },
    'gpu': {
        # 旧版三档（force_cpu > force_gpu > auto_detect）
        'auto_detect': False,
        'force_cpu': False,
        'force_gpu': True,
        # 新版单 bool
        'enabled': True,
    },
    'files': {
        'output_dir': 'output',
        'banlist_file': DEFAULT_BANLIST_FILE,
        'save_screenshot': False,
        'save_ocr_result': False,
        'folder_mode': 'minute',
        'max_folders': 10,
    },
    'cleanup': {
        'enabled': True,
        'max_age_hours': 1,
        'interval_minutes': 10,
        'scan_interval': 10,
    },
    'matching': {
        'enabled': True,
        'display_duration': 3.0,
        'position': 'center',
        'font_size': 18,
        'enable_sound': True,
    },
    'logging': {
        'level': 'INFO',
        'file': 'logs/app.log',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'max_bytes': 10485760,
        'backup_count': 5,
    },
    'performance': {
        'memory_monitor_interval_ms': 5000,
        'use_psutil': True,
        'max_log_queue_size': 1000,
        'log_queue_cleanup_threshold': 800,
        'explicit_image_cleanup': True,
    },
}
