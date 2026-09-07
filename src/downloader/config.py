import json
import os
from pathlib import Path
from typing import Any


class Config:
    """
    Singleton for storing key-value configuration settings.
    """
    _instance = None
    _config_data: dict[str, Any] | None = None
    _config_path: Path = Path(os.getcwd()) / "config.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _init(self):
        if self._config_data is not None:
            return

        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_path}")

        with self._config_path.open("r", encoding="utf-8") as f:
            self._config_data = json.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Returns the value associated with a key.
        If it does not exist, default or None is returned.
        """
        self._init()

        if self._config_data is None:
            raise RuntimeError("Config data is not loaded.")

        return self._config_data.get(key, default)

    @property
    def data(self) -> dict[str, Any]:
        """
        The config data as a dictionary.
        """
        self._init()

        if self._config_data is None:
            raise RuntimeError("Config data is not loaded.")

        return self._config_data

