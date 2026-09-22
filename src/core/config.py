"""
配置管理器
"""
import json
import os
from typing import Dict, Any
from pathlib import Path


class Config:
    """配置管理类"""

    def __init__(self):
        self.config_dir = Path.home() / ".smart_converter"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "taobao": {
                "app_key": "",
                "app_secret": "",
                "pid": "",
                "adzone_id": "",
                "enabled": False,
            },
            "ai": {
                "anthropic_api_key": "",
                "model": "claude-fable-5",
                "enabled": False,
            },
            "general": {
                "theme": "dark",  # dark/light/system
                "language": "zh_CN",
                "auto_start": False,
                "minimize_to_tray": True,
            },
            "batch": {
                "max_concurrent": 10,
                "auto_analyze": True,
                "default_style": "通用",
            },
            "qq": {
                "forward_group": "",  # 默认转发群
            },
            "jd": {
                "app_key": "",
                "app_secret": "",
                "pid": "",
                "enabled": False,
            },
            "monitor": {
                "enabled": False,
                "target_group": "",  # 目标群（自己的群）
                "auto_send": False,  # 转链后自动发送
                "check_interval": 2,  # 检测间隔（秒）
            },
            "cloud_collect": {
                "haodanku_apikey": "",  # 好单库 API key
                "resources": [],  # 采集资源列表
                "group_mappings": {},  # 群-资源映射 {群名: [资源ID列表]}
                "auto_collect_enabled": False,  # 是否启用自动采集
                "auto_send_enabled": False,  # 是否自动发送
                "collect_interval": 30,  # 采集间隔（分钟）
            }
        }

    def save(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()

    def is_taobao_configured(self) -> bool:
        """检查淘宝配置是否完整"""
        return all([
            self.get('taobao.app_key'),
            self.get('taobao.app_secret'),
            self.get('taobao.pid'),
            self.get('taobao.adzone_id'),
        ])

    def is_ai_configured(self) -> bool:
        """检查 AI 配置是否完整"""
        return bool(self.get('ai.anthropic_api_key'))
