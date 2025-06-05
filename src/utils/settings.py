#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с настройками приложения.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

class Settings:
    """Класс для работы с настройками приложения."""
    
    def __init__(self):
        """Инициализация настроек."""
        self.config_dir = os.path.expanduser("~/.config")
        self.config_file = os.path.join(self.config_dir, "BookmarksChecker.json")
        self.settings = self.load_settings()
        
    def load_settings(self) -> Dict[str, Any]:
        """
        Загрузка настроек из файла.
        
        Returns:
            Dict[str, Any]: Словарь с настройками
        """
        if not os.path.exists(self.config_file):
            return self._get_default_settings()
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка при загрузке настроек: {e}")
            return self._get_default_settings()
    
    def save_settings(self) -> None:
        """Сохранение настроек в файл."""
        try:
            # Создаем директорию, если она не существует
            os.makedirs(self.config_dir, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении настроек: {e}")
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Получение настроек по умолчанию.
        
        Returns:
            Dict[str, Any]: Словарь с настройками по умолчанию
        """
        return {
            "window": {
                "size": [800, 600],
                "position": [100, 100]
            },
            "checker": {
                "timeout": 5,
                "retries": 3,
                "threads": 4,
                "browser": "Chrome"
            },
            "llm": {
                "model": "gpt-3.5-turbo",
                "api_key": "",
                "base_url": "https://api.openai.com/v1"
            }
        }
    
    def get_window_settings(self) -> Dict[str, Any]:
        """Получение настроек окна."""
        return self.settings.get("window", self._get_default_settings()["window"])
    
    def get_checker_settings(self) -> Dict[str, Any]:
        """Получение настроек проверки."""
        return self.settings.get("checker", self._get_default_settings()["checker"])
    
    def get_llm_settings(self) -> Dict[str, Any]:
        """Получение настроек LLM."""
        return self.settings.get("llm", self._get_default_settings()["llm"])
    
    def update_window_settings(self, settings: Dict[str, Any]) -> None:
        """Обновление настроек окна."""
        self.settings["window"] = settings
        self.save_settings()
    
    def update_checker_settings(self, settings: Dict[str, Any]) -> None:
        """Обновление настроек проверки."""
        self.settings["checker"] = settings
        self.save_settings()
    
    def update_llm_settings(self, settings: Dict[str, Any]) -> None:
        """Обновление настроек LLM."""
        self.settings["llm"] = settings
        self.save_settings() 