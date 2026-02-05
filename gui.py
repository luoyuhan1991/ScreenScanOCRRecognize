"""
ScreenScanOCRRecognize - GUI主程序
提供图形用户界面，支持参数配置、状态监控和日志显示
"""

import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from mem_monitor import get_working_set_mb
except Exception:
    get_working_set_mb = None

# Windows任务栏API支持
try:
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        
        # Windows任务栏API常量
        TBPF_NOPROGRESS = 0
        TBPF_INDETERMINATE = 0x1
        TBPF_NORMAL = 0x2
        TBPF_ERROR = 0x4
        TBPF_PAUSED = 0x8
        
        # 尝试加载Windows任务栏API
        try:
            _comdlg32 = ctypes.windll.comdlg32
            _ole32 = ctypes.windll.ole32
            _shell32 = ctypes.windll.shell32
            
            # 定义ITaskbarList3接口
            class ITaskbarList3(ctypes.c_void_p):
                pass
            
            WINDOWS_TASKBAR_AVAILABLE = True
        except:
            WINDOWS_TASKBAR_AVAILABLE = False
    else:
        WINDOWS_TASKBAR_AVAILABLE = False
except:
    WINDOWS_TASKBAR_AVAILABLE = False

# 导入项目模块
from src.config.config import config
from src.config.config_editor import ConfigEditor
from src.config.gui_state import GUIStateManager
from src.gui.gui_logger import GUILoggerHandler
from src.services.scan_service import ScanService
from src.utils.scan_screen import select_roi_interactive
from src.utils.text_matcher import display_matches


class MainGUI:
    """主GUI界面"""
    
    def __init__(self, root):
        """初始化界面"""
        self.root = root
        self.root.title("屏幕扫描OCR识别系统")
        
        # 扫描服务
        self.scan_service = ScanService()
        
        # GUI状态管理器
        self.state_manager = GUIStateManager()
        
        # 加载窗口状态
        geometry = self.state_manager.get_window_geometry()
        if geometry:
            self.root.geometry(geometry)
        else:
            self.root.geometry("800x700")
        
        # 状态变量
        self.is_running = False
        self.scan_thread = None
        self.stop_event = threading.Event()
        # 限制日志队列大小，避免高频日志导致内存增长
        self.log_queue = queue.Queue(maxsize=2000)
        self.scan_count = 0
        self.last_scan_time = None
        self.memory_label = None
        self._memory_interval_ms = 2000
        self._memory_pid = os.getpid()
        
        # OCR相关
        self.roi = None
        
        # 创建界面
        self.create_widgets()
        
        # 加载设置
        self.load_settings()
        
        # 设置GUI日志处理器
        self.setup_gui_logger()
        
        # 启动日志处理
        self.process_log_queue()
        
        # 绑定窗口事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.root.bind('<Configure>', self.on_window_configure)
        
        # 初始化窗口标题（显示状态）
        self.update_window_title("已停止")
        
        # 启动内存监控显示
        self._schedule_memory_update()
    
    def create_widgets(self):
        """创建所有控件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.create_status_bar(main_frame)
        
        # 扫描配置
        self.create_scan_config_widgets(main_frame)
        
        # OCR配置
        self.create_ocr_config_widgets(main_frame)
        
        # 文字匹配配置
        self.create_matching_config_widgets(main_frame)
        
        # 日志显示
        self.create_log_widgets(main_frame)
        
        # 按钮区域
        self.create_button_widgets(main_frame)
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.LabelFrame(parent, text="状态", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 状态标签
        self.status_label = ttk.Label(status_frame, text="状态: ● 已停止", font=("Microsoft YaHei", 10))
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # 扫描次数
        self.scan_count_label = ttk.Label(status_frame, text="扫描次数: 0", font=("Microsoft YaHei", 10))
        self.scan_count_label.pack(side=tk.LEFT, padx=5)
        
        # 最后扫描时间
        self.last_scan_label = ttk.Label(status_frame, text="最后扫描: 无", font=("Microsoft YaHei", 10))
        self.last_scan_label.pack(side=tk.LEFT, padx=5)
        
        # 内存占用
        self.memory_label = ttk.Label(status_frame, text="内存: -- MB", font=("Microsoft YaHei", 10))
        self.memory_label.pack(side=tk.LEFT, padx=5)
    
    def create_scan_config_widgets(self, parent):
        """创建扫描配置控件"""
        frame = ttk.LabelFrame(parent, text="扫描配置", padding="5")
        frame.pack(fill=tk.X, pady=(0, 5))
        
        # 第一行：ROI和GPU选项
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=2)
        
        self.enable_roi_var = tk.BooleanVar()
        roi_check = ttk.Checkbutton(row1, text="启用ROI区域选择", variable=self.enable_roi_var)
        roi_check.pack(side=tk.LEFT, padx=5)
        
        self.remember_roi_var = tk.BooleanVar()
        remember_roi_check = ttk.Checkbutton(row1, text="记住ROI区域", variable=self.remember_roi_var)
        remember_roi_check.pack(side=tk.LEFT, padx=5)
        
        self.enable_gpu_var = tk.BooleanVar()
        gpu_check = ttk.Checkbutton(row1, text="启用GPU加速", variable=self.enable_gpu_var)
        gpu_check.pack(side=tk.LEFT, padx=5)
        
        # 第二行：扫描间隔
        interval_frame = ttk.Frame(frame)
        interval_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(interval_frame, text="扫描间隔:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.scan_interval_var = tk.DoubleVar()
        self.scan_interval_scale = ttk.Scale(interval_frame, from_=1, to=15, orient=tk.HORIZONTAL, variable=self.scan_interval_var, length=200, command=self.on_interval_scale_change)
        self.scan_interval_scale.pack(side=tk.LEFT, padx=5)
        
        self.scan_interval_entry = ttk.Entry(interval_frame, width=5, textvariable=self.scan_interval_var)
        self.scan_interval_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(interval_frame, text="秒").pack(side=tk.LEFT, padx=(0, 5))
        
        # 绑定滑动条和输入框
        self.scan_interval_var.trace('w', self.on_interval_change)
        self.scan_interval_scale.configure(command=self.on_interval_scale_change)
    
    def create_ocr_config_widgets(self, parent):
        """创建OCR配置控件"""
        frame = ttk.LabelFrame(parent, text="OCR配置", padding="5")
        frame.pack(fill=tk.X, pady=(0, 5))
        
        # 第一行：OCR引擎和最小置信度
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="OCR引擎:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.ocr_engine_var = tk.StringVar()
        paddle_radio = ttk.Radiobutton(row1, text="PaddleOCR", variable=self.ocr_engine_var, value="paddle")
        paddle_radio.pack(side=tk.LEFT, padx=5)
        
        easy_radio = ttk.Radiobutton(row1, text="EasyOCR", variable=self.ocr_engine_var, value="easy")
        easy_radio.pack(side=tk.LEFT, padx=5)
        
        # 添加分隔
        ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Label(row1, text="最小置信度:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.min_confidence_var = tk.DoubleVar()
        self.min_confidence_scale = ttk.Scale(
            row1,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.min_confidence_var,
            length=150
        )
        self.min_confidence_scale.pack(side=tk.LEFT, padx=5)
        
        self.min_confidence_entry = ttk.Entry(row1, width=5, textvariable=self.min_confidence_var)
        self.min_confidence_entry.pack(side=tk.LEFT, padx=5)
        
        # 绑定滑动条和输入框
        self.min_confidence_var.trace('w', self.on_confidence_change)
        self.min_confidence_scale.configure(command=self.on_confidence_scale_change)
        
        # 第二行：保存文件选项
        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=2)
        
        self.save_files_var = tk.BooleanVar()
        save_files_check = ttk.Checkbutton(row2, text="保存截图和识别结果", variable=self.save_files_var)
        save_files_check.pack(side=tk.LEFT, padx=5)
    
    def create_matching_config_widgets(self, parent):
        """创建文字匹配控件"""
        frame = ttk.LabelFrame(parent, text="文字匹配", padding="5")
        frame.pack(fill=tk.X, pady=(0, 5))
        
        # 第一行：启用文字匹配和关键词文件
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=2)
        
        self.enable_matching_var = tk.BooleanVar()
        matching_check = ttk.Checkbutton(row1, text="启用文字匹配", variable=self.enable_matching_var)
        matching_check.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="关键词文件:").pack(side=tk.LEFT, padx=(10, 5))
        
        self.banlist_path_var = tk.StringVar()
        banlist_entry = ttk.Entry(row1, textvariable=self.banlist_path_var, width=30)
        banlist_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(row1, text="浏览...", command=self.on_browse_banlist)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        edit_btn = ttk.Button(row1, text="编辑", command=self.on_edit_banlist)
        edit_btn.pack(side=tk.LEFT, padx=5)
        
        # 第二行：显示时长、字体大小和显示位置
        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="显示时长:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.display_duration_var = tk.DoubleVar()
        self.display_duration_scale = ttk.Scale(
            row2,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            variable=self.display_duration_var,
            length=150,
            command=self.on_duration_scale_change
        )
        self.display_duration_scale.pack(side=tk.LEFT, padx=5)
        
        self.display_duration_entry = ttk.Entry(row2, width=5, textvariable=self.display_duration_var)
        self.display_duration_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="秒").pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="字体大小:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.display_font_size_var = tk.IntVar(value=30)
        self.display_font_size_scale = ttk.Scale(
            row2,
            from_=12,
            to=60,
            orient=tk.HORIZONTAL,
            variable=self.display_font_size_var,
            length=150,
            command=self.on_font_size_scale_change
        )
        self.display_font_size_scale.pack(side=tk.LEFT, padx=5)
        
        self.display_font_size_entry = ttk.Entry(row2, width=5, textvariable=self.display_font_size_var)
        self.display_font_size_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="像素").pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(row2, text="显示位置:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.display_position_var = tk.StringVar()
        position_combo = ttk.Combobox(row2, textvariable=self.display_position_var, width=12, state="readonly")
        position_combo['values'] = ('居中', '顶部', '底部')
        position_combo.pack(side=tk.LEFT, padx=5)
    
    def create_log_widgets(self, parent):
        """创建日志显示控件"""
        frame = ttk.LabelFrame(parent, text="运行日志", padding="5")
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 日志文本框（使用ScrolledText，减少高度）
        self.log_text = scrolledtext.ScrolledText(
            frame,
            height=6,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志文本颜色标签
        self.log_text.tag_config("INFO", foreground="#4ec9b0")
        self.log_text.tag_config("WARNING", foreground="#dcdcaa")
        self.log_text.tag_config("ERROR", foreground="#f48771")
        self.log_text.tag_config("DEBUG", foreground="#569cd6")
        
        # 创建悬浮的清空日志按钮（放在日志文本框内部右上角）
        # 使用普通Button以便更好地控制样式
        self.clear_log_btn = tk.Button(
            frame,
            text="🗑",
            command=self.on_clear_log,
            bg="#1e1e1e",  # 与日志背景色相同，实现"透明"效果
            fg="#d4d4d4",
            activebackground="#3c3c3c",  # 鼠标悬停时的背景色
            activeforeground="#d4d4d4",
            relief=tk.FLAT,  # 无边框
            borderwidth=0,
            cursor="hand2",
            font=("Microsoft YaHei", 10),
            padx=5,
            pady=2
        )
        
        # 使用place定位在右上角
        def update_clear_btn_position(event=None):
            """更新清空按钮位置"""
            try:
                # 获取日志文本框的位置和大小
                log_x = self.log_text.winfo_x()
                log_y = self.log_text.winfo_y()
                log_width = self.log_text.winfo_width()
                log_height = self.log_text.winfo_height()
                
                # 按钮大小
                btn_width = 30
                btn_height = 25
                
                # 计算按钮位置（右上角，留出一些边距）
                btn_x = log_x + log_width - btn_width - 5
                btn_y = log_y + 5
                
                # 使用place定位
                self.clear_log_btn.place(x=btn_x, y=btn_y, width=btn_width, height=btn_height)
            except:
                pass
        
        # 绑定鼠标进入和离开事件，实现透明度效果
        def on_enter(event):
            """鼠标进入时，按钮变为不透明"""
            self.clear_log_btn.config(bg="#3c3c3c", relief=tk.RAISED)
        
        def on_leave(event):
            """鼠标离开时，按钮恢复透明"""
            self.clear_log_btn.config(bg="#1e1e1e", relief=tk.FLAT)
        
        self.clear_log_btn.bind("<Enter>", on_enter)
        self.clear_log_btn.bind("<Leave>", on_leave)
        
        # 绑定日志文本框和frame的大小变化事件，更新按钮位置
        self.log_text.bind("<Configure>", update_clear_btn_position)
        frame.bind("<Configure>", update_clear_btn_position)
        
        # 初始定位
        frame.after(100, update_clear_btn_position)
    
    def create_button_widgets(self, parent):
        """创建按钮控件"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(button_frame, text="▶ 开始扫描", command=self.on_start)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹ 停止扫描", command=self.on_stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = ttk.Button(button_frame, text="⚙ 重置配置", command=self.on_reset_config)
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        self.edit_config_btn = ttk.Button(button_frame, text="📝 编辑配置", command=self.on_edit_config)
        self.edit_config_btn.pack(side=tk.LEFT, padx=5)
    
    def on_interval_change(self, *args):
        """扫描间隔改变事件"""
        try:
            value = self.scan_interval_var.get()
            if 1 <= value <= 60:
                self.scan_interval_scale.set(value)
        except:
            pass
    
    def on_interval_scale_change(self, value):
        """扫描间隔滑动条改变事件"""
        try:
            # 设置步长为1
            value = round(float(value))
            self.scan_interval_var.set(value)
        except:
            pass

    def on_duration_scale_change(self, value):
        """显示时长滑动条改变事件"""
        try:
            # 设置步长为1
            value = round(float(value))
            self.display_duration_var.set(value)
        except (ValueError, TypeError):
            pass
    
    def on_font_size_scale_change(self, value):
        """字体大小滑动条改变事件"""
        try:
            # 设置步长为1
            value = round(float(value))
            self.display_font_size_var.set(value)
        except (ValueError, TypeError):
            pass
        except:
            pass
    
    def on_confidence_change(self, *args):
        """置信度改变事件"""
        try:
            value = self.min_confidence_var.get()
            if 0.0 <= value <= 1.0:
                self.min_confidence_scale.set(value)
        except:
            pass
    
    def on_confidence_scale_change(self, value):
        """置信度滑动条改变事件"""
        try:
            val = float(value)
            val = round(val / 0.05) * 0.05
            # 消除浮点数运算误差，保留两位小数
            val = round(val, 2)
            
            # 只有当值真正改变时才更新，避免循环触发
            if abs(self.min_confidence_var.get() - val) > 1e-6:
                self.min_confidence_var.set(val)
        except:
            pass
    
    def load_settings(self):
        """加载设置"""
        # 从config.yaml加载业务配置
        self.enable_roi_var.set(config.get('scan.enable_roi', False))
        self.remember_roi_var.set(config.get('scan.remember_roi', True))
        self.enable_gpu_var.set(config.get('gpu.force_gpu', True))
        self.scan_interval_var.set(config.get('scan.interval_seconds', 5))
        
        # OCR配置
        default_engine = config.get('ocr.default_engine', 'paddle')
        self.ocr_engine_var.set(default_engine)
        self.min_confidence_var.set(round(config.get('ocr.min_confidence', 0.15), 2))
        
        # 读取保存文件配置（默认True）
        save_screenshot = config.get('files.save_screenshot', True)
        self.save_files_var.set(save_screenshot)
        
        # 文字匹配配置
        self.enable_matching_var.set(config.get('matching.enabled', True))
        # 优先使用GUI状态中的路径，否则使用配置文件
        banlist_path = self.state_manager.get_last_banlist_path()
        if not os.path.exists(banlist_path):
            banlist_path = config.get('files.banlist_file', 'docs/banlist.txt')
        self.banlist_path_var.set(banlist_path)
        self.display_duration_var.set(config.get('matching.display_duration', 3))
        position = config.get('matching.position', 'center')
        position_map = {'center': '居中', 'top': '顶部', 'bottom': '底部'}
        self.display_position_var.set(position_map.get(position, '居中'))
        self.display_font_size_var.set(config.get('matching.font_size', 30))
    
    def save_settings(self):
        """保存设置"""
        # 保存业务配置到config.yaml
        config.set('scan.enable_roi', self.enable_roi_var.get())
        config.set('scan.remember_roi', self.remember_roi_var.get())
        config.set('gpu.force_gpu', self.enable_gpu_var.get())
        config.set('scan.interval_seconds', self.scan_interval_var.get())
        
        # OCR配置
        config.set('ocr.default_engine', self.ocr_engine_var.get())
        config.set('ocr.min_confidence', self.min_confidence_var.get())
        
        # 保存文件配置（控制所有文件保存）
        save_files = self.save_files_var.get()
        config.set('files.save_screenshot', save_files)
        config.set('files.save_ocr_result', save_files)
        # 同时也控制中间处理图片的保存
        config.set('ocr.save_processed_image', save_files)
        
        # 文字匹配配置
        config.set('matching.enabled', self.enable_matching_var.get())
        banlist_path = self.banlist_path_var.get()
        config.set('files.banlist_file', banlist_path)
        self.state_manager.set_last_banlist_path(banlist_path)
        config.set('matching.display_duration', self.display_duration_var.get())
        position_map = {'居中': 'center', '顶部': 'top', '底部': 'bottom'}
        config.set('matching.position', position_map.get(self.display_position_var.get(), 'center'))
        config.set('matching.font_size', self.display_font_size_var.get())
        
        # 保存到文件
        if config.save():
            self.append_log("配置已保存", "INFO")
        else:
            self.append_log("配置保存失败", "WARNING")
    
    def on_start(self):
        """开始按钮事件"""
        if self.is_running:
            return
        
        try:
            # 保存当前配置
            self.save_settings()
            
            # 禁用开始按钮，显示初始化状态
            self.start_btn.config(state=tk.DISABLED)
            self.update_status("初始化中...")
            self.append_log("正在初始化OCR引擎...", "INFO")
            
            # 获取参数
            languages = config.get('ocr.languages', ['ch', 'en'])
            use_gpu = self.enable_gpu_var.get()
            engine_choice = self.ocr_engine_var.get()
            
            # 在后台线程中初始化OCR（避免阻塞GUI）
            init_thread = threading.Thread(
                target=self._init_ocr_in_thread,
                args=(engine_choice, languages, use_gpu),
                daemon=True
            )
            init_thread.start()
            
        except Exception as e:
            self.append_log(f"启动失败: {e}", "ERROR")
            self.show_error(f"启动失败: {e}")
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
    
    def _init_ocr_in_thread(self, engine_choice, languages, use_gpu):
        """在后台线程中初始化OCR"""
        try:
            # 初始化扫描服务
            self.scan_service.init_ocr(
                engine_choice=engine_choice,
                languages=languages,
                use_gpu=use_gpu
            )
            
            # 在主线程中更新UI
            self.root.after(0, self._on_ocr_init_complete)
            
        except Exception as e:
            # 在主线程中显示错误
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self._on_ocr_init_failed(msg))
    
    def _on_ocr_init_complete(self):
        """OCR初始化完成后的回调（在主线程中执行）"""
        try:
            self.append_log(f"OCR初始化完成", "INFO")
            
            # 如果启用ROI，先最小化窗口，然后选择ROI区域
            if self.enable_roi_var.get():
                # 先最小化窗口
                self.root.iconify()
                
                # 从配置读取记住ROI状态和已保存的ROI
                remember_roi = self.remember_roi_var.get()
                saved_roi = config.get('scan.saved_roi')
                
                if remember_roi and saved_roi:
                    self.roi = tuple(saved_roi)
                    self.append_log(f"使用保存的ROI区域: {self.roi}", "INFO")
                else:
                    self.append_log("请选择ROI区域...", "INFO")
                    self.roi = select_roi_interactive(parent=self.root)
                    if self.roi is None:
                        self.append_log("ROI选择取消，使用全屏扫描", "WARNING")
                    else:
                        self.append_log(f"ROI区域已设置: {self.roi}", "INFO")
                        
                        if remember_roi:
                            config.set('scan.saved_roi', list(self.roi))
                            config.save()
                            self.append_log("ROI区域已保存", "INFO")
            else:
                self.roi = None
                # 如果没有ROI选择，直接最小化窗口
                self.root.iconify()
            
            # 设置ROI到服务
            self.scan_service.set_roi(self.roi)
            
            # 启动扫描线程
            self.is_running = True
            self.stop_event.clear()
            self.scan_thread = threading.Thread(target=self._run_scan_loop, daemon=True)
            self.scan_thread.start()
            
            # 更新UI
            self.stop_btn.config(state=tk.NORMAL)
            self.update_status("运行中")
            self.append_log("扫描已启动", "INFO")
            
        except Exception as e:
            self.append_log(f"扫描失败: {e}", "ERROR")
            self.show_error(f"扫描失败: {e}")
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.update_status("已停止")
    
    def _on_ocr_init_failed(self, error_msg):
        """OCR初始化失败后的回调（在主线程中执行）"""
        self.append_log(f"OCR初始化失败: {error_msg}", "ERROR")
        self.show_error(f"OCR初始化失败: {error_msg}")
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.update_status("已停止")
    
    def on_stop(self):
        """停止按钮事件"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        # 更新UI
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("已停止")
        self.append_log("扫描已停止", "INFO")
    
    def on_browse_banlist(self):
        """浏览banlist文件"""
        initial_dir = os.path.dirname(self.banlist_path_var.get()) if self.banlist_path_var.get() else "."
        file_path = filedialog.askopenfilename(
            title="选择关键词文件",
            initialdir=initial_dir,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.banlist_path_var.set(file_path)
            self.save_settings()
    
    def on_edit_banlist(self):
        """编辑关键词文件"""
        banlist_path = self.banlist_path_var.get()
        
        # 如果文件路径为空，提示用户先选择文件
        if not banlist_path:
            messagebox.showwarning("警告", "请先选择关键词文件")
            return
        
        # 如果文件不存在，询问是否创建
        if not os.path.exists(banlist_path):
            if not messagebox.askyesno("确认", f"文件不存在：{banlist_path}\n是否创建新文件？"):
                return
            # 创建文件目录
            os.makedirs(os.path.dirname(banlist_path) if os.path.dirname(banlist_path) else ".", exist_ok=True)
        
        # 使用ConfigEditor编辑文本文件（它会自动处理非YAML文件）
        def on_file_saved():
            """文件保存后的回调"""
            self.append_log(f"关键词文件已更新: {banlist_path}", "INFO")
        
        editor = ConfigEditor(self.root, config_file=banlist_path, on_save_callback=on_file_saved)
        editor.show()
    
    def on_reset_config(self):
        """重置配置"""
        if messagebox.askyesno("确认", "确定要重置所有配置为默认值吗？"):
            # 重新加载配置（会使用默认值）
            config.reload()
            self.append_log("配置已重置为默认值", "INFO")
            self.load_settings()
            # 保存重置后的配置
            config.save()
    
    def on_edit_config(self):
        """编辑配置文件"""
        def on_config_saved():
            """配置保存后的回调"""
            # 重新加载配置
            config.reload()
            self.load_settings()
            self.append_log("配置文件已更新，已重新加载", "INFO")
        
        editor = ConfigEditor(self.root, config_file='config/config.yaml', on_save_callback=on_config_saved)
        editor.show()
    
    def on_window_configure(self, event=None):
        """窗口大小或位置改变事件"""
        if event and event.widget == self.root:
            # 保存窗口状态
            try:
                geometry = self.root.geometry()
                # 解析geometry字符串: "widthxheight+x+y"
                parts = geometry.split('+')
                if len(parts) == 3:
                    size_part = parts[0]
                    x = int(parts[1])
                    y = int(parts[2])
                    width, height = map(int, size_part.split('x'))
                    self.state_manager.set_window_geometry(x, y, width, height)
            except:
                pass
    
    def on_window_close(self):
        """窗口关闭事件"""
        if self.is_running:
            if messagebox.askyesno("确认", "扫描正在运行，确定要退出吗？"):
                self.on_stop()
                time.sleep(0.5)  # 等待线程结束
        
        # 保存GUI状态
        self.state_manager.save_state()
        
        self.root.destroy()
    
    def update_status(self, status):
        """更新状态显示"""
        status_text = f"状态: ● {status}"
        self.status_label.config(text=status_text)
        # 同时更新窗口标题（任务栏显示）
        self.update_window_title(status)
    
    def update_window_title(self, status):
        """更新窗口标题，在任务栏显示状态"""
        base_title = "屏幕扫描OCR识别系统"
        # Windows任务栏可能不支持emoji颜色显示，使用清晰的文字前缀
        if status == "运行中":
            # 扫描中：使用明显的文字前缀
            title = f"【扫描中】{base_title}"
        elif status == "初始化中...":
            # 初始化中：使用明显的文字前缀
            title = f"【初始化中】{base_title}"
        elif status == "已停止":
            # 已停止：使用默认标题
            title = base_title
        else:
            title = f"{base_title} - {status}"
        
        self.root.title(title)
    
    def _set_taskbar_state(self, state):
        """设置Windows任务栏按钮状态（仅在Windows上有效）"""
        if not WINDOWS_TASKBAR_AVAILABLE:
            return
        
        try:
            # 获取窗口句柄
            hwnd = self.root.winfo_id()
            if sys.platform == 'win32':
                # Windows任务栏状态设置需要COM接口，这里先简化处理
                # 实际上完整的实现需要创建COM对象并调用ITaskbarList3接口
                # 对于tkinter，这可能比较复杂，我们先用标题显示状态
                pass
        except Exception as e:
            # 如果API调用失败，静默忽略，使用标题显示即可
            pass
    
    def update_stats(self):
        """更新统计信息"""
        self.scan_count_label.config(text=f"扫描次数: {self.scan_count}")
        if self.last_scan_time:
            self.last_scan_label.config(text=f"最后扫描: {self.last_scan_time}")
        else:
            self.last_scan_label.config(text="最后扫描: 无")
    
    def _schedule_memory_update(self):
        """定时刷新内存显示"""
        try:
            if self.memory_label and get_working_set_mb is not None:
                ws_mb = get_working_set_mb(self._memory_pid)
                if ws_mb is None:
                    self.memory_label.config(text="内存: -- MB")
                else:
                    self.memory_label.config(text=f"内存: {ws_mb:.1f} MB")
        except Exception:
            pass
        
        self.root.after(self._memory_interval_ms, self._schedule_memory_update)
    
    def setup_gui_logger(self):
        """设置GUI日志处理器"""
        # 创建GUI日志处理器
        gui_handler = GUILoggerHandler(self.log_queue)
        gui_handler.setLevel(logging.DEBUG)
        
        # 添加到根日志记录器
        root_logger = logging.getLogger()
        root_logger.addHandler(gui_handler)
        
        # 设置日志级别
        log_level = config.get('logging.level', 'INFO')
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    def append_log(self, message, level='INFO'):
        """追加日志到日志区域"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 确保每条日志消息都以换行符结尾
        log_message = f"{timestamp} - {message}\n"
        
        # 将日志放入队列
        try:
            self.log_queue.put_nowait((log_message, level))
        except queue.Full:
            pass
    
    def on_clear_log(self):
        """清空日志"""
        self.log_text.delete('1.0', tk.END)
        self.append_log("日志已清空", "INFO")
    
    def process_log_queue(self):
        """处理日志队列（在主线程中）"""
        try:
            while True:
                try:
                    log_message, level = self.log_queue.get_nowait()
                    self.log_text.insert(tk.END, log_message, level)
                    self.log_text.see(tk.END)
                    
                    # 限制日志行数
                    max_lines = self.state_manager.get_log_max_lines()
                    lines = int(self.log_text.index('end-1c').split('.')[0])
                    if lines > max_lines:
                        # 删除前100行
                        self.log_text.delete('1.0', '100.0')
                except queue.Empty:
                    break
        except:
            pass
        
        # 每100ms检查一次
        self.root.after(100, self.process_log_queue)
    
    def show_error(self, message):
        """显示错误消息"""
        messagebox.showerror("错误", message)
    
    def show_info(self, message):
        """显示信息消息"""
        messagebox.showinfo("信息", message)
    
    def _run_scan_loop(self):
        """运行扫描循环（在独立线程中）"""
        # 获取配置
        scan_interval = self.scan_interval_var.get()
        
        try:
            while not self.stop_event.is_set():
                self.scan_count += 1
                self.append_log(f"开始第 {self.scan_count} 次扫描...", "INFO")
                
                # 获取当前时间
                now = datetime.now()
                self.last_scan_time = now.strftime('%H:%M:%S')
                
                # 更新统计信息（在主线程中）
                self.root.after(0, self.update_stats)
                
                # 执行扫描
                result = self.scan_service.scan_once()
                
                if result['success']:
                    self.append_log(f"扫描完成，耗时 {result['duration']:.2f}秒", "INFO")
                    if 'screenshot_path' in result and result['screenshot_path']:
                        self.append_log(f"截图已保存: {os.path.basename(result['screenshot_path'])}", "DEBUG")
                    
                    # 如果有匹配结果，显示浮窗（在主线程中）
                    if 'matches' in result and result['matches']:
                        matches = result['matches']
                        self.append_log(f"匹配成功: {matches}", "INFO")
                        
                        # 在主线程中显示
                        self.root.after(0, lambda: display_matches(
                            matches,
                            duration=self.scan_service.display_duration,
                            position=self.scan_service.display_position,
                            font_size=self.scan_service.display_font_size,
                            parent_root=self.root
                        ))
                        
                elif 'error' in result:
                    self.append_log(f"扫描出错: {result['error']}", "ERROR")
                
                # 计算等待时间
                scan_duration = result['duration']
                wait_time = max(0, scan_interval - scan_duration)
                
                if wait_time > 0:
                    # 等待指定时间，但每0.5秒检查一次停止信号
                    elapsed = 0
                    while elapsed < wait_time and not self.stop_event.is_set():
                        time.sleep(0.5)
                        elapsed += 0.5
                else:
                    self.append_log(f"扫描耗时 {scan_duration:.2f}秒，超过间隔时间，立即开始下一次扫描", "WARNING")
        
        except Exception as e:
            self.append_log(f"扫描循环出错: {e}", "ERROR")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.update_status("已停止"))
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))


def main():
    """主函数"""
    root = tk.Tk()
    app = MainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()