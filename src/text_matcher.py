"""
文字匹配和显示模块
从OCR结果中提取文字，与TXT文件进行对比，匹配成功后在屏幕上显示
"""

import os
import threading
import time
from datetime import datetime
import tkinter as tk


class TextMatcher:
    """文字匹配器"""
    
    def __init__(self, txt_file="docs/banlist.txt"):
        """
        初始化文字匹配器
        
        Args:
            txt_file (str): 关键词TXT文件路径，默认为 docs/banlist.txt
        """
        self.txt_file = txt_file
        self.keywords = self._load_keywords()
    
    def _load_keywords(self):
        """加载关键词列表"""
        keywords = []
        if os.path.exists(self.txt_file):
            try:
                with open(self.txt_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            keywords.append(line)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已加载 {len(keywords)} 个关键词")
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 加载关键词文件失败: {e}")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 关键词文件不存在: {self.txt_file}")
            # 创建默认关键词文件
            self._create_default_keywords_file()
        
        return keywords
    
    def _create_default_keywords_file(self):
        """创建默认关键词文件"""
        try:
            with open(self.txt_file, 'w', encoding='utf-8') as f:
                f.write("示例关键词1\n")
                f.write("示例关键词2\n")
                f.write("示例关键词3\n")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已创建默认关键词文件: {self.txt_file}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 创建默认关键词文件失败: {e}")
    
    def reload_keywords(self):
        """重新加载关键词"""
        self.keywords = self._load_keywords()
    
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
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 匹配成功: '{keyword}' (OCR: '{ocr_text}')")
                    break
        
        if matched_keywords:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 总共匹配到 {len(matched_keywords)} 个关键词")
        
        return matched_keywords


class FloatingTextDisplay:
    """浮动文字显示器"""
    
    def __init__(self, text, duration=3, position="center"):
        """
        初始化浮动文字显示器
        
        Args:
            text (str): 要显示的文字
            duration (int): 显示时长（秒），默认为3
            position (str): 显示位置，"center"（屏幕中央）、"top"（顶部）、"bottom"（底部）
        """
        self.text = text
        self.duration = duration
        self.position = position
        self.root = None
        self.label = None
    
    def show(self):
        """显示浮动文字"""
        def _show():
            # 创建主窗口
            self.root = tk.Tk()
            self.root.overrideredirect(True)  # 无边框
            self.root.attributes('-topmost', True)  # 置顶
            self.root.attributes('-alpha', 0.9)  # 半透明
            self.root.attributes('-disabled', True)  # 禁用窗口，不捕获鼠标事件
            
            # 创建标签
            self.label = tk.Label(
                self.root,
                text=self.text,
                font=('Microsoft YaHei', 24, 'bold'),
                bg='yellow',
                fg='red',
                padx=20,
                pady=10,
                relief='raised',
                borderwidth=3
            )
            self.label.pack()
            
            # 设置窗口位置
            self._set_position()
            
            # 更新窗口
            self.root.update()
            
            # 等待指定时间后关闭
            time.sleep(self.duration)
            
            # 关闭窗口
            self.root.destroy()
        
        # 在新线程中显示，避免阻塞主线程
        thread = threading.Thread(target=_show, daemon=True)
        thread.start()
    
    def _set_position(self):
        """设置窗口位置"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 更新窗口以获取实际尺寸
        self.root.update()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        if self.position == "center":
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        elif self.position == "top":
            x = (screen_width - window_width) // 2
            y = 50
        elif self.position == "bottom":
            x = (screen_width - window_width) // 2
            y = screen_height - window_height - 50
        else:
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        
        self.root.geometry(f"+{x}+{y}")


def match_and_display(ocr_results, txt_file="docs/banlist.txt", duration=3, position="center"):
    """
    匹配关键词并显示
    
    Args:
        ocr_results (list): OCR识别结果列表
        txt_file (str): 关键词TXT文件路径，默认为 docs/banlist.txt
        duration (int): 显示时长（秒）
        position (str): 显示位置
    
    Returns:
        list: 匹配到的关键词列表
    """
    # 创建匹配器
    matcher = TextMatcher(txt_file)
    
    # 匹配关键词
    matched_keywords = matcher.match(ocr_results)
    
    # 如果有匹配的关键词，显示在屏幕上
    if matched_keywords:
        # 将所有匹配的关键词合并为一个字符串
        display_text = " | ".join(matched_keywords)
        
        # 创建并显示浮动文字
        display = FloatingTextDisplay(display_text, duration, position)
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
