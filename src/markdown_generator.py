"""
@file: markdown_generator.py
@description: Модуль для генерации markdown файлов из URL
@dependencies: requests, beautifulsoup4, pathlib
@created: 2024-03-20
"""

import os
from pathlib import Path
from typing import Optional
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarkdownGenerator:
    """Класс для генерации markdown файлов из URL с сохранением иерархии."""
    
    def __init__(self):
        """Инициализация генератора markdown файлов."""
        self.session = requests.Session()
    
    def generate_markdown(self, url: str, save_path: Path) -> Optional[Path]:
        """
        Генерирует markdown файл из содержимого URL и сохраняет его по указанному пути.
        
        Args:
            url: URL для загрузки контента
            save_path: Путь для сохранения файла
            
        Returns:
            Path: Путь к сохраненному файлу или None в случае ошибки
        """
        try:
            # Загружаем контент
            content = self._fetch_content(url)
            if not content:
                return None
                
            # Создаем markdown
            markdown_content = self._convert_to_markdown(content)
            
            # Создаем директории если нужно
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем файл
            save_path.write_text(markdown_content, encoding='utf-8')
            logger.info(f"Markdown файл успешно сохранен: {save_path}")
            
            return save_path
            
        except Exception as e:
            logger.error(f"Ошибка при генерации markdown для {url}: {str(e)}")
            return None
    
    def _fetch_content(self, url: str) -> Optional[str]:
        """
        Загружает контент с указанного URL.
        
        Args:
            url: URL для загрузки
            
        Returns:
            str: HTML контент или None в случае ошибки
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Ошибка при загрузке {url}: {str(e)}")
            return None
    
    def _convert_to_markdown(self, html_content: str) -> str:
        """
        Конвертирует HTML контент в markdown формат.
        
        Args:
            html_content: HTML контент для конвертации
            
        Returns:
            str: Markdown контент
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Получаем заголовок страницы
        title = soup.title.string if soup.title else "Без заголовка"
        
        # Базовая конвертация - можно расширить для более сложной обработки
        content = []
        content.append(f"# {title}\n")
        
        # Добавляем основной контент
        main_content = []
        for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if tag.name.startswith('h'):
                level = int(tag.name[1])
                main_content.append(f"{'#' * level} {tag.get_text().strip()}\n")
            else:
                main_content.append(f"{tag.get_text().strip()}\n")
        
        content.extend(main_content)
        
        return "\n".join(content) 