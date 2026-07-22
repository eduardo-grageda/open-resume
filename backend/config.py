from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
CONFIG_PATH = DATA_DIR / "config.json"

DEFAULT_CONFIG = {
    "openrouter_api_key": "",
    "openrouter_base_url": "https://openrouter.ai/api/v1",
    "openrouter_model": "deepseek/deepseek-v4-pro",
    "storage_backend": "json",
    "mongo_uri": "mongodb://localhost:27017",
    "search_provider": "serpapi",
    "search_api_key": "",
}


class AppConfig(BaseModel):
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-v4-pro"
    storage_backend: str = "json"
    mongo_uri: str = "mongodb://localhost:27017"
    search_provider: str = "serpapi"
    search_api_key: str = ""


def _env_override(config: AppConfig) -> AppConfig:
    env_map = {
        "openrouter_api_key": "OPENROUTER_API_KEY",
        "openrouter_base_url": "OPENROUTER_BASE_URL",
        "openrouter_model": "OPENROUTER_MODEL",
        "storage_backend": "STORAGE_BACKEND",
        "mongo_uri": "MONGO_URI",
        "search_provider": "SEARCH_PROVIDER",
        "search_api_key": "SEARCH_API_KEY",
    }
    data = config.model_dump()
    for field_name, env_var in env_map.items():
        env_val = os.environ.get(env_var)
        if env_val:
            data[field_name] = env_val
    return AppConfig(**data)


def load_config() -> AppConfig:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            raw = json.load(f)
        config = AppConfig(**{k: v for k, v in raw.items() if k in AppConfig.model_fields})
    else:
        config = AppConfig(**DEFAULT_CONFIG)
    return _env_override(config)


def save_config(config: AppConfig) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


def config_file_exists() -> bool:
    return CONFIG_PATH.is_file()