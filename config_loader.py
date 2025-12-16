"""Configuration file loader and validator."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


class Config:
    """Configuration class with defaults and validation."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize config with defaults or provided values."""
        if config_dict is None:
            config_dict = {}
        
        # Processing settings
        self.threads: int = config_dict.get('threads', 1)
        self.min_improvement_pct: float = config_dict.get('min_improvement_pct', 5.0)
        self.hang_timeout: int = config_dict.get('hang_timeout', 300)  # seconds
        self.recursive: bool = config_dict.get('recursive', True)
        
        # File filtering
        self.skip_extensions: List[str] = config_dict.get('skip_extensions', ['.webp', '.jxl'])
        
        # Conversion settings
        self.jpegxl_quality: int = config_dict.get('jpegxl_quality', 100)
        self.jpegxl_effort: int = config_dict.get('jpegxl_effort', 9)
        self.webp_method: int = config_dict.get('webp_method', 6)
        self.conversion_timeout: int = config_dict.get('conversion_timeout', 300)  # seconds
        self.max_animated_frames: int = config_dict.get('max_animated_frames', 1000)
        
        # Logging and notifications
        self.log_file: str = config_dict.get('log_file', 'image-squisher.log')
        self.enable_notifications: bool = config_dict.get('enable_notifications', True)
        
        # Validate values
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration values."""
        if self.threads < 1:
            raise ValueError("threads must be >= 1")
        if not (0 <= self.min_improvement_pct <= 100):
            raise ValueError("min_improvement_pct must be between 0 and 100")
        if self.hang_timeout < 1:
            raise ValueError("hang_timeout must be >= 1")
        if not (1 <= self.jpegxl_quality <= 100):
            raise ValueError("jpegxl_quality must be between 1 and 100")
        if not (0 <= self.jpegxl_effort <= 9):
            raise ValueError("jpegxl_effort must be between 0 and 9")
        if not (0 <= self.webp_method <= 6):
            raise ValueError("webp_method must be between 0 and 6")
        if self.conversion_timeout < 1:
            raise ValueError("conversion_timeout must be >= 1")
        if self.max_animated_frames < 1:
            raise ValueError("max_animated_frames must be >= 1")
        
        # Normalize skip_extensions to lowercase with dots
        normalized = []
        for ext in self.skip_extensions:
            ext = ext.lower()
            if not ext.startswith('.'):
                ext = '.' + ext
            normalized.append(ext)
        self.skip_extensions = normalized


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to config file. If None, looks for config.json in current directory.
        
    Returns:
        Config object with loaded settings
    """
    if config_path is None:
        config_path = Path('config.json')
    
    # If config file doesn't exist, return default config
    if not config_path.exists():
        return Config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return Config(config_dict)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Error loading config file: {e}")


def create_default_config(config_path: Path) -> None:
    """
    Create a default configuration file.
    
    Args:
        config_path: Path where to create the config file
    """
    default_config = {
        "threads": 1,
        "min_improvement_pct": 5.0,
        "hang_timeout": 300,
        "recursive": True,
        "skip_extensions": [".webp", ".jxl"],
        "jpegxl_quality": 100,
        "jpegxl_effort": 9,
        "webp_method": 6,
        "conversion_timeout": 300,
        "max_animated_frames": 1000,
        "log_file": "image-squisher.log",
        "enable_notifications": True
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)

