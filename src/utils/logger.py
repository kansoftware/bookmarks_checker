#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль настройки логирования.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """Класс для логирования."""

    def __init__(self, log_dir: Path, name: str = "bookmarks_checker") -> None:
        self.log_dir = log_dir
        self.name = name
        self.logger: Optional[logging.Logger] = None

    def setup(self) -> None:
        """Настраивает логгер."""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True)

        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)

        # Форматтер
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Файловый обработчик
        file_handler = logging.FileHandler(
            self.log_dir / f"{self.name}.log", encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def get_logger(self) -> logging.Logger:
        """Возвращает настроенный логгер."""
        if not self.logger:
            self.setup()
        return self.logger


def setup_logger(name: Optional[str] = None, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Настройка логгера."""
    logger = logging.getLogger(name or __name__)

    if not logger.handlers:
        logger.setLevel(level)

        # Форматтер для логов
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Хендлер для вывода в консоль
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Хендлер для записи в файл, если указан log_file
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
