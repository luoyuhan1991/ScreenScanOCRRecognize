"""
配置管理模块
支持从YAML配置文件读取配置，并提供默认配置
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class Config:
    """配置管理类"""
    
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        # 默认配置
        default_config = {
            'scan': {
                'interval_seconds': 5,
                'roi_padding': 10,
                'enable_roi': False
            },
            'ocr': {
                'default_engine': 'paddle',
                'languages': ['ch', 'en'],
                'min_confidence': 0.15,
                'use_preprocessing': True,
                'easyocr': {
                    'canvas_size': 1920,
                    'mag_ratio': 1.5,
                    'dynamic_params': True
                },
                'preprocessing': {
                    'clahe_clip_limit': 3.0,
                    'clahe_tile_size': 8,
                    'min_width': 640,
                    'max_width': 2560,
                    'enable_clahe': True,
                    'enable_sharpen': True,
                    'fast_mode': False
                }
            },
            'gpu': {
                'auto_detect': False,
                'force_cpu': False,
                'force_gpu': True
            },
            'files': {
                'output_dir': 'output',
                'banlist_file': 'docs/banlist.txt'
            },
            'cleanup': {
                'enabled': True,
                'max_age_hours': 1,
                'interval_minutes': 10
            },
            'matching': {
                'enabled': True,
                'display_duration': 3,
                'position': 'center'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/app.log',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'max_bytes': 10485760,
                'backup_count': 5
            }
        }
        
        # 尝试加载配置文件
        config_file = Path('config.yaml')
        if config_file.exists() and YAML_AVAILABLE:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f) or {}
                    # 合并配置（文件配置覆盖默认配置）
                    self._config = self._merge_config(default_config, file_config)
            except Exception as e:
                import warnings
                warnings.warn(f"无法加载配置文件 {config_file}: {e}，使用默认配置")
                self._config = default_config
        elif config_file.exists() and not YAML_AVAILABLE:
            import warnings
            warnings.warn(f"配置文件 {config_file} 存在，但PyYAML未安装，使用默认配置。请运行: pip install pyyaml")
            self._config = default_config
        else:
            self._config = default_config
    
    def _merge_config(self, default: Dict, override: Dict) -> Dict:
        """递归合并配置字典"""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的路径
        
        Args:
            key_path: 配置路径，如 'scan.interval_seconds'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any):
        """
        设置配置值
        
        Args:
            key_path: 配置路径
            value: 配置值
        """
        keys = key_path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def save(self, config_file: Optional[str] = None):
        """
        保存配置到YAML文件
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径 'config.yaml'
        """
        if not YAML_AVAILABLE:
            import warnings
            warnings.warn("PyYAML未安装，无法保存配置文件。请运行: pip install pyyaml")
            return False
        
        if config_file is None:
            config_file = Path('config.yaml')
        else:
            config_file = Path(config_file)
        
        try:
            # 确保目录存在
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存配置到文件
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            return True
        except Exception as e:
            import warnings
            warnings.warn(f"保存配置文件失败: {e}")
            return False
    
    def reload(self):
        """重新加载配置文件"""
        self._load_config()


# 全局配置实例
config = Config()

