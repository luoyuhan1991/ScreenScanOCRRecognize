"""
GUI状态管理模块
管理GUI界面状态（窗口大小、位置等，不涉及业务配置）
"""

import json
from pathlib import Path
from typing import Optional, Dict


class GUIStateManager:
    """管理GUI界面状态（窗口大小、位置等，不涉及业务配置）"""
    
    def __init__(self, state_file='config/gui_state.json'):
        """
        初始化状态管理器
        
        Args:
            state_file: 状态文件路径
        """
        self.state_file = Path(state_file)
        self.state = {
            'window': {
                'width': 800,
                'height': 700,
                'x': None,
                'y': None,
                'geometry': None
            },
            'ui': {
                'last_banlist_path': 'docs/banlist.txt',
                'log_level_filter': 'INFO',
                'log_max_lines': 1000,
                'remember_roi': True,  # 是否记住ROI区域，默认选中
                'saved_roi': None  # 保存的ROI区域 (x1, y1, x2, y2)
            }
        }
        self.load_state()
    
    def load_state(self):
        """加载GUI状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    loaded_state = json.load(f)
                    # 合并状态（保留默认值）
                    self._merge_state(self.state, loaded_state)
            except Exception as e:
                import warnings
                warnings.warn(f"无法加载GUI状态文件 {self.state_file}: {e}，使用默认状态")
    
    def _merge_state(self, default: Dict, override: Dict):
        """递归合并状态字典"""
        for key, value in override.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_state(default[key], value)
            else:
                default[key] = value
    
    def save_state(self):
        """保存GUI状态"""
        try:
            # 确保目录存在
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存状态到文件
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            import warnings
            warnings.warn(f"保存GUI状态文件失败: {e}")
            return False
    
    def get_window_geometry(self) -> Optional[str]:
        """
        获取窗口位置和大小
        
        Returns:
            窗口几何字符串，格式: "widthxheight+x+y"，如果未设置返回None
        """
        window = self.state.get('window', {})
        width = window.get('width', 800)
        height = window.get('height', 700)
        x = window.get('x')
        y = window.get('y')
        
        if x is not None and y is not None:
            return f"{width}x{height}+{x}+{y}"
        elif 'geometry' in window and window['geometry']:
            return window['geometry']
        else:
            return f"{width}x{height}"
    
    def set_window_geometry(self, x: int, y: int, width: int, height: int):
        """
        保存窗口位置和大小
        
        Args:
            x: 窗口X坐标
            y: 窗口Y坐标
            width: 窗口宽度
            height: 窗口高度
        """
        if 'window' not in self.state:
            self.state['window'] = {}
        
        self.state['window']['x'] = x
        self.state['window']['y'] = y
        self.state['window']['width'] = width
        self.state['window']['height'] = height
        self.state['window']['geometry'] = f"{width}x{height}+{x}+{y}"
    
    def get_last_banlist_path(self) -> str:
        """获取上次使用的banlist文件路径"""
        return self.state.get('ui', {}).get('last_banlist_path', 'docs/banlist.txt')
    
    def set_last_banlist_path(self, path: str):
        """设置上次使用的banlist文件路径"""
        if 'ui' not in self.state:
            self.state['ui'] = {}
        self.state['ui']['last_banlist_path'] = path
    
    def get_log_max_lines(self) -> int:
        """获取日志最大行数"""
        return self.state.get('ui', {}).get('log_max_lines', 1000)
    
    def set_log_max_lines(self, max_lines: int):
        """设置日志最大行数"""
        if 'ui' not in self.state:
            self.state['ui'] = {}
        self.state['ui']['log_max_lines'] = max_lines
    
    def get_remember_roi(self) -> bool:
        """获取是否记住ROI区域"""
        return self.state.get('ui', {}).get('remember_roi', True)
    
    def set_remember_roi(self, remember: bool):
        """设置是否记住ROI区域"""
        if 'ui' not in self.state:
            self.state['ui'] = {}
        self.state['ui']['remember_roi'] = remember
    
    def get_saved_roi(self) -> Optional[tuple]:
        """获取保存的ROI区域"""
        roi = self.state.get('ui', {}).get('saved_roi')
        if roi and isinstance(roi, list) and len(roi) == 4:
            return tuple(roi)
        return None
    
    def set_saved_roi(self, roi: Optional[tuple]):
        """设置保存的ROI区域"""
        if 'ui' not in self.state:
            self.state['ui'] = {}
        if roi:
            self.state['ui']['saved_roi'] = list(roi)
        else:
            self.state['ui']['saved_roi'] = None

