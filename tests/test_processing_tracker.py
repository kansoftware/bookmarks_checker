"""
@file: test_processing_tracker.py
@description: Тесты для модуля отслеживания процесса обработки
@dependencies: pytest
@created: 2024-03-21
"""

import json
import pytest
from pathlib import Path
import threading
from typing import Dict

from src.core.processing_tracker import ProcessingTracker

class TestProcessingTracker:
    @pytest.fixture
    def tracker(self, tmp_path_factory):
        """Фикстура для создания трекера с временной директорией."""
        tmp_dir = tmp_path_factory.mktemp("tracker")
        return ProcessingTracker(tmp_dir)
    
    def test_init(self, tracker):
        """Тест инициализации трекера."""
        assert tracker.processing_file.exists()
        data = self._read_data(tracker.processing_file)
        assert "urls" in data
        assert isinstance(data["urls"], dict)
        assert len(data["urls"]) == 0
    
    def test_add_url(self, tracker):
        """Тест добавления URL."""
        url = "http://test.com"
        title = "Test Page"
        
        tracker.add_url(url, title)
        
        url_info = tracker.get_url_info(url)
        assert url_info is not None
        assert url_info["title"] == title
        assert url_info["status"] == "pending"
    
    def test_update_check_result(self, tracker):
        """Тест обновления результата проверки."""
        url = "http://test.com"
        tracker.add_url(url, "Test")
        
        tracker.update_check_result(url, True)
        url_info = tracker.get_url_info(url)
        assert url_info["status"] == "checked"
        assert url_info["check_result"] is True
        
        tracker.update_check_result(url, False, "Test error")
        url_info = tracker.get_url_info(url)
        assert url_info["check_result"] is False
        assert url_info["error"] == "Test error"
    
    def test_update_markdown_path(self, tracker):
        """Тест обновления пути к markdown файлу."""
        url = "http://test.com"
        tracker.add_url(url, "Test")
        
        markdown_path = Path("test.md")
        tracker.update_markdown_path(url, markdown_path)
        
        url_info = tracker.get_url_info(url)
        assert url_info["status"] == "completed"
        assert url_info["markdown_path"] == str(markdown_path)
        
        tracker.update_markdown_path(url, None)
        url_info = tracker.get_url_info(url)
        assert url_info["status"] == "failed"
        assert url_info["markdown_path"] is None
    
    def test_get_pending_urls(self, tracker):
        """Тест получения списка необработанных URL."""
        # Добавляем URL в разных состояниях
        tracker.add_url("http://test1.com", "Test 1")  # pending
        
        tracker.add_url("http://test2.com", "Test 2")  # checked, success
        tracker.update_check_result("http://test2.com", True)
        
        tracker.add_url("http://test3.com", "Test 3")  # checked, failed
        tracker.update_check_result("http://test3.com", False)
        
        tracker.add_url("http://test4.com", "Test 4")  # completed
        tracker.update_check_result("http://test4.com", True)
        tracker.update_markdown_path("http://test4.com", Path("test.md"))
        
        pending = tracker.get_pending_urls()
        assert len(pending) == 1
        assert "http://test2.com" in pending
    
    def test_thread_safety(self, tracker):
        """Тест потокобезопасности."""
        urls = [(f"http://test{i}.com", f"Test {i}") for i in range(10)]
        
        def add_urls(start, end):
            for i in range(start, end):
                url, title = urls[i]
                tracker.add_url(url, title)
                tracker.update_check_result(url, True)
                tracker.update_markdown_path(url, Path(f"test_{i}.md"))
        
        threads = []
        chunk_size = len(urls) // 4
        for i in range(0, len(urls), chunk_size):
            t = threading.Thread(
                target=add_urls,
                args=(i, min(i + chunk_size, len(urls)))
            )
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        all_urls = tracker.get_all_urls()
        assert len(all_urls) == len(urls)
        
        for i, (url, title) in enumerate(urls):
            url_info = tracker.get_url_info(url)
            assert url_info is not None
            assert url_info["title"] == title
            assert url_info["status"] == "completed"
            assert url_info["markdown_path"] == str(Path(f"test_{i}.md"))
    
    @staticmethod
    def _read_data(file_path: Path) -> Dict:
        """Вспомогательный метод для чтения данных из файла."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

@pytest.fixture
def tmp_path_factory(tmp_path):
    """Фикстура для создания временных директорий."""
    class Factory:
        def mktemp(self, name):
            path = tmp_path / name
            path.mkdir(parents=True, exist_ok=True)
            return path
    return Factory()

@pytest.fixture
def tracker(tmp_path_factory):
    """Фикстура для создания трекера."""
    results_dir = tmp_path_factory.mktemp("results")
    return ProcessingTracker(results_dir)

def test_init(tracker, tmp_path_factory):
    """Тест инициализации трекера."""
    # Проверяем создание директории
    assert tracker.results_dir.exists()
    
    # Проверяем создание файла
    assert tracker.processing_file.exists()
    
    # Проверяем начальное содержимое
    with open(tracker.processing_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert "urls" in data
        assert "last_update" in data
        assert isinstance(data["urls"], dict)
        assert len(data["urls"]) == 0

def test_add_url(tracker):
    """Тест добавления URL."""
    url = "http://test.com"
    title = "Test Page"
    
    tracker.add_url(url, title)
    
    # Проверяем добавление
    url_info = tracker.get_url_info(url)
    assert url_info is not None
    assert url_info["title"] == title
    assert url_info["status"] == "pending"
    assert url_info["check_result"] is None
    assert url_info["check_time"] is None
    assert url_info["markdown_path"] is None
    assert url_info["error"] is None
    
    # Проверяем, что повторное добавление не изменяет данные
    tracker.add_url(url, "New Title")
    url_info = tracker.get_url_info(url)
    assert url_info["title"] == title

def test_update_check_result(tracker):
    """Тест обновления результата проверки."""
    url = "http://test.com"
    tracker.add_url(url, "Test")
    
    # Обновляем результат
    tracker.update_check_result(url, True)
    
    # Проверяем обновление
    url_info = tracker.get_url_info(url)
    assert url_info["status"] == "checked"
    assert url_info["check_result"] is True
    assert url_info["check_time"] is not None
    assert url_info["error"] is None
    
    # Проверяем обновление с ошибкой
    tracker.update_check_result(url, False, "Test error")
    url_info = tracker.get_url_info(url)
    assert url_info["check_result"] is False
    assert url_info["error"] == "Test error"

def test_update_markdown_path(tracker):
    """Тест обновления пути к markdown файлу."""
    url = "http://test.com"
    tracker.add_url(url, "Test")
    
    # Обновляем путь
    markdown_path = tracker.results_dir / "test.md"
    tracker.update_markdown_path(url, markdown_path)
    
    # Проверяем обновление
    url_info = tracker.get_url_info(url)
    assert url_info["status"] == "completed"
    assert url_info["markdown_path"] == str(markdown_path)
    
    # Проверяем обновление с ошибкой
    tracker.update_markdown_path(url, None)
    url_info = tracker.get_url_info(url)
    assert url_info["status"] == "failed"
    assert url_info["markdown_path"] is None

def test_get_pending_urls(tracker):
    """Тест получения списка необработанных URL."""
    # Добавляем URL в разных состояниях
    tracker.add_url("http://test1.com", "Test 1")  # pending
    
    tracker.add_url("http://test2.com", "Test 2")  # checked, success
    tracker.update_check_result("http://test2.com", True)
    
    tracker.add_url("http://test3.com", "Test 3")  # checked, failed
    tracker.update_check_result("http://test3.com", False)
    
    tracker.add_url("http://test4.com", "Test 4")  # completed
    tracker.update_check_result("http://test4.com", True)
    tracker.update_markdown_path("http://test4.com", Path("test.md"))
    
    # Получаем список необработанных
    pending = tracker.get_pending_urls()
    assert len(pending) == 1
    assert "http://test2.com" in pending

def test_reset_failed(tracker):
    """Тест сброса неудачных проверок."""
    # Добавляем URL с разными статусами
    urls = {
        "http://test1.com": ("Test 1", "failed"),
        "http://test2.com": ("Test 2", "completed"),
        "http://test3.com": ("Test 3", "failed")
    }
    
    for url, (title, status) in urls.items():
        tracker.add_url(url, title)
        if status == "failed":
            tracker.update_check_result(url, False, "Test error")
            tracker.update_markdown_path(url, None)
        else:
            tracker.update_check_result(url, True)
            tracker.update_markdown_path(url, Path("test.md"))
    
    # Сбрасываем неудачные
    tracker.reset_failed()
    
    # Проверяем результаты
    for url, (title, status) in urls.items():
        url_info = tracker.get_url_info(url)
        if status == "failed":
            assert url_info["status"] == "pending"
            assert url_info["check_result"] is None
            assert url_info["check_time"] is None
            assert url_info["markdown_path"] is None
            assert url_info["error"] is None
        else:
            assert url_info["status"] == "completed"
            assert url_info["markdown_path"] is not None

def test_thread_safety(tmp_path_factory):
    """Тест потокобезопасности."""
    results_dir = tmp_path_factory.mktemp("results")
    tracker = ProcessingTracker(results_dir)
    
    # Создаем множество URL
    urls = [
        (f"http://test{i}.com", f"Test {i}")
        for i in range(20)  # Уменьшаем количество URL
    ]
    
    # Функция для добавления URL
    def add_urls(start, end):
        for i in range(start, end):
            url, title = urls[i]
            tracker.add_url(url, title)
            tracker.update_check_result(url, True)
            tracker.update_markdown_path(url, Path(f"test_{i}.md"))
    
    # Запускаем потоки
    threads = []
    chunk_size = len(urls) // 4
    for i in range(0, len(urls), chunk_size):
        t = threading.Thread(
            target=add_urls,
            args=(i, min(i + chunk_size, len(urls)))
        )
        threads.append(t)
        t.start()
    
    # Ждем завершения
    for t in threads:
        t.join()
    
    # Проверяем результаты
    all_urls = tracker.get_all_urls()
    assert len(all_urls) == len(urls)
    
    for i, (url, title) in enumerate(urls):
        url_info = tracker.get_url_info(url)
        assert url_info is not None
        assert url_info["title"] == title
        assert url_info["status"] == "completed"
        assert url_info["markdown_path"] == str(Path(f"test_{i}.md")) 