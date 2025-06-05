#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль конфигурации приложения.
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List


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
        self.cache_dir: str = "cache"
        self.output_dir: str = "output"
        
        # Загрузка конфигурации из файла, если указан путь
        self.config_path = config_path
        if config_path:
            self.load(config_path)

    def save(self, path: str) -> None:
        """
        Сохранение конфигурации в файл.
        
        Args:
            path: Путь к файлу конфигурации
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

    def load(self, path: str) -> None:
        """
        Загрузка конфигурации из файла.
        
        Args:
            path: Путь к файлу конфигурации
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        except FileNotFoundError:
            # Если файл не найден, используем значения по умолчанию
            pass
        except Exception as e:
            print(f"Ошибка при загрузке конфигурации: {e}")

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
