"""
@file: content_processor.py
@description: Модуль для многопоточной обработки URL и генерации markdown
@dependencies: threading, queue, ProcessingTracker, MarkdownGenerator
@created: 2024-03-21
"""

import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
import logging
import time
from urllib.parse import urlparse
import hashlib

from .markdown_generator import MarkdownGenerator
from .processing_tracker import ProcessingTracker

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Класс для обработки контента."""

    def __init__(self, results_dir: str, max_workers: int = 4) -> None:
        """
        Инициализация обработчика контента.

        Args:
            results_dir: Директория для результатов
            max_workers: Максимальное количество рабочих потоков
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"[PROCESSOR] Инициализация ContentProcessor: {results_dir}, max_workers: {max_workers}")

        self.results_dir = Path(results_dir)
        self.max_workers = max_workers
        self.tracker = ProcessingTracker(self.results_dir)
        self.markdown_generator = MarkdownGenerator()
        
        self.queue = queue.Queue()
        self.queue_thread = None
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        self.stop_event = threading.Event()

        self.logger.info("[PROCESSOR] Инициализация ContentProcessor завершена")

    def add_url(self, url: str, title: Optional[str] = None) -> None:
        """
        Добавляет URL в очередь на обработку.

        Args:
            url: URL для обработки
            title: Заголовок страницы
        """
        self.logger.info(f"[PROCESSOR] Добавление URL: {url}, title: {title}")
        
        with self._lock:
            # Добавляем URL в трекер
            self.tracker.add_url(url, title or "")
            
            # Добавляем URL в очередь
            self.queue.put(url)

    def start_processing(self) -> None:
        """Запускает обработку URL."""
        self.logger.info("[PROCESSOR] Запуск обработки")

        with self._lock:
            if self.is_running:
                self.logger.warning("[PROCESSOR] Обработка уже запущена")
                return

            # Сбрасываем событие остановки
            self.stop_event.clear()

            # Создаем поток для обработки очереди
            self.logger.info("[PROCESSOR] Создание потока очереди")
            self.queue_thread = threading.Thread(target=self._process_queue)
            self.queue_thread.daemon = True

            # Загружаем ожидающие URL
            self.logger.info("[PROCESSOR] Загрузка ожидающих URL")
            pending_urls = self.tracker.get_pending_urls()
            self.logger.info(f"[PROCESSOR] Найдено ожидающих URL: {len(pending_urls)}")
            for url in pending_urls:
                self.queue.put(url)

            # Запускаем обработку
            self.is_running = True
            self.queue_thread.start()
            self.logger.info("[PROCESSOR] Обработка запущена")

    def stop_processing(self) -> None:
        """Останавливает обработку URL."""
        self.logger.info("[PROCESSOR] Остановка обработки")

        with self._lock:
            if not self.is_running:
                self.logger.warning("[PROCESSOR] Обработка уже остановлена")
                return

            # Устанавливаем событие остановки
            self.stop_event.set()

            # Останавливаем обработку
            self.is_running = False

            # Ожидаем завершения активных задач
            self.logger.info("[PROCESSOR] Ожидание завершения активных задач")
            self.executor.shutdown(wait=True)

            # Создаем новый executor
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

            # Ожидаем завершения потока очереди
            self.logger.info("[PROCESSOR] Ожидание завершения потока очереди")
            if self.queue_thread:
                self.queue_thread.join()
                self.queue_thread = None

            # Очищаем очередь
            self.logger.info("[PROCESSOR] Очистка очереди")
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    break

            self.logger.info("[PROCESSOR] Обработка остановлена")

    def process_url(self, url: str) -> bool:
        """
        Обрабатывает URL.

        Args:
            url: URL для обработки

        Returns:
            bool: True если обработка успешна, False в случае ошибки
        """
        self.logger.info(f"[PROCESSOR] Обработка URL: {url}")

        try:
            # Проверяем событие остановки
            if self.stop_event.is_set():
                self.logger.info(f"[PROCESSOR] Пропуск обработки URL {url} из-за остановки")
                return False

            # Генерируем имя файла
            filename = hashlib.md5(url.encode()).hexdigest() + ".md"
            save_path = Path(self.results_dir) / filename

            # Обновляем статус
            self.tracker.update_url_status(url, "processing")

            # Генерируем markdown
            result = self.markdown_generator.generate_markdown(url, str(save_path))

            if result:
                # Обновляем статус и путь к файлу
                self.tracker.update_url_status(url, "completed")
                self.tracker.update_markdown_path(url, result)
                self.logger.info(f"[PROCESSOR] URL обработан успешно: {url}")
                return True
            else:
                # Обновляем статус с ошибкой
                self.tracker.update_url_status(url, "error")
                self.logger.error(f"[PROCESSOR] Ошибка при обработке URL: {url}")
                return False

        except Exception as e:
            self.logger.error(f"[PROCESSOR] Ошибка при обработке URL {url}: {str(e)}")
            self.tracker.update_url_status(url, "error")
            return False

    def _process_queue(self) -> None:
        """Обрабатывает URL из очереди."""
        self.logger.info("[PROCESSOR] Запуск обработчика очереди")

        while self.is_running and not self.stop_event.is_set():
            try:
                # Ожидаем URL из очереди
                self.logger.info("[PROCESSOR] Ожидание URL из очереди...")
                try:
                    url = self.queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Обрабатываем URL
                if not self.stop_event.is_set():
                    self.executor.submit(self.process_url, url)

            except Exception as e:
                self.logger.error(f"[PROCESSOR] Ошибка в обработчике очереди: {str(e)}")
                if not self.stop_event.is_set():
                    time.sleep(1)  # Пауза перед следующей попыткой

        self.logger.info("[PROCESSOR] Обработчик очереди остановлен")

    def _get_save_path(self, url: str, title: str) -> Path:
        """
        Создает путь для сохранения markdown файла.
        
        Args:
            url: URL
            title: Название
            
        Returns:
            Path: Путь для сохранения
        """
        # Создаем безопасное имя файла из заголовка
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title.strip().replace(' ', '_')
        
        # Получаем домен из URL
        domain = urlparse(url).netloc
        
        # Создаем структуру директорий
        domain_dir = Path(self.results_dir) / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем имя файла
        filename = f"{safe_title}_{hashlib.md5(url.encode()).hexdigest()[:8]}.md"
        return domain_dir / filename
