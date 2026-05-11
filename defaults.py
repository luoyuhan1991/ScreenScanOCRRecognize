"""
项目级默认值（唯一来源）。

- 这里是代码层面唯一的默认来源；DEFAULT_CONFIG 缺的键，运行时 config.get() 也拿不到。
- 启动时 Config.load() 把 yaml 深合并到 defaults 之上：yaml 优先，defaults 兜底。
- Config.save() 写全量字典回 yaml（含默认值），所以 yaml 文件会被覆盖、手写注释不保留。

新增配置项：在 DEFAULT_CONFIG 加默认值；业务代码用 config.get('key.path')；GUI 改动走 config.set + config.save。
"""

DEFAULT_BANLIST_FILE = 'C:/Users/Administrator/Desktop/banlist.txt'

APP_VERSION = '1.0.0'

DEFAULT_CONFIG = {
    'scan': {
        'interval_seconds': 5.0,         # 两次扫描之间的间隔（秒）
        'roi_padding': 10,                # ROI 周围外扩像素数（避免边缘文字被裁切）
        'enable_roi': True,               # True = 用 ROI 区域；False = 全屏扫描
        'remember_roi': True,             # 启动时是否复用上次保存的 ROI（False = 每次启动都重新框选）
        'enable_diff_skip': True,         # 帧差检测：与上次画面相似时跳过 OCR
        'diff_threshold': 5.0,            # MSE 阈值，小于此值视为画面无变化（缩成 160x120 灰度图比较）
        # 当前生效的 ROI 坐标 [x1, y1, x2, y2]，屏幕绝对像素；None = 未保存。
        # 默认 [1170, 256, 1880, 843] 是项目工作区域，开箱即用。
        # 开关由 enable_roi 单独承担，避免「None=禁用 / coords=启用」二义性。
        'roi_rect': [1170, 256, 1880, 843],
        # ROI 预设字典 {名字: [x1,y1,x2,y2]}。'4+2' 是内置预设（与默认 roi_rect 同坐标，开箱即用）。
        # GUI「保存当前」会向此 dict 追加用户自定义预设。
        'roi_presets': {'4+2': [1170, 256, 1880, 843]},
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
        'enabled': True,                    # 是否启用关键词匹配（False 时只 OCR 不弹浮窗）
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
