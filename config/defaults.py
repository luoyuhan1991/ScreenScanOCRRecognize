"""
项目级默认值（唯一来源）。

- 这里是代码层面唯一的默认来源；DEFAULT_CONFIG 缺的键，运行时 config.get() 也拿不到。
- 启动时 Config.load() 把 yaml 深合并到 defaults 之上：yaml 优先，defaults 兜底。
- Config.save() 写全量字典回 yaml（含默认值），所以 yaml 文件会被覆盖、手写注释不保留。

新增配置项：在 DEFAULT_CONFIG 加默认值；业务代码用 config.get('key.path')；GUI 改动走 config.set + config.save。
"""

import os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
DEFAULT_BANLIST_FILE = _os.path.join(_PROJECT_ROOT, 'config', 'banlist.example.txt')

APP_VERSION = '1.0.0'

DEFAULT_CONFIG = {
    'scan': {
        'interval_seconds': 5.0,         # 两次扫描之间的间隔（秒）
        'roi_padding': 10,                # ROI 周围外扩像素数（避免边缘文字被裁切）
        'enable_roi': True,               # True = 用 ROI 区域；False = 全屏扫描
        'diff_threshold': 5.0,            # MSE 阈值，小于此值视为画面无变化（缩成 160x120 灰度图比较）
        # 当前生效的 ROI 坐标 [x1, y1, x2, y2]，屏幕绝对像素；None = 未保存，首启弹 picker。
        # 与 last_roi_choice='__reselect__' 配合：两者必须保持一致意图（见 §十一.5）。
        # 开关由 enable_roi 单独承担，避免「None=禁用 / coords=启用」二义性。
        'roi_rect': None,
        # ROI 预设字典 {名字: [x1,y1,x2,y2]}。完全由用户管理：GUI「保存当前」追加，
        # 「删除」按钮移除。default 不预置任何项 —— 否则用户删除后下次启动 deep_merge
        # 会把 default 里的项"复活"。
        'roi_presets': {},
        # 记住 ROI 下拉上次选了哪一项；启动时下拉自动定位。
        # 取值：'__reselect__'（首项「重新框选...」）或某个预设名。
        'last_roi_choice': '__reselect__',
    },
    'ocr': {
        'language': 'ch',                 # PaddleOCR 一次只能加载一种语言模型
        'min_confidence': 0.3,            # OCR 置信度门槛，低于此值的文本块丢弃
        'enable_image_invert': False,     # 白底黑字关闭可提速 15-25%；黑底白字需开启
    },
    'gpu': {
        'enabled': True,                  # True = GPU，False = CPU
    },
    'files': {
        'banlist_file': DEFAULT_BANLIST_FILE,        # 关键词文件路径（相对路径会拼到项目根；可绝对）
    },
    'matching': {
        'display_duration': 3.0,            # 浮窗每次显示时长（秒），到时自动 withdraw
        'position': 'center',               # 浮窗位置：'center' / 'top' / 'bottom' / 'top-left' 等
        'font_size': 18,                    # 浮窗字号
        'enable_sound': True,               # 命中新关键词时播放 C 大三和弦提示音
    },
    'logging': {
        'level': 'INFO',                                            # DEBUG / INFO / WARNING / ERROR
        'file': 'logs/app.log',                                     # 日志文件相对路径
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'max_bytes': 10485760,                                      # 单个日志文件最大 10 MB（旋转触发阈值）
        'backup_count': 5,                                          # 旋转保留 5 份历史日志
    },
    'app': {                              # PySide6 GUI 通用设置
        'minimize_to_tray': True,         # 关闭主窗口时缩进系统托盘
        'startup_mode': 'paused',         # 'paused' = 启动后停在待机；'auto' = 等 OCR 加载完自动开扫
    },
}
