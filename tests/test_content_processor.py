"""
@file: test_content_processor.py
@description: Тесты для модуля обработки контента
@dependencies: pytest, requests_mock
@created: 2024-03-21
"""

import pytest
from pathlib import Path
import threading
import time

import requests_mock
import logging

from src.core.content_processor import ContentProcessor

logger = logging.getLogger(__name__)

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
def processor(tmp_path_factory):
    """Фикстура для создания процессора контента."""
    results_dir = tmp_path_factory.mktemp("results")
    processor = ContentProcessor(results_dir, max_workers=2)
    yield processor
    processor.stop_processing()  # Очищаем ресурсы после теста

def wait_for_processing_start(processor, timeout=5):
    """
    Ожидает запуска обработки.
    
    Args:
        processor: Процессор контента
        timeout: Максимальное время ожидания в секундах
        
    Returns:
        bool: True если обработка запущена, False если превышен таймаут
    """
    logger.info(f"Ожидание запуска обработки (таймаут: {timeout}с)")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if (processor.executor is not None and 
            processor.queue_thread is not None and 
            processor.queue_thread.is_alive() and
            not processor.stop_event.is_set()):
            logger.info("Обработка успешно запущена")
            return True
        time.sleep(0.1)
    logger.error("Таймаут ожидания запуска обработки")
    return False

def wait_for_processing(processor, timeout=5):
    """
    Ожидает завершения обработки всех URL.
    
    Args:
        processor: Процессор контента
        timeout: Максимальное время ожидания в секундах
        
    Returns:
        bool: True если обработка завершена, False если превышен таймаут
    """
    logger.info(f"Ожидание завершения обработки (таймаут: {timeout}с)")
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Проверяем все URL
        all_completed = True
        urls = processor.tracker.get_all_urls()
        logger.info(f"Проверка статусов URL ({len(urls)} шт.)")
        
        for url, url_info in urls.items():
            status = url_info["status"]
            logger.info(f"URL {url}: статус {status}")
            if status not in ["completed", "error"]:
                all_completed = False
                break
        
        if all_completed:
            logger.info("Все URL обработаны")
            return True
            
        time.sleep(0.1)
    
    logger.error("Таймаут ожидания завершения обработки")
    return False

def test_add_url(processor):
    """Тест добавления и обработки URL."""
    logger.info("=== Начало теста test_add_url ===")
    url = "http://test.com"
    title = "Test Page"
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body><p>Test content</p></body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        logger.info(f"Настройка мока для URL: {url}")
        m.get(url, text=html)
        
        # Добавляем URL
        logger.info("Добавление URL")
        processor.add_url(url, title)
        
        # Проверяем добавление в трекер
        logger.info("Проверка добавления в трекер")
        url_info = processor.tracker.get_url_info(url)
        assert url_info is not None, "URL не добавлен в трекер"
        assert url_info["status"] == "pending", f"Неверный статус: {url_info['status']}"
        
        # Запускаем обработку
        logger.info("Запуск обработки")
        processor.start_processing()
        
        # Ждем запуска обработки
        logger.info("Ожидание запуска обработки")
        assert wait_for_processing_start(processor), "Обработка не запустилась"
        
        # Ждем завершения обработки
        logger.info("Ожидание завершения обработки")
        assert wait_for_processing(processor), "Обработка не завершилась вовремя"
        
        # Проверяем результат обработки
        logger.info("Проверка результата обработки")
        url_info = processor.tracker.get_url_info(url)
        assert url_info["status"] == "completed", f"Неверный статус: {url_info['status']}"
        assert url_info["markdown_path"] is not None, "Не создан markdown файл"
        
        # Проверяем файл
        logger.info("Проверка созданного файла")
        markdown_path = Path(url_info["markdown_path"])
        assert markdown_path.exists(), "Файл не существует"
        content = markdown_path.read_text()
        assert "# Test Page" in content, "Неверное содержимое файла"
        
        logger.info("=== Тест test_add_url успешно завершен ===")

def test_start_stop_processing(processor):
    """Тест запуска и остановки обработки."""
    url = "http://test.com"
    html = "<html><body>Test</body></html>"
    
    with requests_mock.Mocker() as m:
        m.get(url, text=html)
        
        # Добавляем URL для обработки
        processor.add_url(url, "Test")
        
        # Запускаем обработку
        processor.start_processing()
        
        # Ждем запуска обработки
        assert wait_for_processing_start(processor), "Обработка не запустилась"
        
        # Останавливаем обработку
        processor.stop_processing()
        assert processor.stop_event.is_set()
        assert not processor.is_running

def test_process_url(processor):
    """Тест обработки URL."""
    url = "http://test.com"
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body><p>Test content</p></body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        m.get(url, text=html)
        
        # Добавляем URL
        processor.add_url(url, "Test")
        
        # Проверяем начальное состояние
        url_info = processor.tracker.get_url_info(url)
        assert url_info["status"] == "pending"
        
        # Запускаем обработку
        processor.start_processing()
        
        # Ждем завершения обработки
        assert wait_for_processing(processor), "Обработка не завершилась вовремя"
        
        # Проверяем результат
        url_info = processor.tracker.get_url_info(url)
        assert url_info["status"] == "completed"
        assert url_info["markdown_path"] is not None
        assert Path(url_info["markdown_path"]).exists()

def test_process_multiple_urls(processor):
    """Тест обработки нескольких URL."""
    urls = [
        ("http://test1.com", "Test 1"),
        ("http://test2.com", "Test 2"),
        ("http://test3.com", "Test 3")
    ]
    
    html_template = """
    <html>
        <head><title>{title}</title></head>
        <body><p>Content for {title}</p></body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        # Настраиваем моки
        for url, title in urls:
            m.get(url, text=html_template.format(title=title))
            processor.add_url(url, title)
        
        # Запускаем обработку
        processor.start_processing()
        
        # Ждем завершения
        assert wait_for_processing(processor), "Обработка не завершилась вовремя"
        
        # Проверяем результаты
        for url, title in urls:
            url_info = processor.tracker.get_url_info(url)
            assert url_info["status"] == "completed"
            assert url_info["markdown_path"] is not None
            assert Path(url_info["markdown_path"]).exists()

def test_error_handling(processor):
    """Тест обработки ошибок."""
    url = "http://test.com"
    
    with requests_mock.Mocker() as m:
        # Настраиваем мок с ошибкой
        m.get(url, status_code=404)
        
        # Добавляем URL
        processor.add_url(url, "Test")
        
        # Запускаем обработку
        processor.start_processing()
        
        # Ждем завершения
        assert wait_for_processing(processor), "Обработка не завершилась вовремя"
        
        # Проверяем результат
        url_info = processor.tracker.get_url_info(url)
        assert url_info["status"] == "error"

def test_resume_processing(processor):
    """Тест возобновления обработки."""
    urls = [
        ("http://test1.com", "Test 1"),
        ("http://test2.com", "Test 2")
    ]
    
    html_template = """
    <html>
        <head><title>{title}</title></head>
        <body><p>Content for {title}</p></body>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        # Настраиваем моки
        for url, title in urls:
            m.get(url, text=html_template.format(title=title))
            processor.add_url(url, title)
        
        # Запускаем обработку
        processor.start_processing()
        
        # Ждем запуска обработки
        assert wait_for_processing_start(processor), "Обработка не запустилась"
        
        # Останавливаем обработку
        processor.stop_processing()
        
        # Возобновляем обработку
        processor.start_processing()
        
        # Ждем завершения
        assert wait_for_processing(processor), "Обработка не завершилась вовремя"
        
        # Проверяем результаты
        for url, title in urls:
            url_info = processor.tracker.get_url_info(url)
            assert url_info["status"] == "completed"
            assert url_info["markdown_path"] is not None
            assert Path(url_info["markdown_path"]).exists()

def test_thread_safety(tmp_path_factory):
    """Тест потокобезопасности."""
    results_dir = tmp_path_factory.mktemp("results")
    processor = ContentProcessor(results_dir, max_workers=4)
    
    try:
        # Создаем множество URL
        urls = [
            (f"http://test{i}.com", f"Test {i}")
            for i in range(10)  # Уменьшаем количество URL
        ]
        
        html_template = """
        <html>
            <head><title>{title}</title></head>
            <body><p>Content</p></body>
        </html>
        """
        
        with requests_mock.Mocker() as m:
            # Настраиваем моки
            for url, title in urls:
                m.get(url, text=html_template.format(title=title))
            
            # Добавляем URL из разных потоков
            threads = []
            chunk_size = len(urls) // 2
            
            def add_urls(start, end):
                for i in range(start, end):
                    url, title = urls[i]
                    processor.add_url(url, title)
            
            # Создаем и запускаем потоки
            for i in range(0, len(urls), chunk_size):
                thread = threading.Thread(
                    target=add_urls,
                    args=(i, min(i + chunk_size, len(urls)))
                )
                threads.append(thread)
                thread.start()
            
            # Ждем завершения добавления URL
            for thread in threads:
                thread.join()
            
            # Запускаем обработку
            processor.start_processing()
            
            # Ждем запуска обработки
            assert wait_for_processing_start(processor), "Обработка не запустилась"
            
            # Ждем завершения обработки
            assert wait_for_processing(processor), "Обработка не завершилась вовремя"
            
            # Проверяем результаты
            processed_urls = processor.tracker.get_all_urls()
            assert len(processed_urls) == len(urls)
            
            for url, title in urls:
                url_info = processor.tracker.get_url_info(url)
                assert url_info is not None
                assert url_info["status"] == "completed"
                assert url_info["markdown_path"] is not None
                assert Path(url_info["markdown_path"]).exists()
    
    finally:
        processor.stop_processing() 