#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для модуля конфигурации.
"""

import json
import os
import tempfile

from src.utils.config import Config


def test_config_defaults() -> None:
    """Тест значений по умолчанию."""
    config = Config()
    assert config.timeout == 5
    assert config.retries == 3
    assert config.openrouter_model == "openai/gpt-3.5-turbo"
    assert config.cache_dir == "cache"
    assert config.output_dir == "output"


def test_config_save_load() -> None:
    """Тест сохранения и загрузки конфигурации."""
    config = Config()
    config.bookmarks_file = "test.json"
    config.timeout = 10
    config.retries = 5
    config.openrouter_api_key = "test_key"
    config.openrouter_model = "test_model"
    config.cache_dir = "test_cache"
    config.output_dir = "test_output"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        config.save(f.name)
        loaded_config = Config().load(f.name)
        
        assert loaded_config.bookmarks_file == config.bookmarks_file
        assert loaded_config.timeout == config.timeout
        assert loaded_config.retries == config.retries
        assert loaded_config.openrouter_api_key == config.openrouter_api_key
        assert loaded_config.openrouter_model == config.openrouter_model
        assert loaded_config.cache_dir == config.cache_dir
        assert loaded_config.output_dir == config.output_dir

    os.unlink(f.name)
