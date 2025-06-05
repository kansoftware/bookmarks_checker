import json
from datetime import datetime
from pathlib import Path

import pytest

from src.core.parser import Bookmark, BookmarksParser


@pytest.fixture
def sample_bookmarks_file(tmp_path):
    """Создает тестовый файл закладок."""
    bookmarks = {
        "roots": {
            "bookmark_bar": {
                "name": "Bookmarks Bar",
                "id": "1",
                "type": "folder",
                "children": [
                    {
                        "name": "Test Bookmark",
                        "url": "https://example.com",
                        "id": "2",
                        "type": "url",
                        "date_added": "1234567890",
                    },
                    {
                        "name": "Test Folder",
                        "id": "3",
                        "type": "folder",
                        "children": [
                            {
                                "name": "Nested Bookmark",
                                "url": "https://test.com",
                                "id": "4",
                                "type": "url",
                                "date_added": "1234567891",
                            }
                        ],
                    },
                ],
            }
        }
    }

    bookmarks_file = tmp_path / "bookmarks.json"
    with open(bookmarks_file, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f)

    return bookmarks_file


def test_parser_initialization():
    """Тест инициализации парсера."""
    parser = BookmarksParser("test.json")
    assert parser.bookmarks_file == Path("test.json")
    assert parser.max_file_size == 10 * 1024 * 1024


def test_validate_file_not_exists():
    """Тест валидации несуществующего файла."""
    parser = BookmarksParser("nonexistent.json")
    assert not parser.validate_file()


def test_validate_file_too_large(tmp_path):
    """Тест валидации слишком большого файла."""
    large_file = tmp_path / "large.json"
    large_file.write_bytes(b"0" * (11 * 1024 * 1024))  # 11 MB

    parser = BookmarksParser(str(large_file))
    assert not parser.validate_file()


def test_parse_bookmark():
    """Тест парсинга одной закладки."""
    parser = BookmarksParser("test.json")
    bookmark_data = {
        "name": "Test",
        "url": "https://example.com",
        "id": "1",
        "type": "url",
        "date_added": "1234567890",
    }

    bookmark = parser.parse_bookmark(bookmark_data)
    assert isinstance(bookmark, Bookmark)
    assert bookmark.name == "Test"
    assert str(bookmark.url).rstrip("/") == "https://example.com"
    assert bookmark.id == "1"
    assert bookmark.type == "url"


def test_parse_bookmark_with_children():
    """Тест парсинга закладки с дочерними элементами."""
    parser = BookmarksParser("test.json")
    bookmark_data = {
        "name": "Folder",
        "id": "1",
        "type": "folder",
        "children": [
            {"name": "Child", "url": "https://example.com", "id": "2", "type": "url"}
        ],
    }

    bookmark = parser.parse_bookmark(bookmark_data)
    assert isinstance(bookmark, Bookmark)
    assert bookmark.name == "Folder"
    assert bookmark.type == "folder"
    assert len(bookmark.children) == 1
    assert bookmark.children[0].name == "Child"


def test_parse_file(sample_bookmarks_file):
    """Тест парсинга файла закладок."""
    parser = BookmarksParser(str(sample_bookmarks_file))
    root = parser.parse()

    assert isinstance(root, Bookmark)
    assert root.name == "Bookmarks Bar"
    assert root.type == "folder"
    assert len(root.children) == 2

    # Проверяем первую закладку
    assert root.children[0].name == "Test Bookmark"
    assert str(root.children[0].url).rstrip("/") == "https://example.com"

    # Проверяем вложенную папку
    folder = root.children[1]
    assert folder.name == "Test Folder"
    assert len(folder.children) == 1
    assert folder.children[0].name == "Nested Bookmark"


def test_get_all_urls(sample_bookmarks_file):
    """Тест получения всех URL."""
    parser = BookmarksParser(str(sample_bookmarks_file))
    urls = parser.get_all_urls()

    assert len(urls) == 2
    assert any(url.rstrip("/") == "https://example.com" for url in urls)
    assert any(url.rstrip("/") == "https://test.com" for url in urls)


def test_parse_invalid_json(tmp_path):
    """Тест парсинга некорректного JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("invalid json")

    parser = BookmarksParser(str(invalid_file))
    assert parser.parse() is None


def test_parse_missing_roots(tmp_path):
    """Тест парсинга файла без roots."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text('{"invalid": "format"}')

    parser = BookmarksParser(str(invalid_file))
    assert parser.parse() is None


def test_parse_bookmarks(sample_bookmarks_file):
    """Тест парсинга закладок."""
    parser = BookmarksParser(str(sample_bookmarks_file))
    root = parser.parse()

    assert isinstance(root, Bookmark)
    assert root.name == "Bookmarks Bar"
    assert root.type == "folder"
    assert len(root.children) == 2

    # Проверяем первую закладку
    assert root.children[0].name == "Test Bookmark"
    assert str(root.children[0].url).rstrip("/") == "https://example.com"

    # Проверяем вложенную папку
    folder = root.children[1]
    assert folder.name == "Test Folder"
    assert len(folder.children) == 1
    assert folder.children[0].name == "Nested Bookmark"


def test_invalid_file():
    """Тест обработки невалидного файла."""
    parser = BookmarksParser("nonexistent.json")
    assert not parser.validate_file()
    assert parser.parse() is None


def test_get_urls(sample_bookmarks_file):
    """Тест получения URL."""
    parser = BookmarksParser(str(sample_bookmarks_file))
    urls = parser.get_all_urls()

    assert len(urls) == 2
    assert any(url.rstrip("/") == "https://example.com" for url in urls)
    assert any(url.rstrip("/") == "https://test.com" for url in urls)


def test_get_folders(sample_bookmarks_file):
    """Тест получения папок."""
    parser = BookmarksParser(str(sample_bookmarks_file))
    root = parser.parse()

    # Получаем все папки рекурсивно
    def get_folders(bookmark):
        folders = []
        if bookmark.type == "folder":
            folders.append(bookmark)
            for child in bookmark.children:
                folders.extend(get_folders(child))
        return folders

    folders = get_folders(root)
    assert len(folders) == 2  # Bookmarks Bar и Test Folder
    assert folders[0].name == "Bookmarks Bar"
    assert folders[1].name == "Test Folder"


def test_get_bookmarks_by_folder(sample_bookmarks_file):
    """Тест получения закладок по папке."""
    parser = BookmarksParser(str(sample_bookmarks_file))
    root = parser.parse()

    # Находим папку Test Folder
    test_folder = None
    for child in root.children:
        if child.name == "Test Folder":
            test_folder = child
            break

    assert test_folder is not None
    assert len(test_folder.children) == 1
    assert test_folder.children[0].name == "Nested Bookmark"
    assert str(test_folder.children[0].url).rstrip("/") == "https://test.com"
