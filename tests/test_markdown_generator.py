"""
@file: test_markdown_generator.py
@description: Тесты для модуля генерации markdown файлов
@dependencies: pytest, requests-mock
@created: 2024-03-20
"""

import pytest
from pathlib import Path
import requests_mock
from src.markdown_generator import MarkdownGenerator

@pytest.fixture
def generator():
    return MarkdownGenerator()

@pytest.fixture
def tmp_path_factory(tmp_path):
    return lambda x: tmp_path / x

def test_generate_markdown_success(generator, tmp_path_factory):
    """Тест успешной генерации markdown файла."""
    test_url = "http://example.com"
    test_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Header</h1>
            <p>Test paragraph</p>
        </body>
    </html>
    """
    save_path = tmp_path_factory("test.md")
    
    with requests_mock.Mocker() as m:
        m.get(test_url, text=test_html)
        result = generator.generate_markdown(test_url, save_path)
        
        assert result is not None
        assert result.exists()
        content = result.read_text(encoding='utf-8')
        assert "# Test Page" in content
        assert "# Main Header" in content
        assert "Test paragraph" in content

def test_generate_markdown_failed_fetch(generator, tmp_path_factory):
    """Тест обработки ошибки при загрузке URL."""
    test_url = "http://example.com"
    save_path = tmp_path_factory("test.md")
    
    with requests_mock.Mocker() as m:
        m.get(test_url, status_code=404)
        result = generator.generate_markdown(test_url, save_path)
        assert result is None
        assert not save_path.exists()

def test_create_nested_directories(generator, tmp_path_factory):
    """Тест создания вложенных директорий."""
    test_url = "http://example.com"
    test_html = "<html><head><title>Test</title></head><body><p>Content</p></body></html>"
    save_path = tmp_path_factory("nested/dirs/test.md")
    
    with requests_mock.Mocker() as m:
        m.get(test_url, text=test_html)
        result = generator.generate_markdown(test_url, save_path)
        
        assert result is not None
        assert result.exists()
        assert result.parent.exists()

def test_convert_complex_html(generator, tmp_path_factory):
    """Тест конвертации сложного HTML."""
    test_url = "http://example.com"
    test_html = """
    <html>
        <head><title>Complex Page</title></head>
        <body>
            <h1>Main Header</h1>
            <p>First paragraph</p>
            <h2>Subheader</h2>
            <p>Second paragraph</p>
            <h3>Sub-subheader</h3>
            <p>Third paragraph</p>
        </body>
    </html>
    """
    save_path = tmp_path_factory("complex.md")
    
    with requests_mock.Mocker() as m:
        m.get(test_url, text=test_html)
        result = generator.generate_markdown(test_url, save_path)
        
        assert result is not None
        content = result.read_text(encoding='utf-8')
        assert "# Complex Page" in content
        assert "# Main Header" in content
        assert "## Subheader" in content
        assert "### Sub-subheader" in content
        assert "First paragraph" in content
        assert "Second paragraph" in content
        assert "Third paragraph" in content 