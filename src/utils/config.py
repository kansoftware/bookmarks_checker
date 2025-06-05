#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль конфигурации приложения.
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List, Union


@dataclass
class Config:
    """Класс конфигурации приложения."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации.
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        # Базовые настройки
        self.timeout: int = 5
        self.retries: int = 3
        self.threads: int = 4
        self.browser: str = "Chrome"
        self.bookmarks_file: Optional[str] = None
        self.max_redirects: int = 5
        
        # Настройки LLM
        self.openrouter_api_key: Optional[str] = None
        self.openrouter_model: str = "openai/gpt-3.5-turbo"
        self.llm_request_delay: int = 1000  # Задержка между запросами в миллисекундах
        self.available_models: List[str] = [
            "gpt-3.5-turbo",
            "gpt-4",
            "claude-3-opus",
            "claude-3-sonnet",
            "gemini-pro"
        ]
        
        # Пути
        self._cache_dir: Optional[Path] = "cache"
        self._output_dir: Optional[Path] = "output"
        self.results_dir: Optional[str] = None
        
        # Настройки обработки контента
        self.save_images: bool = True
        self.save_links: bool = True
        self.extract_metadata: bool = True
        self.max_content_size: int = 10 * 1024 * 1024  # 10 MB
        self.allowed_content_types: List[str] = [
            "text/html",
            "text/plain",
            "application/xhtml+xml"
        ]
        self.excluded_domains: List[str] = []
        self.user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Загрузка конфигурации из файла, если указан путь
        self.config_path = config_path
        if config_path:
            self.load(config_path)

    def save(self, path: str) -> None:
        """
        Сохраняет конфигурацию в файл.
        
        Args:
            path: Путь к файлу конфигурации
        """
        config = {
            "bookmarks_file": self.bookmarks_file,
            "timeout": self.timeout,
            "retries": self.retries,
            "openrouter_api_key": self.openrouter_api_key,
            "openrouter_model": self.openrouter_model,
            "cache_dir": str(self.cache_dir) if self.cache_dir else None,
            "output_dir": str(self.output_dir) if self.output_dir else None
        }
        
        with open(path, 'w') as f:
            json.dump(config, f, indent=4)

    def load(self, path: str) -> 'Config':
        """
        Загружает конфигурацию из файла.
        
        Args:
            path: Путь к файлу конфигурации
            
        Returns:
            Config: Объект конфигурации
        """
        with open(path) as f:
            config = json.load(f)
            
        self.bookmarks_file = config.get("bookmarks_file")
        self.timeout = config.get("timeout", 5)
        self.retries = config.get("retries", 3)
        self.openrouter_api_key = config.get("openrouter_api_key")
        self.openrouter_model = config.get("openrouter_model")
        
        cache_dir = config.get("cache_dir")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
        output_dir = config.get("output_dir")
        self.output_dir = Path(output_dir) if output_dir else None
        
        return self

    def update_from_ui(self, timeout: int, retries: int, threads: int, browser: str) -> None:
        """
        Обновление конфигурации из пользовательского интерфейса.
        
        Args:
            timeout: Таймаут запросов
            retries: Количество попыток
            threads: Количество потоков
            browser: Браузер
        """
        self.timeout = timeout
        self.retries = retries
        self.threads = threads
        self.browser = browser

    @property
    def cache_dir(self) -> Optional[Path]:
        """Директория для кэша."""
        return self._cache_dir

    @cache_dir.setter
    def cache_dir(self, value: Optional[Union[str, Path]]) -> None:
        """
        Устанавливает директорию для кэша.
        
        Args:
            value: Путь к директории или None
        """
        if value is None:
            self._cache_dir = None
        else:
            self._cache_dir = Path(value)

    @property
    def output_dir(self) -> Optional[Path]:
        """Директория для результатов."""
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: Optional[Union[str, Path]]) -> None:
        """
        Устанавливает директорию для результатов.
        
        Args:
            value: Путь к директории или None
        """
        if value is None:
            self._output_dir = None
        else:
            self._output_dir = Path(value)
