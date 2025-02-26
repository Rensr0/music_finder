import json
import os
from pathlib import Path
from typing import Dict, Any
from PyQt5.QtCore import QByteArray

class Settings:
    """配置管理类"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".music_finder"
        self.config_file = self.config_dir / "settings.json"
        self.defaults = {
            "last_directory": "",
            "check_method": "按文件名",
            "min_size": 0,
            "max_depth": 0,
            "window_geometry": None,
            "case_sensitive": False,
            "title_only": True
        }
        self.settings = self.load()
        
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if self.config_file.exists():
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        loaded_settings = json.load(f)
                        
                    # 处理特殊类型的数据
                    settings = self.defaults.copy()
                    for key, value in loaded_settings.items():
                        if key == 'window_geometry' and isinstance(value, str):
                            # 将 base64 字符串转回 QByteArray
                            settings[key] = QByteArray.fromBase64(value.encode('utf-8'))
                        else:
                            settings[key] = value
                            
                    return settings
                    
                except json.JSONDecodeError as e:
                    print(f"配置文件格式错误: {e}")
                    # 如果配置文件损坏，备份并创建新的
                    backup_file = self.config_file.with_suffix('.json.bak')
                    self.config_file.rename(backup_file)
                    print(f"已将损坏的配置文件备份为: {backup_file}")
                    
        except Exception as e:
            print(f"加载配置失败: {e}")
            
        # 返回默认配置
        return self.defaults.copy()
        
    def save(self) -> None:
        """保存配置"""
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # 处理 QByteArray 类型的数据
            settings_to_save = {}
            for key, value in self.settings.items():
                if isinstance(value, QByteArray):
                    # 将 QByteArray 转换为 base64 字符串
                    settings_to_save[key] = str(value.toBase64(), 'utf-8')
                else:
                    settings_to_save[key] = value
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存配置失败: {e}")
            
    def get(self, key: str, default=None) -> Any:
        """获取配置项"""
        return self.settings.get(key, default)
        
    def set(self, key: str, value: Any):
        """设置配置项"""
        self.settings[key] = value
        self.save() 