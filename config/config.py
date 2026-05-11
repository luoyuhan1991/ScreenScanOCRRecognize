import copy
import os
import yaml

from .defaults import DEFAULT_BANLIST_FILE, DEFAULT_CONFIG

# 其它模块可直接 from config.config import PROJECT_ROOT 复用，避免到处手写 dirname 链。
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _deep_merge(default, override):
    """递归合并：override 覆盖 default；default 中存在但 override 无的 key 保留默认值"""
    if not isinstance(override, dict):
        return override
    result = copy.deepcopy(default) if isinstance(default, dict) else {}
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._loaded = False
        return cls._instance

    def load(self, path=None):
        """加载配置：DEFAULT_CONFIG 兜底，yaml 覆盖（与旧版 Config 行为一致）"""
        if path is None:
            path = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')

        self._data = copy.deepcopy(DEFAULT_CONFIG)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                file_data = yaml.safe_load(f) or {}
                self._data = _deep_merge(self._data, file_data)
        except FileNotFoundError:
            pass

        self._path = path
        self._loaded = True

    def get(self, dotted_key, default=None):
        """点号路径访问: config.get('scan.interval_seconds')；defaults 已合并，通常无需传 default"""
        if not self._loaded:
            self.load()
        keys = dotted_key.split('.')
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, dotted_key, value):
        if not self._loaded:
            self.load()
        keys = dotted_key.split('.')
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def save(self):
        with open(self._path, 'w', encoding='utf-8') as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def reset_to_defaults(self):
        """恢复全量配置到 DEFAULT_CONFIG（不写盘，调用方决定是否 save）。"""
        if not self._loaded:
            self.load()
        self._data = copy.deepcopy(DEFAULT_CONFIG)


config = Config()
