import json
import os
from pathlib import Path
from typing import Any, ClassVar, Self, cast


class Config:
    """Singleton for storing key-value configuration settings."""

    _instance: ClassVar[Config | None] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_instance()
        return cast(Self, cls._instance)
    
    @staticmethod
    def _get_root() -> Path:
        if "PROJECT_ROOT" in os.environ:
            return Path(os.environ["PROJECT_ROOT"])

        current_dir = Path(__file__).resolve().parent
        for parent in [current_dir, *current_dir.parents]:
            if (parent / "pyproject.toml").exists():
                return parent

        raise RuntimeError("Could not determine project root.");

    def _init_instance(self) -> None:
        self._root = Config._get_root()
        self._config_path = self._root / "config.json"

        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self._config_path}"
            )

        with self._config_path.open("r", encoding="utf-8") as f:
            self._config_data = json.load(f)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration key by value."""
        return cls()._config_data.get(key, default)

    @classmethod
    def data(cls) -> dict[str, Any]:
        """Get the entire configuration data as a dictionary."""
        return cls()._config_data

    @classmethod
    def root(cls) -> Path:
        """Get the project root directory."""
        return cls()._root

