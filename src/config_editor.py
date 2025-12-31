"""
配置文件编辑器模块
提供YAML配置文件编辑功能，支持语法高亮和格式验证
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ConfigEditor:
    """配置文件编辑器"""
    
    def __init__(self, parent, config_file='config.yaml', on_save_callback=None):
        """
        初始化编辑器
        
        Args:
            parent: 父窗口
            config_file: 配置文件路径
            on_save_callback: 保存后的回调函数
        """
        self.parent = parent
        self.config_file = Path(config_file)
        self.on_save_callback = on_save_callback
        self.window = None
        self.text_widget = None
        self.original_content = None
        self.is_modified = False
        
    def show(self):
        """显示编辑器窗口"""
        if self.window is not None:
            self.window.lift()
            self.window.focus()
            return
        
        # 创建编辑器窗口
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"编辑配置文件 - {self.config_file.name}")
        self.window.geometry("900x700")
        
        # 创建控件
        self.create_widgets()
        
        # 加载配置文件
        if not self.load_config():
            self.window.destroy()
            self.window = None
            return
        
        # 绑定窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # 绑定文本改变事件
        self.text_widget.bind('<KeyRelease>', self.on_text_change)
        self.text_widget.bind('<Button-1>', self.on_text_change)
        
        # 焦点设置
        self.text_widget.focus_set()
    
    def create_widgets(self):
        """创建编辑器控件"""
        # 主容器
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # 按钮
        save_btn = ttk.Button(toolbar, text="保存 (Ctrl+S)", command=self.on_save)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = ttk.Button(toolbar, text="重置", command=self.on_reset)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(toolbar, text="取消", command=self.on_cancel)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_label = ttk.Label(toolbar, text="就绪")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # 文本编辑区域
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # 行号（简化版，使用标签显示）
        line_label = ttk.Label(text_frame, text="行号", width=5, anchor='n')
        line_label.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # 文本编辑器
        self.text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.NONE,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4",
            selectbackground="#264f78",
            undo=True
        )
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置文本标签颜色
        self.text_widget.tag_config("comment", foreground="#6a9955")  # 注释
        self.text_widget.tag_config("key", foreground="#9cdcfe")  # 键
        self.text_widget.tag_config("string", foreground="#ce9178")  # 字符串
        self.text_widget.tag_config("number", foreground="#b5cea8")  # 数字
        self.text_widget.tag_config("boolean", foreground="#569cd6")  # 布尔值
        
        # 绑定快捷键
        self.window.bind('<Control-s>', lambda e: self.on_save())
        self.window.bind('<Control-S>', lambda e: self.on_save())
        self.window.bind('<Escape>', lambda e: self.on_cancel())
    
    def load_config(self):
        """加载配置文件内容"""
        try:
            if not self.config_file.exists():
                self.show_error(f"配置文件不存在: {self.config_file}")
                return False
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
            
            # 显示内容
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', self.original_content)
            
            # 应用语法高亮
            self.highlight_syntax()
            
            self.is_modified = False
            self.update_status("已加载")
            return True
            
        except Exception as e:
            self.show_error(f"加载配置文件失败: {e}")
            return False
    
    def save_config(self):
        """保存配置文件"""
        try:
            content = self.text_widget.get('1.0', tk.END)
            
            # 验证YAML格式
            if not self.validate_yaml(content):
                return False
            
            # 保存文件
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.original_content = content
            self.is_modified = False
            self.update_status("已保存")
            
            # 调用回调函数
            if self.on_save_callback:
                self.on_save_callback()
            
            self.show_info("配置文件已保存")
            return True
            
        except Exception as e:
            self.show_error(f"保存配置文件失败: {e}")
            return False
    
    def validate_yaml(self, content):
        """验证YAML格式"""
        if not YAML_AVAILABLE:
            self.show_error("PyYAML未安装，无法验证YAML格式。请运行: pip install pyyaml")
            return False
        
        try:
            yaml.safe_load(content)
            return True
        except yaml.YAMLError as e:
            error_msg = f"YAML格式错误:\n{str(e)}"
            self.show_error(error_msg)
            return False
    
    def on_save(self):
        """保存按钮事件"""
        if self.save_config():
            # 不关闭窗口，允许继续编辑
            pass
    
    def on_cancel(self):
        """取消按钮事件"""
        if self.is_modified:
            if not messagebox.askyesno("确认", "有未保存的更改，确定要关闭吗？"):
                return
        
        self.window.destroy()
        self.window = None
        self.text_widget = None
        self.is_modified = False
    
    def on_reset(self):
        """重置为原始内容"""
        if not self.is_modified:
            return
        
        if messagebox.askyesno("确认", "确定要重置为原始内容吗？所有更改将丢失。"):
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', self.original_content)
            self.highlight_syntax()
            self.is_modified = False
            self.update_status("已重置")
    
    def on_text_change(self, event=None):
        """文本改变事件"""
        if self.text_widget:
            current_content = self.text_widget.get('1.0', tk.END)
            self.is_modified = (current_content != self.original_content)
            
            if self.is_modified:
                self.update_status("已修改")
            else:
                self.update_status("就绪")
    
    def update_status(self, status):
        """更新状态标签"""
        if self.status_label:
            self.status_label.config(text=status)
    
    def highlight_syntax(self):
        """语法高亮（简化版）"""
        if not self.text_widget:
            return
        
        content = self.text_widget.get('1.0', tk.END)
        lines = content.split('\n')
        
        # 简单的语法高亮规则
        for i, line in enumerate(lines):
            line_start = f"{i+1}.0"
            line_end = f"{i+1}.end"
            
            # 注释（以#开头）
            if line.strip().startswith('#'):
                self.text_widget.tag_add("comment", line_start, line_end)
            
            # 键（冒号前的部分）
            if ':' in line:
                colon_pos = line.find(':')
                key_part = line[:colon_pos].strip()
                if key_part:
                    key_start = f"{i+1}.0"
                    key_end = f"{i+1}.{colon_pos}"
                    self.text_widget.tag_add("key", key_start, key_end)
            
            # 字符串值（引号内的内容）
            import re
            for match in re.finditer(r'["\']([^"\']*)["\']', line):
                start_pos = match.start()
                end_pos = match.end()
                self.text_widget.tag_add("string", f"{i+1}.{start_pos}", f"{i+1}.{end_pos}")
            
            # 数字
            for match in re.finditer(r'\b\d+\.?\d*\b', line):
                start_pos = match.start()
                end_pos = match.end()
                # 排除注释中的数字
                if not line.strip().startswith('#'):
                    self.text_widget.tag_add("number", f"{i+1}.{start_pos}", f"{i+1}.{end_pos}")
            
            # 布尔值
            for match in re.finditer(r'\b(true|false|True|False)\b', line):
                start_pos = match.start()
                end_pos = match.end()
                if not line.strip().startswith('#'):
                    self.text_widget.tag_add("boolean", f"{i+1}.{start_pos}", f"{i+1}.{end_pos}")
    
    def show_error(self, message):
        """显示错误消息"""
        messagebox.showerror("错误", message)
    
    def show_info(self, message):
        """显示信息消息"""
        messagebox.showinfo("信息", message)

