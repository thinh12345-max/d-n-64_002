"""Configuration loader - loads config once and provides access to validated config."""
from pathlib import Path
from typing import Optional
from .schema import Config, load_config


_config: Optional[Config] = None


def get_config(config_path: str = "config/config.yaml") -> Config:
    """
    Get the configuration instance.
    Loads and validates config on first call, then returns cached instance.
    """
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def reload_config(config_path: str = "config/config.yaml") -> Config:
    """Force reload configuration from file."""
    global _config
    _config = load_config(config_path)
    return _config


def reset_config() -> None:
    """Reset the cached configuration (useful for testing)."""
    global _config
    _config = None