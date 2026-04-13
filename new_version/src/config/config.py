import os
import yaml


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._loaded = False
        return cls._instance

    def load(self, path=None):
        if path is None:
            # 查找 config/config.yaml，相对于 new_version/ 根目录
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'config', 'config.yaml'
            )
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self._data = yaml.safe_load(f) or {}
        self._path = path
        self._loaded = True

    def get(self, dotted_key, default=None):
        """点号路径访问: config.get('scan.interval_seconds', 2.0)"""
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


config = Config()
