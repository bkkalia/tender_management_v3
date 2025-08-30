# core/config_manager.py
import json
import os
import logging
from typing import Dict, Any, Optional

# Define constants directly in this file
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")

logger = logging.getLogger(__name__)

class BaseConfig:
    """Base class for configuration management."""
    def __init__(self, config_path: Optional[str] = None, default_config: Optional[Dict[str, Any]] = None):
        self.config_path = config_path
        self.default_config = default_config if default_config is not None else {}
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from a JSON file or return defaults."""
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys are present
                    # Loaded config values take precedence
                    merged_config = {**self.default_config, **loaded_config}
                    logger.info(f"Configuration loaded from {self.config_path}")
                    return merged_config
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from {self.config_path}. Using defaults.")
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}. Using defaults.")
        else:
            if self.config_path:
                logger.warning(f"Config file {self.config_path} not found. Using defaults and attempting to save.")
            else:
                logger.info("No config path provided. Using in-memory defaults.")

        # If using defaults and a path was intended, try to save them.
        if self.config_path and self.default_config:
            self.save_config(self.default_config) # Save defaults if file didn't exist

        return self.default_config.copy() # Return a copy of defaults

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value (in memory)."""
        self.config[key] = value

    def save_config(self, data_to_save: Optional[Dict[str, Any]] = None) -> bool:
        """Save the current configuration to the file."""
        if not self.config_path:
            logger.warning("Cannot save config: No config_path specified.")
            return False
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            data = data_to_save if data_to_save is not None else self.config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            return False

class GlobalConfig(BaseConfig):
    """Manages global application settings."""
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        # Initialize logger first
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        default_settings = {
            "app_title": "Tender Search Utility V3",
            "default_data_folder": "./data/input_excel_files/",
            "merged_data_folder": "./data/merged_data/",
            "log_level": "INFO",
            "last_used_folders": [],
            "merger_unique_key": "Tender ID", # Example default
            "merger_critical_fields": ["Closing Date", "Status", "Value"] # Example default
        }
        super().__init__(config_path, default_settings)
        os.makedirs(self.get("default_data_folder", "./data/input_excel_files/"), exist_ok=True)
        os.makedirs(self.get("merged_data_folder", "./data/merged_data/"), exist_ok=True)

    def save_config(self, data_to_save: Optional[Dict[str, Any]] = None) -> bool:
        """Save the current configuration to file."""
        if not self.config_path:
            logger.error("Cannot save config: No config_path specified.")
            return False
            
        try:
            # Ensure the directory exists
            config_dir = os.path.dirname(self.config_path)
            if config_dir:  # Only create if dirname returns a non-empty string
                os.makedirs(config_dir, exist_ok=True)
            
            # Use provided data or current config
            config_to_save = data_to_save if data_to_save is not None else self.config
            
            # Normalize paths before saving
            normalized_config = config_to_save.copy()
            for key in ["default_data_folder", "merged_data_folder"]:
                if key in normalized_config:
                    path = normalized_config[key]
                    if path:
                        # Convert to absolute path and normalize
                        normalized_config[key] = os.path.abspath(path).replace("\\", "/")
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(normalized_config, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

class FeatureConfig(BaseConfig):
    """Manages feature-specific configurations."""
    def __init__(self, feature_name: str, global_config: GlobalConfig, default_config: Optional[Dict[str, Any]] = None):
        # Example: store feature configs in a sub-directory or with a prefix
        config_dir = os.path.join(os.path.dirname(global_config.config_path or DEFAULT_CONFIG_PATH), "feature_configs")
        os.makedirs(config_dir, exist_ok=True)
        config_file_path = os.path.join(config_dir, f"{feature_name}_config.json")
        super().__init__(config_file_path, default_config)
        self.feature_name = feature_name