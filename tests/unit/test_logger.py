#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для модуля логирования.
"""

import logging
import os
import tempfile

from src.utils.logger import setup_logger


def test_logger_setup() -> None:
    """Тест настройки логгера."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        log_file = f.name
    try:
        logger = setup_logger(name="bookmarks_checker", log_file=log_file)
        assert logger.name == "bookmarks_checker"
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    finally:
        os.unlink(log_file)


def test_logger_custom_file() -> None:
    """Тест логгера с пользовательским файлом."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        log_file = f.name

    try:
        logger = setup_logger(log_file=log_file)
        logger.info("Test message")

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Test message" in content
    finally:
        os.unlink(log_file)


def test_logger_custom_level() -> None:
    """Тест логгера с пользовательским уровнем."""
    logger = setup_logger()
    # Очищаем хендлеры, чтобы уровень мог быть установлен
    logger.handlers.clear()
    logger = setup_logger(level=logging.DEBUG)
    assert logger.level == logging.DEBUG
