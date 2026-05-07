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

行尾注释里若标注"旧版/新版"：
- 旧版 = old_version/，依赖 ScanService + 双 OCR 引擎 + 文件落盘
- 新版 = 当前主版本，pipeline 架构 + PaddleOCR 单引擎 + 零 I/O
- 不带标注的项是两版共用
"""

DEFAULT_BANLIST_FILE = 'C:/Users/Administrator/Desktop/banlist.txt'

DEFAULT_CONFIG = {
    'scan': {
        'interval_seconds': 5.0,         # 两次扫描之间的间隔（秒）
        'roi_padding': 10,                # ROI 周围外扩像素数（避免边缘文字被裁切）
        'enable_roi': True,               # True = 用 ROI 区域；False = 全屏扫描
        'remember_roi': True,             # 启动时是否复用上次保存的 ROI（False = 每次启动都重新框选）
        'enable_diff_skip': True,         # 帧差检测：与上次画面相似时跳过 OCR
        'diff_threshold': 5.0,            # MSE 阈值，小于此值视为画面无变化（缩成 160x120 灰度图比较）
        # ROI 坐标格式 [x1, y1, x2, y2]（屏幕绝对像素），None 表示未保存。
        # 默认值 [1170, 256, 1880, 843] 是项目当前的工作区域，开箱即用。
        'saved_roi': [1170, 256, 1880, 843],   # 旧版 ROI 持久化键
        'roi': [1170, 256, 1880, 843],         # 新版 ROI 持久化键（与 saved_roi 含义重叠，新版用这套）
        'roi_presets': {},                # ROI 预设字典 {名字: [x1,y1,x2,y2]}（保留扩展位）
    },
    'ocr': {
        'default_engine': 'paddle',       # 旧版引擎选择：'paddle' 或 'easy'；新版只有 paddle
        'languages': ['ch', 'en'],        # 旧版多语言列表（EasyOCR 支持并发多语言）
        'language': 'ch',                 # 新版单语言（PaddleOCR 一次只能加载一种语言模型）
        'min_confidence': 0.3,            # OCR 置信度门槛，低于此值的文本块丢弃
        'save_processed_image': False,    # 旧版：是否把预处理后的图也存盘（调试用）
        'enable_image_invert': False,     # 旧版：白底黑字关闭可提速 15-25%；黑底白字需开启
        'auto_detect_invert': False,      # 旧版：自动判断是否需要图像取反
        'easyocr': {                       # 旧版 EasyOCR 专用参数（新版无 EasyOCR）
            'canvas_size': 1920,           # EasyOCR 内部缩放最大尺寸
            'mag_ratio': 1.5,              # 检测放大倍数，越大越准但越慢
            'dynamic_params': True,        # 根据图片实际尺寸动态调整 canvas_size
        },
    },
    'gpu': {
        # 旧版三档优先级：force_cpu > force_gpu > auto_detect
        'auto_detect': False,             # 自动检测是否有可用 GPU
        'force_cpu': False,               # 强制 CPU（最高优先级，True 则忽略其它两项）
        'force_gpu': True,                # 强制 GPU（次优先级）
        'enabled': True,                  # 新版单 bool：True = GPU，False = CPU
    },
    'files': {
        'output_dir': 'output',                      # 截图/OCR 结果输出目录（相对项目根；新版默认零 I/O，不写）
        'banlist_file': DEFAULT_BANLIST_FILE,        # 关键词文件路径（相对路径会拼到项目根；可绝对）
        'save_screenshot': False,                    # 旧版：是否保存每次截图
        'save_ocr_result': False,                    # 旧版：是否保存 OCR 结果文本
        'folder_mode': 'minute',                     # 旧版输出子文件夹粒度：'minute' / 'hour' / 'day'
        'max_folders': 10,                           # 旧版最多保留多少个子文件夹（超过会触发清理）
    },
    'cleanup': {                            # 旧版才用；新版零 I/O 不需要清理
        'enabled': True,                    # 是否启用 output/ 自动清理
        'max_age_hours': 1,                 # 文件保留多少小时
        'interval_minutes': 10,             # 时间触发清理的间隔（分钟）
        'scan_interval': 10,                # 每隔多少次扫描触发一次清理
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
    'performance': {                            # 旧版才用；新版没有内存监控/日志队列治理逻辑
        'memory_monitor_interval_ms': 5000,     # 内存监控刷新间隔（毫秒）
        'use_psutil': True,                     # 优先用 psutil 取内存数据，缺失时回退 Win32 API
        'max_log_queue_size': 1000,             # GUI 日志队列最大长度
        'log_queue_cleanup_threshold': 800,     # 超过此长度时主动丢弃旧消息
        'explicit_image_cleanup': True,         # 显式 del + gc.collect 帮助回收 OCR 图像内存
    },
}
