"""
文字匹配和显示模块
从OCR结果中提取文字，与TXT文件进行对比，匹配成功后在屏幕上显示
"""

import os
import threading
import tkinter as tk

from .logger import logger

try:
    from ..config.config import config
except Exception:
    config = None


# 匹配阈值：关键词中至少该比例字符（按顺序）在 OCR 文本中出现则算匹配
MATCH_RATIO_THRESHOLD = 0.75


class TextMatcher:
    """文字匹配器"""
    
    def __init__(self, txt_file="docs/banlist.txt", match_ratio_threshold=None):
        """
        初始化文字匹配器
        
        Args:
            txt_file (str): 关键词TXT文件路径，默认为 docs/banlist.txt
            match_ratio_threshold (float): 匹配比例阈值，默认 0.75，即 75% 以上文字匹配则算数
        """
        self.txt_file = txt_file
        self.keywords = []
        self._last_mtime = None
        self.match_ratio_threshold = match_ratio_threshold if match_ratio_threshold is not None else MATCH_RATIO_THRESHOLD
        self.keywords = self._load_keywords()
    
    def _load_keywords(self):
        """加载关键词列表"""
        keywords = []
        if os.path.exists(self.txt_file):
            try:
                self._last_mtime = os.path.getmtime(self.txt_file)
                with open(self.txt_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            keywords.append(line)
                logger.info(f"已加载 {len(keywords)} 个关键词")
            except Exception as e:
                logger.error(f"加载关键词文件失败: {e}", exc_info=True)
        else:
            logger.warning(f"关键词文件不存在: {self.txt_file}")
            # 创建默认关键词文件
            self._create_default_keywords_file()
            self._last_mtime = None
        
        return keywords
    
    def _create_default_keywords_file(self):
        """创建默认关键词文件（如果不存在）"""
        if os.path.exists(self.txt_file):
            return
        
        try:
            os.makedirs(os.path.dirname(self.txt_file), exist_ok=True) if os.path.dirname(self.txt_file) else None
            with open(self.txt_file, 'w', encoding='utf-8') as f:
                f.write("示例关键词1\n")
                f.write("示例关键词2\n")
                f.write("示例关键词3\n")
            logger.info(f"已创建默认关键词文件: {self.txt_file}")
        except Exception as e:
            logger.error(f"创建默认关键词文件失败: {e}", exc_info=True)
    
    def reload_keywords(self):
        """重新加载关键词"""
        self.keywords = self._load_keywords()

    def reload_if_changed(self):
        """如果关键词文件已更新则重新加载"""
        if not os.path.exists(self.txt_file):
            # 文件不存在时保持现有关键词，避免频繁清空
            return
        
        try:
            current_mtime = os.path.getmtime(self.txt_file)
        except Exception:
            return
        
        if self._last_mtime is None or current_mtime != self._last_mtime:
            self.reload_keywords()

    def _match_ratio(self, keyword, ocr_text):
        """
        计算关键词在 OCR 文本中的匹配比例（按顺序出现的字符数 / 关键词长度）。
        用于实现“75% 以上文字匹配则算数”。
        
        Args:
            keyword (str): 关键词
            ocr_text (str): OCR 识别出的文本
        
        Returns:
            float: 0.0~1.0，表示关键词中有多少比例字符按顺序在 ocr_text 中出现
        """
        if not keyword:
            return 1.0
        if not ocr_text:
            return 0.0
        pos = 0
        matched = 0
        for c in keyword:
            i = ocr_text.find(c, pos)
            if i != -1:
                matched += 1
                pos = i + 1
        return matched / len(keyword)
    
    def _get_match_threshold(self):
        """获取当前匹配比例阈值（优先从配置读取，便于界面可调）"""
        if config is not None:
            return float(config.get('matching.match_ratio_threshold', self.match_ratio_threshold))
        return self.match_ratio_threshold

    def match(self, ocr_results):
        """
        匹配OCR结果中的关键词。只要 OCR 某条结果里包含该关键词（子串包含）即算匹配。
        
        Args:
            ocr_results (list): OCR识别结果列表，每个元素是包含'text'键的字典
        
        Returns:
            list: 匹配到的关键词列表
        """
        matched_keywords = []
        
        if not self.keywords:
            return matched_keywords
        
        # 从OCR结果中提取所有文字
        ocr_texts = []
        for result in ocr_results:
            if isinstance(result, dict) and 'text' in result:
                ocr_texts.append(result['text'])
        
        # 只要关键词在任意一条 OCR 结果中出现即算匹配
        for keyword in self.keywords:
            for ocr_text in ocr_texts:
                if keyword in ocr_text:
                    matched_keywords.append(keyword)
                    logger.info(f"匹配成功: '{keyword}' (OCR: '{ocr_text}')")
                    break
        
        if matched_keywords:
            logger.info(f"总共匹配到 {len(matched_keywords)} 个关键词")
        
        return matched_keywords


class FloatingTextDisplay:
    """遮罩式文字显示器（水印效果）"""

    def __init__(self, text_lines, duration=3, position="center", font_size=20, parent_root=None):
        """
        初始化遮罩式文字显示器

        Args:
            text_lines (list): 要显示的文字行列表，每行是 (text, color) 元组
            duration (int): 显示时长（秒），默认为3
            position (str): 显示位置，"center"（屏幕中央）、"top"（顶部）、"bottom"（底部）
            font_size (int): 字体大小，默认为20
            parent_root: 可选的父窗口（Tkinter根窗口）。如果提供，将使用Toplevel创建浮窗。
        """
        self.text_lines = text_lines
        self.duration = duration
        self.position = position
        self.font_size = font_size
        self.parent_root = parent_root
        self.root = None

    def show(self):
        """显示遮罩文字（水印效果）"""
        if self.parent_root:
            # 如果有父窗口，在主线程中调度显示
            self.parent_root.after(0, self._show_in_main_thread)
        else:
            # 如果没有父窗口（命令行模式），在新线程中显示
            # 注意：如果主线程没有运行mainloop，这里创建tk.Tk()是安全的
            # 但如果主线程有mainloop，这里会报错。所以确保只在命令行模式下使用无parent_root的方式
            thread = threading.Thread(target=self._show_standalone, daemon=True)
            thread.start()

    def _show_in_main_thread(self):
        """在主线程中显示（使用Toplevel）"""
        try:
            self.root = tk.Toplevel(self.parent_root)
            self._setup_window()
            
            # 定时关闭
            self.root.after(int(self.duration * 1000), self._close)
        except Exception as e:
            logger.error(f"显示水印文字失败: {e}")

    def _show_standalone(self):
        """独立显示（创建新的Tk实例）"""
        try:
            self.root = tk.Tk()
            self._setup_window()
            
            # 定时关闭
            self.root.after(int(self.duration * 1000), self._close_standalone)
            
            self.root.mainloop()
        except Exception as e:
            logger.error(f"显示独立水印文字失败: {e}")

    def _close(self):
        """关闭窗口"""
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
            self.root = None

    def _close_standalone(self):
        """关闭独立窗口"""
        if self.root:
            try:
                self.root.destroy()
                # 退出mainloop
                self.root.quit()
            except:
                pass
            self.root = None

    def _setup_window(self):
        """设置窗口属性和内容"""
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes('-topmost', True)  # 置顶

        # 设置为工具窗口，减少系统干扰
        try:
            self.root.attributes('-toolwindow', True)
        except:
            pass

        # 关键：设置透明背景，让鼠标事件穿透
        self.root.attributes('-transparentcolor', 'black')
        self.root.config(bg='black')
        self.root.attributes('-alpha', 0.7)

        # 允许鼠标穿透窗口（Windows API）
        try:
            import ctypes
            from ctypes import windll
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except:
            pass

        # 防止窗口出现在任务栏
        try:
            self.root.attributes('-type', 'splash')
        except:
            pass

        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 计算文字区域的尺寸和位置
        text_width, text_height, window_x, window_y = self._calculate_window_geometry(screen_width, screen_height)

        # 设置窗口大小
        padding = 2
        window_width = text_width + padding * 2
        window_height = text_height + padding * 2
        self.root.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")

        # 创建Canvas
        canvas = tk.Canvas(
            self.root,
            width=window_width,
            height=window_height,
            bg='black',
            highlightthickness=0,
            takefocus=False
        )
        canvas.pack()

        # 构建字体元组
        font_tuple = ('Microsoft YaHei', self.font_size, 'bold')

        # 绘制多行文字
        line_height = self.font_size * 1.3
        start_y = padding + line_height / 2
        
        for i, (text, color) in enumerate(self.text_lines):
            # 计算文字在Canvas中的位置
            text_x = window_width // 2
            text_y = start_y + i * line_height

            # 添加阴影
            shadow_offset = max(1, self.font_size // 30)
            canvas.create_text(
                text_x + shadow_offset, text_y + shadow_offset,
                text=text,
                font=font_tuple,
                fill='#000000',
                anchor='center',
                tags=f'watermark_shadow_{i}'
            )

            # 绘制文字
            canvas.create_text(
                text_x, text_y,
                text=text,
                font=font_tuple,
                fill=color,
                anchor='center',
                tags=f'watermark_text_{i}'
            )

            # 重新排列图层
            canvas.tag_raise(f'watermark_text_{i}', f'watermark_shadow_{i}')


    def _calculate_window_geometry(self, screen_width, screen_height):
        """计算窗口几何信息（位置和大小）"""
        font = ('Microsoft YaHei', self.font_size, 'bold')

        # 计算所有文字行的最大宽度和总高度
        max_text_width = 0
        total_text_height = 0
        line_height = int(self.font_size * 1.3)

        for text, _ in self.text_lines:
            # 创建临时标签来测量文字尺寸
            temp_label = tk.Label(self.root, text=text, font=font)
            self.root.update_idletasks()

            try:
                text_width = temp_label.winfo_reqwidth()
            except:
                text_width = len(text) * int(self.font_size * 0.6)

            temp_label.destroy()

            max_text_width = max(max_text_width, text_width)
            total_text_height += line_height

        # 最小边距（用于计算窗口位置时保持一致）
        padding = 2
        window_width = max_text_width + padding * 2
        window_height = total_text_height + padding * 2

        # 根据位置计算窗口在屏幕上的位置（紧贴文字，无额外边距）
        if self.position == "center":
            # 窗口居中显示
            window_x = (screen_width - window_width) // 2
            window_y = (screen_height - window_height) // 2
        elif self.position == "top":
            # 窗口显示在顶部
            window_x = (screen_width - window_width) // 2
            window_y = 50
        elif self.position == "bottom":
            # 窗口显示在底部
            window_x = (screen_width - window_width) // 2
            window_y = screen_height - window_height - 50
        else:
            # 默认居中
            window_x = (screen_width - window_width) // 2
            window_y = (screen_height - window_height) // 2

        return int(max_text_width), int(total_text_height), int(window_x), int(window_y)

_matcher_cache = {}
_cache_lock = threading.Lock()


def _get_cached_matcher(txt_file: str) -> TextMatcher:
    """获取（或创建）缓存的关键词匹配器"""
    file_path = os.path.abspath(txt_file)
    with _cache_lock:
        matcher = _matcher_cache.get(file_path)
        if matcher is None:
            matcher = TextMatcher(file_path)
            _matcher_cache[file_path] = matcher
    matcher.reload_if_changed()
    return matcher


def display_ocr_results(ocr_results, matched_keywords, duration=3, position="center", font_size=20, parent_root=None, matcher=None):
    """
    显示OCR识别结果，用颜色区分匹配状态。某行包含任一匹配关键词即标为匹配（红色）。
    
    Args:
        ocr_results (list): OCR识别结果列表，每个元素包含 text, confidence, bbox
        matched_keywords (list): 匹配到的关键词列表
        duration (int): 显示时长
        position (str): 显示位置
        font_size (int): 字体大小
        parent_root: 可选的父窗口
        matcher (TextMatcher): 可选，保留参数兼容
    """
    if not ocr_results:
        return
    
    # 生成带颜色的文字行列表
    text_lines = []
    for result in ocr_results:
        text = result.get('text', '')
        if not text:
            continue
        
        # 只要该行 OCR 文本中包含任一匹配关键词即算匹配（子串包含）
        is_matched = any(keyword in text for keyword in matched_keywords)
        # 匹配的用红色，未匹配的用绿色
        color = '#ff3333' if is_matched else '#00ff00'
        text_lines.append((text, color))
    
    # 创建并显示浮动文字
    display = FloatingTextDisplay(text_lines, duration, position, font_size, parent_root)
    display.show()


def display_matches(matched_keywords, duration=3, position="center", font_size=30, parent_root=None):
    """
    显示匹配的关键词（旧接口，保留兼容性）
    
    Args:
        matched_keywords (list): 匹配到的关键词列表
        duration (int): 显示时长
        position (str): 显示位置
        font_size (int): 字体大小
        parent_root: 可选的父窗口
    """
    if matched_keywords:
        # 将所有匹配的关键词合并为一个字符串
        display_text = " | ".join(matched_keywords)
        
        # 创建并显示浮动文字
        display = FloatingTextDisplay([(display_text, '#ff3333')], duration, position, font_size, parent_root)
        display.show()


def match_and_display(ocr_results, txt_file="docs/banlist.txt", duration=3, position="center", font_size=20):
    """
    匹配关键词并显示（显示所有OCR结果，用颜色区分匹配状态）
    
    Args:
        ocr_results (list): OCR识别结果列表
        txt_file (str): 关键词TXT文件路径
        duration (int): 显示时长
        position (str): 显示位置
        font_size (int): 字体大小
    
    Returns:
        list: 匹配到的关键词列表
    """
    # 使用缓存的匹配器（避免每次读取文件）
    matcher = _get_cached_matcher(txt_file)
    
    # 匹配关键词（75% 以上文字匹配则算数）
    matched_keywords = matcher.match(ocr_results)
    
    # 显示所有OCR结果，用颜色区分匹配状态（使用同一 matcher 保证高亮与匹配一致）
    display_ocr_results(ocr_results, matched_keywords, duration, position, font_size, matcher=matcher)
    
    return matched_keywords


if __name__ == "__main__":
    """测试文字匹配和显示功能"""
    print("文字匹配和显示模块测试")
    
    # 创建测试关键词文件
    test_file = "test_keywords.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("测试\n")
        f.write("匹配\n")
        f.write("显示\n")
    
    # 模拟OCR结果
    test_ocr_results = [
        {'text': '这是一个测试文本', 'confidence': 0.95},
        {'text': '匹配成功', 'confidence': 0.88},
        {'text': '其他文字', 'confidence': 0.92}
    ]
    
    # 测试匹配和显示
    matched = match_and_display(test_ocr_results, test_file, duration=3)
    print(f"匹配到的关键词: {matched}")

