"""
@file: markdown_generator.py
@description: Модуль для генерации markdown файлов из URL
@dependencies: requests, beautifulsoup4, pathlib, html2text
@created: 2024-03-20
"""

from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag, NavigableString
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarkdownGenerator:
    """Класс для генерации markdown из HTML."""
    
    def __init__(self):
        """Инициализация генератора markdown."""
        self.logger = logging.getLogger(__name__)

    def generate_markdown(self, url: str, save_path: str) -> Optional[Path]:
        """
        Генерирует markdown из HTML страницы.

        Args:
            url: URL страницы
            save_path: Путь для сохранения

        Returns:
            Path: Путь к сохраненному файлу или None
        """
        self.logger.info(f"[MARKDOWN] generate_markdown: {url}, save_path: {save_path}")

        try:
            # Получаем HTML
            html = self._fetch_content(url)
            if not html:
                return None

            # Создаем BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Получаем заголовок и метаданные
            title = self._get_title(soup)
            description = self._get_meta(soup, "description")
            keywords = self._get_meta(soup, "keywords")

            # Формируем markdown
            markdown = []
            
            # Добавляем заголовок
            markdown.append(f"# {title}\n")
            
            # Добавляем метаданные
            if description:
                markdown.append(f"> {description}\n")
            if keywords:
                markdown.append(f"**Ключевые слова**: {keywords}\n")
            markdown.append(f"**Источник**: [{url}]({url})\n")

            # Обрабатываем основной контент
            body = soup.find('body')
            if body and isinstance(body, Tag):
                markdown.append(self._process_content(body, url))

            # Сохраняем результат
            save_path_obj = Path(save_path)
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            save_path_obj.write_text('\n'.join(markdown))

            return save_path_obj

        except Exception as e:
            self.logger.error(f"[MARKDOWN] Ошибка при генерации markdown: {e}")
            return None

    def _get_meta(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        """
        Получает значение мета-тега.

        Args:
            soup: BeautifulSoup объект
            name: Имя мета-тега

        Returns:
            str: Значение мета-тега или None
        """
        meta = soup.find('meta', {'name': name})
        if meta and isinstance(meta, Tag):
            content = meta.get('content')
            if content and isinstance(content, str):
                return content.strip()
        return None

    def _process_content(self, element: Tag, base_url: str) -> str:
        """
        Обрабатывает HTML элемент и возвращает markdown.

        Args:
            element: HTML элемент
            base_url: Базовый URL

        Returns:
            str: Markdown
        """
        result = []
        for child in element.children:
            if isinstance(child, NavigableString):
                if str(child).strip():
                    result.append(str(child).strip())
            elif isinstance(child, Tag):
                if child.name == 'table':
                    result.append(self._process_table(child))
                elif child.name in ('ul', 'ol'):
                    result.append(self._process_list(child))
                elif child.name == 'a':
                    result.append(self._process_link(child, base_url))
                elif child.name == 'img':
                    result.append(self._process_image(child, base_url))
                elif child.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                    result.append(self._process_heading(child))
                elif child.name == 'p':
                    result.append(self._process_paragraph(child, base_url))
                elif child.name == 'br':
                    result.append('\n')
                elif child.name == 'hr':
                    result.append('---\n')
                elif child.name in ('strong', 'b'):
                    result.append(f"**{self._process_content(child, base_url)}**")
                elif child.name in ('em', 'i'):
                    result.append(f"*{self._process_content(child, base_url)}*")
                elif child.name == 'code':
                    result.append(f"`{self._process_content(child, base_url)}`")
                elif child.name == 'pre':
                    result.append(f"```\n{self._process_content(child, base_url)}\n```")
                else:
                    result.append(self._process_content(child, base_url))

        return ' '.join(result)

    def _process_table(self, table: Tag) -> str:
        """
        Обрабатывает HTML таблицу.

        Args:
            table: HTML таблица

        Returns:
            str: Markdown таблица
        """
        result = []
        headers = []
        rows = []

        # Обрабатываем заголовки
        header_row = table.find('tr')
        if header_row and isinstance(header_row, Tag):
            for th in header_row.find_all(['th', 'td']):
                headers.append(th.get_text().strip())

        # Обрабатываем строки
        for tr in table.find_all('tr')[1:]:
            row = []
            for td in tr.find_all('td'):
                row.append(td.get_text().strip())
            if row:
                rows.append(row)

        # Формируем markdown таблицу
        if headers:
            result.append('| ' + ' | '.join(headers) + ' |')
            result.append('| ' + ' | '.join(['---' for _ in headers]) + ' |')

        for row in rows:
            result.append('| ' + ' | '.join(row) + ' |')

        return '\n'.join(result) + '\n\n'

    def _process_list(self, list_tag: Tag, level: int = 0, parent_counter: Optional[int] = None) -> str:
        """
        Обрабатывает HTML список.

        Args:
            list_tag: HTML список
            level: Уровень вложенности
            parent_counter: Счетчик родительского списка

        Returns:
            str: Markdown список
        """
        result = []
        is_ordered = list_tag.name == 'ol'
        counter = 1

        # Учитываем атрибут start для нумерованных списков
        if is_ordered:
            start_attr = list_tag.get('start')
            if start_attr and isinstance(start_attr, str):
                try:
                    counter = int(start_attr)
                except (ValueError, TypeError):
                    pass

        for item in list_tag.find_all('li', recursive=False):
            # Обрабатываем вложенные списки
            nested_lists = []
            for nested_list in item.find_all(['ul', 'ol'], recursive=False):
                nested_content = self._process_list(nested_list, level + 1, counter if is_ordered else None)
                nested_lists.append(nested_content)
                nested_list.extract()  # Удаляем вложенный список из родительского элемента

            # Получаем текст элемента списка
            item_text = item.get_text().strip()

            # Формируем строку списка
            indent = '  ' * level  # Используем 2 пробела для отступа
            if is_ordered:
                result.append(f"{indent}{counter}. {item_text}")
                counter += 1
            else:
                result.append(f"{indent}- {item_text}")

            # Добавляем вложенные списки
            for nested_list in nested_lists:
                result.append(nested_list.rstrip())


    def _process_link(self, link: Tag, base_url: str) -> str:
        """
        Обрабатывает HTML ссылку.

        Args:
            link: HTML ссылка
            base_url: Базовый URL

        Returns:
            str: Markdown ссылка
        """
        href = link.get('href', '')
        if not href or not isinstance(href, str):
            return link.get_text()

        # Пропускаем javascript: ссылки
        if href.startswith('javascript:'):
            return link.get_text()

        # Обрабатываем относительные ссылки
        if not href.startswith(('http://', 'https://', 'mailto:', 'tel:', '#')):
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            else:
                href = urljoin(base_url, href)

        text = link.get_text().strip() or href
        return f"[{text}]({href})"

    def _process_image(self, img: Tag, base_url: str) -> str:
        """
        Обрабатывает HTML изображение.

        Args:
            img: HTML изображение
            base_url: Базовый URL

        Returns:
            str: Markdown изображение
        """
        src = img.get('src', '')
        if not src or not isinstance(src, str):
            return ''

        # Обрабатываем относительные пути
        if not src.startswith(('http://', 'https://')):
            if src.startswith('/'):
                parsed_base = urlparse(base_url)
                src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
            else:
                src = urljoin(base_url, src)

        alt = img.get('alt', 'image')
        if not isinstance(alt, str):
            alt = 'image'
        return f"![{alt}]({src})"

    def _process_heading(self, heading: Tag) -> str:
        """
        Обрабатывает HTML заголовок.

        Args:
            heading: HTML заголовок

        Returns:
            str: Markdown заголовок
        """
        level = int(heading.name[1])
        return f"{'#' * level} {heading.get_text().strip()}\n\n"

    def _process_paragraph(self, paragraph: Tag, base_url: str) -> str:
        """
        Обрабатывает HTML параграф.

        Args:
            paragraph: HTML параграф
            base_url: Базовый URL

        Returns:
            str: Markdown параграф
        """
        return f"{self._process_content(paragraph, base_url)}\n\n"

    def _get_title(self, soup: BeautifulSoup) -> str:
        """
        Получает заголовок страницы.

        Args:
            soup: BeautifulSoup объект

        Returns:
            str: Заголовок страницы
        """
        title = soup.find('title')
        if title:
            return title.get_text().strip()
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        return "Untitled"

    def _fetch_content(self, url: str) -> Optional[str]:
        """
        Получает HTML контент по URL.

        Args:
            url: URL страницы

        Returns:
            str: HTML контент или None
        """
        self.logger.info(f"[MARKDOWN] _fetch_content: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"[MARKDOWN] Ошибка при получении контента: {e}")
            return None
