"""
文字匹配和显示模块
从OCR结果中提取文字，与TXT文件进行对比，匹配成功后在屏幕上显示
"""

import os
import threading
import time
import tkinter as tk

from .logger import logger


class TextMatcher:
    """文字匹配器"""
    
    def __init__(self, txt_file="docs/banlist.txt"):
        """
        初始化文字匹配器
        
        Args:
            txt_file (str): 关键词TXT文件路径，默认为 docs/banlist.txt
        """
        self.txt_file = txt_file
        self.keywords = []
        self._last_mtime = None
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
        """创建默认关键词文件"""
        try:
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
    
    def match(self, ocr_results):
        """
        匹配OCR结果中的关键词（基于字符串包含）
        
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
        
        # 检查每个关键词是否在OCR结果中
        for keyword in self.keywords:
            for ocr_text in ocr_texts:
                # 检查关键词是否包含在OCR结果中
                if keyword in ocr_text:
                    matched_keywords.append(keyword)
                    logger.info(f"匹配成功: '{keyword}' (OCR: '{ocr_text}')")
                    break
        
        if matched_keywords:
            logger.info(f"总共匹配到 {len(matched_keywords)} 个关键词")
        
        return matched_keywords


class FloatingTextDisplay:
    """遮罩式文字显示器（水印效果）"""

    def __init__(self, text, duration=3, position="center", font_size=30):
        """
        初始化遮罩式文字显示器

        Args:
            text (str): 要显示的文字
            duration (int): 显示时长（秒），默认为3
            position (str): 显示位置，"center"（屏幕中央）、"top"（顶部）、"bottom"（底部）
            font_size (int): 字体大小，默认为30
        """
        self.text = text
        self.duration = duration
        self.position = position
        self.font_size = font_size
        self.root = None

    def show(self):
        """显示遮罩文字（水印效果）"""
        def _show():
            try:
                # 创建透明窗口用于显示水印文字
                self.root = tk.Tk()
                self.root.overrideredirect(True)  # 无边框
                self.root.attributes('-topmost', True)  # 置顶

                # 设置为工具窗口，减少系统干扰
                try:
                    self.root.attributes('-toolwindow', True)
                except:
                    pass  # 某些tkinter版本不支持

                # 关键：设置半透明窗口（而不是完全透明），确保文字可见但不干扰操作
                self.root.attributes('-alpha', 0.5)  # 50%透明度，水印效果

                # 重要：确保窗口不会获得焦点，真正实现水印效果
                self.root.attributes('-disabled', True)  # 禁用窗口输入
                try:
                    self.root.attributes('-focusable', False)  # 窗口不可获得焦点
                except:
                    pass  # 某些tkinter版本不支持此属性

                # 防止窗口出现在任务栏
                try:
                    self.root.attributes('-type', 'splash')  # 设置为启动画面类型
                except:
                    pass  # 某些系统不支持

                # 获取屏幕尺寸
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()

                # 计算文字区域的尺寸和位置
                text_width, text_height, window_x, window_y = self._calculate_window_geometry(screen_width, screen_height)

                # 设置窗口大小为紧贴文字的大小（最小包裹，只添加2像素边距避免裁剪）
                padding = 2  # 最小边距，避免文字被裁剪
                window_width = text_width + padding * 2
                window_height = text_height + padding * 2
                self.root.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")

                # 创建Canvas，大小匹配窗口
                canvas = tk.Canvas(
                    self.root,
                    width=window_width,
                    height=window_height,
                    highlightthickness=0,  # 无边框
                    takefocus=False  # 不接受焦点
                )
                canvas.pack()

                # 计算文字在Canvas中的位置（居中）
                text_x = window_width // 2
                text_y = window_height // 2

                # 构建字体元组
                font_tuple = ('Microsoft YaHei', self.font_size, 'bold')

                # 在Canvas上绘制文字，使用半透明颜色
                canvas.create_text(
                    text_x, text_y,
                    text=self.text,
                    font=font_tuple,
                    fill='#FF4444',  # 半透明红色
                    anchor='center',
                    tags='watermark_text'
                )

                # 添加文字阴影效果，让水印更明显
                shadow_offset = max(1, self.font_size // 30)  # 根据字体大小调整阴影偏移
                canvas.create_text(
                    text_x + shadow_offset, text_y + shadow_offset,
                    text=self.text,
                    font=font_tuple,
                    fill='#000000',  # 黑色阴影
                    anchor='center',
                    tags='watermark_shadow'
                )

                # 重新排列图层，确保文字在阴影之上
                canvas.tag_raise('watermark_text', 'watermark_shadow')

                # 更新窗口
                self.root.update_idletasks()
                self.root.update()

                # 直接显示（无渐显渐隐效果）

                # 等待指定时间（保持显示）
                start_time = time.time()
                while time.time() - start_time < self.duration:
                    # 短暂休眠，让其他事件处理
                    time.sleep(0.1)
                    # 保持窗口更新
                    try:
                        self.root.update_idletasks()
                    except:
                        break  # 窗口可能已被销毁

                # 直接关闭窗口（无渐隐效果）

            except Exception as e:
                logger.error(f"显示水印文字时出错: {e}")
            finally:
                # 关闭窗口
                if self.root:
                    try:
                        self.root.destroy()
                    except:
                        pass

        # 在新线程中显示，避免阻塞主线程
        thread = threading.Thread(target=_show, daemon=True)
        thread.start()

    def _calculate_window_geometry(self, screen_width, screen_height):
        """计算窗口几何信息（位置和大小）"""
        # 使用更准确的文字尺寸计算
        font = ('Microsoft YaHei', self.font_size, 'bold')

        # 创建临时标签来测量文字尺寸
        temp_label = tk.Label(self.root, text=self.text, font=font)
        self.root.update_idletasks()  # 确保标签被正确初始化

        try:
            # 获取文字的实际尺寸
            text_width = temp_label.winfo_reqwidth()
            text_height = temp_label.winfo_reqheight()
        except:
            # 如果测量失败，使用估算值（根据字体大小动态调整）
            text_width = len(self.text) * int(self.font_size * 0.6)
            text_height = int(self.font_size * 1.2)

        # 销毁临时标签
        temp_label.destroy()

        # 最小边距（用于计算窗口位置时保持一致）
        padding = 2
        window_width = text_width + padding * 2

        # 根据位置计算窗口在屏幕上的位置（紧贴文字，无额外边距）
        if self.position == "center":
            # 窗口居中显示
            window_x = (screen_width - window_width) // 2
            window_y = (screen_height - (text_height + padding * 2)) // 2
        elif self.position == "top":
            # 窗口显示在顶部
            window_x = (screen_width - window_width) // 2
            window_y = 50
        elif self.position == "bottom":
            # 窗口显示在底部
            window_x = (screen_width - window_width) // 2
            window_y = screen_height - (text_height + padding * 2) - 50
        else:
            # 默认居中
            window_x = (screen_width - window_width) // 2
            window_y = (screen_height - (text_height + padding * 2)) // 2

        return text_width, text_height, window_x, window_y

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


def match_and_display(ocr_results, txt_file="docs/banlist.txt", duration=3, position="center", font_size=30):
    """
    匹配关键词并显示
    
    Args:
        ocr_results (list): OCR识别结果列表
        txt_file (str): 关键词TXT文件路径，默认为 docs/banlist.txt
        duration (int): 显示时长（秒）
        position (str): 显示位置
        font_size (int): 字体大小，默认为30
    
    Returns:
        list: 匹配到的关键词列表
    """
    # 使用缓存的匹配器（避免每次读取文件）
    matcher = _get_cached_matcher(txt_file)
    
    # 匹配关键词
    matched_keywords = matcher.match(ocr_results)
    
    # 如果有匹配的关键词，显示在屏幕上
    if matched_keywords:
        # 将所有匹配的关键词合并为一个字符串
        display_text = " | ".join(matched_keywords)
        
        # 创建并显示浮动文字
        display = FloatingTextDisplay(display_text, duration, position, font_size)
        display.show()
    
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

