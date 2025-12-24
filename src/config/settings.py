"""
配置管理模块
负责应用配置的加载和保存
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# 配置文件路径
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "../../storage")
CREDENTIALS_FILE = os.path.join(STORAGE_DIR, "credentials.json")
MONITOR_HISTORY_FILE = os.path.join(STORAGE_DIR, "monitor_history.json")
SETTINGS_FILE = os.path.join(STORAGE_DIR, "settings.json")
CACHE_DURATION_HOURS = 6


class ConfigManager:
    """配置管理器"""

    @staticmethod
    def ensure_storage_dir() -> None:
        """确保存储目录存在"""
        if not os.path.exists(STORAGE_DIR):
            os.makedirs(STORAGE_DIR)
            logger.info(f"创建存储目录: {STORAGE_DIR}")

    @staticmethod
    def load_json_file(file_path: str, default: Any = None) -> Any:
        """加载 JSON 文件"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            logger.error(f"加载文件失败 {file_path}: {e}")
            return default

    @staticmethod
    def save_json_file(file_path: str, data: Any, secure: bool = False) -> bool:
        """保存 JSON 文件"""
        try:
            ConfigManager.ensure_storage_dir()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            if secure:
                os.chmod(file_path, 0o600)
            
            return True
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")
            return False


class SettingsManager:
    """应用设置管理器"""

    def __init__(self):
        self._settings = self._load()

    def _load(self) -> dict:
        """加载设置"""
        return ConfigManager.load_json_file(SETTINGS_FILE, {}) or {}

    def save(self) -> bool:
        """保存设置"""
        return ConfigManager.save_json_file(SETTINGS_FILE, self._settings, secure=True)

    def get(self, key: str, default: Any = None) -> Any:
        """获取设置值"""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置值"""
        self._settings[key] = value
        return self.save()

    def update(self, data: dict) -> bool:
        """批量更新设置"""
        self._settings.update(data)
        return self.save()

    def get_all(self) -> dict:
        """获取所有设置"""
        return self._settings.copy()


class MonitorHistoryManager:
    """监控历史记录管理器"""

    @staticmethod
    def load() -> list[str]:
        """加载历史监控房间号"""
        data = ConfigManager.load_json_file(MONITOR_HISTORY_FILE, {'room_ids': []})
        return data.get('room_ids', [])

    @staticmethod
    def save(room_ids: list[str]) -> bool:
        """保存历史监控房间号"""
        # 只保留最近20个记录
        room_ids = room_ids[-20:] if len(room_ids) > 20 else room_ids
        return ConfigManager.save_json_file(MONITOR_HISTORY_FILE, {'room_ids': room_ids})

    @staticmethod
    def add(room_id: str) -> bool:
        """添加房间号到历史记录"""
        history = MonitorHistoryManager.load()
        
        # 如果房间号已存在，先删除
        if room_id in history:
            history.remove(room_id)
        
        # 添加到开头
        history.insert(0, room_id)
        return MonitorHistoryManager.save(history)


# 全局设置实例
app_settings = SettingsManager()
