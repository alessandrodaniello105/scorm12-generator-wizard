"""
Configuration management for SCORM Generator.
Handles saving and loading user preferences.
"""
import json
import os
from pathlib import Path
from typing import Optional, List, Dict


class Config:
    """Manages application configuration and user preferences."""
    
    def __init__(self):
        """Initialize config with default values."""
        # Get app data directory
        if os.name == 'nt':  # Windows
            app_data = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        else:  # Linux/Mac
            app_data = Path.home() / '.config'
        
        self.config_dir = app_data / 'SCORM_Wrapper_Wizard'
        self.config_file = self.config_dir / 'config.json'
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default values
        self.defaults = {
            'last_output_dir': '',
            'last_video_type': 'vimeo',
            'recent_csv_files': [],
            'auto_open_folder': False,
            'theme': 'light_blue'
        }
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    merged = self.defaults.copy()
                    merged.update(config)
                    return merged
            except (json.JSONDecodeError, IOError):
                return self.defaults.copy()
        return self.defaults.copy()
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except IOError:
            pass  # Silently fail if can't save
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        """Set a configuration value and save."""
        self._config[key] = value
        self._save_config()
    
    def get_last_output_dir(self) -> str:
        """Get last used output directory."""
        return self.get('last_output_dir', '')
    
    def set_last_output_dir(self, path: str):
        """Set last used output directory."""
        self.set('last_output_dir', path)
    
    def get_last_video_type(self) -> str:
        """Get last selected video type."""
        return self.get('last_video_type', 'vimeo')
    
    def set_last_video_type(self, video_type: str):
        """Set last selected video type."""
        self.set('last_video_type', video_type)
    
    def get_recent_csv_files(self, max_count: int = 5) -> List[str]:
        """Get recent CSV files."""
        files = self.get('recent_csv_files', [])
        return files[:max_count]
    
    def add_recent_csv_file(self, file_path: str):
        """Add a CSV file to recent list."""
        files = self.get('recent_csv_files', [])
        # Remove if already exists
        if file_path in files:
            files.remove(file_path)
        # Add to beginning
        files.insert(0, file_path)
        # Keep only last 5
        files = files[:5]
        self.set('recent_csv_files', files)
    
    def get_auto_open_folder(self) -> bool:
        """Get auto-open folder setting."""
        return self.get('auto_open_folder', False)
    
    def set_auto_open_folder(self, value: bool):
        """Set auto-open folder setting."""
        self.set('auto_open_folder', value)
