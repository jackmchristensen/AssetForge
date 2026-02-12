import json

from pathlib import Path
from typing import Any

_settings_cache: dict[str, Any] | None = None

def load_settings() -> dict[str, Any]:
    """Load settings from config/settings.json. Caches the result for subsequent calls."""
    global _settings_cache

    if _settings_cache is not None:
        return _settings_cache

    config_path = Path(__file__).parent / "settings.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Settings file not found at {config_path}")

    with open(config_path, "r") as f:
        _settings_cache = json.load(f)

    assert _settings_cache is not None

    return _settings_cache


def get_setting(key_path: str, default: Any = None) -> Any:
    """Get a setting using dot notation. 
    
    Example: 'unreal_engine.version'
    """

    settings = load_settings()
    keys = key_path.split(".")

    value = settings
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def reload_settings() -> None:
    """Reload settings from the JSON file, clearing the cache."""

    global _settings_cache
    _settings_cache = None
    load_settings()


def save_setting(key_path: str, value: Any) -> None:
    """Save a setting using dot notation and persist to settings.json.

    Example: save_setting('naming_conventions.mesh_prefix', 'SM_')
    """

    global _settings_cache

    settings = load_settings()
    keys = key_path.split(".")

    current = settings
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}

        current = current[k]

        if not isinstance(current, dict):
            raise ValueError(f"Cannot navigate to {key_path}: '{k}' is not a dict")

    current[keys[-1]] = value

    config_path = Path(__file__).parent / "settings.json"
    temp_path = config_path.with_suffix('.tmp')

    with open(temp_path, 'w') as f:
        json.dump(settings, f, indent=2)

    temp_path.replace(config_path)

    _settings_cache = settings
