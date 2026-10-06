import logging
import subprocess
from typing import ClassVar, Self, cast

from src.downloader.config import Config

DEFAULT_LOGGERS = [
        (logging.INFO, "info", "[%(levelname)s] %(message)s", True),
        (logging.ERROR, "error", "[%(asctime)s] [%(levelname)s] %(message)s", True),
        (logging.DEBUG, "debug", "[%(levelname)s] %(message)s", False),
]


class Logger:
    """Singleton for managing loggers."""
    _instance: ClassVar[Logger | None] = None

    _loggers: dict[str, logging.Logger]

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_instance()
        return cast(Self, cls._instance)

    def _init_instance(self):
        self._loggers = {}

        log_dir = Config.root() / Config.get("log_dir")
        log_dir.mkdir(parents=True, exist_ok=True)

        for level, name, format, is_stdout in DEFAULT_LOGGERS:
            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.propagate = False
            logger.handlers.clear()

            file_handler = logging.FileHandler(log_dir / f"{name}.log")
            file_handler.setFormatter(logging.Formatter(format))

            if is_stdout:
                stream_handler = logging.StreamHandler()
                stream_handler.setFormatter(logging.Formatter(format))
                logger.addHandler(stream_handler)

            logger.addHandler(file_handler)

            self._loggers[name] = logger
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger by name."""
        return cls()._loggers[name]

    @classmethod
    def info(cls, message: str) -> None:
        """Log an info message."""
        cls.get_logger("info").info(message)

    @classmethod
    def error(cls, message: str) -> None:
        """Log an error message."""
        cls.get_logger("error").error(message)

    @classmethod
    def exception(cls, message: str) -> None:
        """Log an exception message."""
        cls.get_logger("error").exception(message)

    @classmethod
    def debug(cls, message: str) -> None:
        """Log a debug message."""
        cls.get_logger("debug").debug(message)

    @classmethod
    def debug_process_result(cls, result: subprocess.CompletedProcess, label: str | None = None) -> None:
        """Log the result of a subprocess call at debug level."""
        label = f"[{label}] " if label else ""
        cls.debug(f"{label}{result.stdout}\n{result.stderr}\nReturn code: {result.returncode}")

