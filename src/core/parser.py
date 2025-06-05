import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)


class Bookmark(BaseModel):
    """
    Модель закладки.

    Attributes:
        name: Название закладки
        url: URL закладки
        date_added: Дата добавления в формате timestamp
        parent_id: ID родительской папки
        id: Уникальный ID закладки
        type: Тип (url/folder)
        children: Дочерние элементы для папок
    """

    name: str
    url: Optional[HttpUrl] = None
    date_added: Optional[str] = None
    parent_id: Optional[str] = None
    id: str
    type: str
    children: Optional[List["Bookmark"]] = None


class BookmarksParser:
    """
    Парсер закладок из Chrome/Yandex Browser.

    Attributes:
        bookmarks_file: Путь к файлу закладок
        max_file_size: Максимальный размер файла в байтах (10 МБ)
    """

    def __init__(self, bookmarks_file: str, max_file_size: int = 10 * 1024 * 1024):
        """
        Инициализация парсера.

        Args:
            bookmarks_file: Путь к файлу закладок
            max_file_size: Максимальный размер файла в байтах
        """
        self.bookmarks_file = Path(bookmarks_file)
        self.max_file_size = max_file_size

    def validate_file(self) -> bool:
        """
        Проверяет валидность файла закладок.

        Returns:
            bool: True если файл валиден
        """
        if not self.bookmarks_file.exists():
            logger.error(f"Bookmarks file not found: {self.bookmarks_file}")
            return False

        if self.bookmarks_file.stat().st_size > self.max_file_size:
            logger.error(f"Bookmarks file too large: {self.bookmarks_file}")
            return False

        return True

    def parse_bookmark(self, bookmark_data: Dict[str, Any]) -> Bookmark:
        """
        Парсит одну закладку из JSON.

        Args:
            bookmark_data: Данные закладки из JSON

        Returns:
            Bookmark: Объект закладки
        """
        children = None
        if "children" in bookmark_data:
            children = [
                self.parse_bookmark(child) for child in bookmark_data["children"]
            ]

        return Bookmark(
            name=bookmark_data.get("name", ""),
            url=bookmark_data.get("url"),
            date_added=bookmark_data.get("date_added"),
            parent_id=bookmark_data.get("parent_id"),
            id=bookmark_data.get("id", ""),
            type=bookmark_data.get("type", "url"),
            children=children,
        )

    def parse(self) -> Optional[Bookmark]:
        """
        Парсит файл закладок.

        Returns:
            Optional[Bookmark]: Корневая закладка или None при ошибке
        """
        if not self.validate_file():
            return None

        try:
            with open(self.bookmarks_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "roots" not in data:
                logger.error("Invalid bookmarks file format: no roots")
                return None

            # Парсим корневую папку
            root_data = data["roots"]["bookmark_bar"]
            return self.parse_bookmark(root_data)

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing bookmarks file: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing bookmarks: {e}")
            return None

    def get_all_urls(self, bookmark: Optional[Bookmark] = None) -> List[str]:
        """
        Получает список всех URL из закладок.

        Args:
            bookmark: Закладка для обработки (по умолчанию None)

        Returns:
            List[str]: Список URL
        """
        if bookmark is None:
            bookmark = self.parse()
            if bookmark is None:
                return []

        urls = []
        if bookmark.url:
            urls.append(str(bookmark.url))

        if bookmark.children:
            for child in bookmark.children:
                urls.extend(self.get_all_urls(child))

        return urls
