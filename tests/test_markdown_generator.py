"""
@file: test_markdown_generator.py
@description: Тесты для модуля генерации markdown
@dependencies: pytest, requests_mock
@created: 2024-03-21
"""

import pytest
import requests_mock
import requests

from src.core.markdown_generator import MarkdownGenerator

@pytest.fixture
def generator():
    """Фикстура для создания генератора markdown."""
    return MarkdownGenerator()

@pytest.fixture
def tmp_path_factory(tmp_path):
    """Фикстура для создания временных директорий."""
    class Factory:
        def mktemp(self, name):
            path = tmp_path / name
            path.mkdir(parents=True, exist_ok=True)
            return path
    return Factory()

def test_basic_conversion(generator, tmp_path_factory):
    """Тест базовой конвертации HTML в markdown."""
    html = """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
            <meta name="keywords" content="test, keywords">
        </head>
        <body>
            <h1>Main Title</h1>
            <p>Test paragraph</p>
            <h2>Subtitle</h2>
            <p>Another paragraph</p>
        </body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        url = "http://test.com/page"
        m.get(url, text=html)
        
        save_path = tmp_path_factory.mktemp("test") / "test.md"
        result = generator.generate_markdown(url, save_path)
        
        assert result is not None
        assert result.exists()
        content = result.read_text()
        
        assert "# Test Page" in content
        assert "> Test description" in content
        assert "**Ключевые слова**: test, keywords" in content
        assert "# Main Title" in content
        assert "## Subtitle" in content
        assert "Test paragraph" in content
        assert "Another paragraph" in content

def test_table_conversion(generator, tmp_path_factory):
    """Тест конвертации таблиц."""
    html = """
    <html>
        <head><title>Table Test</title></head>
        <body>
            <table>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><td>Cell 1</td><td>Cell 2</td></tr>
                <tr><td>Cell 3</td><td>Cell 4</td></tr>
            </table>
        </body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        url = "http://test.com/table"
        m.get(url, text=html)
        
        save_path = tmp_path_factory.mktemp("test") / "table.md"
        result = generator.generate_markdown(url, save_path)
        
        assert result is not None
        assert result.exists()
        content = result.read_text()
        
        assert "| Header 1 | Header 2 |" in content
        assert "| --- | --- |" in content
        assert "| Cell 1 | Cell 2 |" in content
        assert "| Cell 3 | Cell 4 |" in content

def test_list_conversion(generator, tmp_path_factory):
    """Тест конвертации списков."""
    html = """
    <html>
        <head><title>List Test</title></head>
        <body>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
                <li>Item 3</li>
            </ul>
            <ol>
                <li>First</li>
                <li>Second</li>
                <li>Third</li>
            </ol>
        </body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        url = "http://test.com/list"
        m.get(url, text=html)
        
        save_path = tmp_path_factory.mktemp("test") / "list.md"
        result = generator.generate_markdown(url, save_path)
        
        assert result is not None
        assert result.exists()
        content = result.read_text()
        
        assert "- Item 1" in content
        assert "- Item 2" in content
        assert "- Item 3" in content
        assert "1. First" in content
        assert "2. Second" in content
        assert "3. Third" in content

def test_link_conversion(generator, tmp_path_factory):
    """Тест конвертации ссылок."""
    html = """
    <html>
        <head><title>Link Test</title></head>
        <body>
            <a href="http://example.com">External Link</a>
            <a href="/relative">Relative Link</a>
            <a href="#anchor">Anchor Link</a>
            <a href="javascript:void(0)">JavaScript Link</a>
        </body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        url = "http://test.com/links"
        m.get(url, text=html)
        
        save_path = tmp_path_factory.mktemp("test") / "links.md"
        result = generator.generate_markdown(url, save_path)
        
        assert result is not None
        assert result.exists()
        content = result.read_text()
        
        assert "[External Link](http://example.com)" in content
        assert "[Relative Link](http://test.com/relative)" in content
        assert "javascript:void(0)" not in content

def test_image_conversion(generator, tmp_path_factory):
    """Тест конвертации изображений."""
    html = """
    <html>
        <head><title>Image Test</title></head>
        <body>
            <img src="http://example.com/image.jpg" alt="External Image">
            <img src="/local/image.png" alt="Local Image">
            <img src="relative/image.gif">
        </body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        url = "http://test.com/images"
        m.get(url, text=html)
        
        save_path = tmp_path_factory.mktemp("test") / "images.md"
        result = generator.generate_markdown(url, save_path)
        
        assert result is not None
        assert result.exists()
        content = result.read_text()
        
        assert "![External Image](http://example.com/image.jpg)" in content
        assert "![Local Image](http://test.com/local/image.png)" in content
        assert "![image](http://test.com/relative/image.gif)" in content

def test_error_handling(generator, tmp_path_factory):
    """Тест обработки ошибок."""
    with requests_mock.Mocker() as m:
        # Тест недоступного URL
        url = "http://test.com/404"
        m.get(url, status_code=404)
        
        save_path = tmp_path_factory.mktemp("test") / "error.md"
        result = generator.generate_markdown(url, save_path)
        
        assert result is None
        assert not save_path.exists()
        
        # Тест таймаута
        url = "http://test.com/timeout"
        m.get(url, exc=requests.exceptions.Timeout)
        
        result = generator.generate_markdown(url, save_path)
        assert result is None
        
        # Тест некорректного HTML
        url = "http://test.com/invalid"
        m.get(url, text="<invalid>")
        
        result = generator.generate_markdown(url, save_path)
        assert result is not None  # Должен обработать некорректный HTML
        assert save_path.exists()
