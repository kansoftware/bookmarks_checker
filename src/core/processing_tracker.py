"""
@file: processing_tracker.py
@description: Модуль для отслеживания процесса обработки URL и сохранения результатов
@dependencies: json, pathlib, threading
@created: 2024-03-21
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ProcessingTracker:
    """Класс для отслеживания процесса обработки URL и сохранения результатов."""
    
    def __init__(self, results_dir: Path):
        """
        Инициализация трекера.
        
        Args:
            results_dir: Директория для сохранения результатов
        """
        logger.info(f"[TRACKER] Инициализация ProcessingTracker: {results_dir}")
        self.results_dir = results_dir
        self.processing_file = results_dir / "processing.json"
        self.lock = threading.RLock()
        self.data = None
        self._ensure_dirs()
        logger.info("[TRACKER] Инициализация ProcessingTracker завершена")
    
    def _ensure_dirs(self) -> None:
        logger.info("[TRACKER] Создание директорий и файла состояния")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        if not self.processing_file.exists():
            logger.info("[TRACKER] Создание нового файла состояния")
            self.data = {
                "urls": {},
                "last_update": datetime.now().isoformat()
            }
            self._save_data()
        else:
            logger.info("[TRACKER] Загрузка существующего файла состояния")
            self._load_data()
    
    def _load_data(self) -> None:
        logger.info("[TRACKER] Загрузка данных из файла")
        try:
            with self.lock:
                with open(self.processing_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    logger.info(f"[TRACKER] Загружено URL: {len(self.data['urls'])}")
        except Exception as e:
            logger.error(f"[TRACKER] Ошибка загрузки данных: {e}")
            self.data = {
                "urls": {},
                "last_update": datetime.now().isoformat()
            }
    
    def _save_data(self) -> None:
        logger.info("[TRACKER] Сохранение данных в файл")
        with self.lock:
            if self.data:
                with open(self.processing_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
                    logger.info(f"[TRACKER] Сохранено URL: {len(self.data['urls'])}")
    
    def add_url(self, url: str, title: str) -> None:
        logger.info(f"[TRACKER] Добавление URL: {url}, title: {title}")
        with self.lock:
            if self.data and url not in self.data["urls"]:
                logger.info(f"[TRACKER] Новый URL: {url}")
                self.data["urls"][url] = {
                    "title": title,
                    "status": "pending",
                    "check_result": None,
                    "check_time": None,
                    "markdown_path": None,
                    "error": None
                }
                self.data["last_update"] = datetime.now().isoformat()
                self._save_data()
            else:
                logger.info(f"[TRACKER] URL уже существует: {url}")
    
    def update_check_result(self, url: str, success: bool, error: Optional[str] = None) -> None:
        logger.info(f"[TRACKER] Обновление результата проверки: {url}, success: {success}, error: {error}")
        with self.lock:
            if self.data and url in self.data["urls"]:
                self.data["urls"][url].update({
                    "status": "checked",
                    "check_result": success,
                    "check_time": datetime.now().isoformat(),
                    "error": error
                })
                self.data["last_update"] = datetime.now().isoformat()
                self._save_data()
                logger.info(f"[TRACKER] Результат проверки обновлен: {url}")
            else:
                logger.warning(f"[TRACKER] URL не найден при обновлении результата: {url}")
    
    def update_markdown_path(self, url: str, markdown_path: Optional[Path]) -> None:
        logger.info(f"[TRACKER] Обновление пути markdown: {url}, path: {markdown_path}")
        with self.lock:
            if self.data and url in self.data["urls"]:
                self.data["urls"][url].update({
                    "status": "completed" if markdown_path else "failed",
                    "markdown_path": str(markdown_path) if markdown_path else None
                })
                self.data["last_update"] = datetime.now().isoformat()
                self._save_data()
                logger.info(f"[TRACKER] Путь markdown обновлен: {url}")
            else:
                logger.warning(f"[TRACKER] URL не найден при обновлении пути: {url}")
    
    def get_pending_urls(self) -> List[str]:
        """
        Возвращает список URL, ожидающих обработки.
        
        Returns:
            List[str]: Список URL
        """
        logger.info("[TRACKER] Получение списка ожидающих обработки URL")
        
        with self.lock:
            if not self.data:
                return []
            pending = [
                url for url, info in self.data["urls"].items()
                if info["status"] in ["pending", "checked"] 
                and info.get("check_result", True)  # Включаем только успешно проверенные или не проверенные
                and not info.get("markdown_path")
            ]
            
        logger.info(f"[TRACKER] Найдено ожидающих URL: {len(pending)}")
        return pending
    
    def get_url_info(self, url: str) -> Optional[Dict]:
        logger.info(f"[TRACKER] Получение информации об URL: {url}")
        with self.lock:
            if not self.data:
                return None
            info = self.data["urls"].get(url)
            if info:
                logger.info(f"[TRACKER] Информация найдена: {url}, status: {info['status']}")
            else:
                logger.warning(f"[TRACKER] Информация не найдена: {url}")
            return info
    
    def get_all_urls(self) -> Dict:
        logger.info("[TRACKER] Получение всех URL")
        with self.lock:
            if not self.data:
                return {}
            urls = dict(self.data["urls"])
            logger.info(f"[TRACKER] Всего URL: {len(urls)}")
            return urls
    
    def reset_failed(self) -> None:
        logger.info("[TRACKER] Сброс неудачных проверок")
        with self.lock:
            if not self.data:
                return
            reset_count = 0
            for url_info in self.data["urls"].values():
                if url_info["status"] == "failed":
                    url_info["status"] = "pending"
                    url_info["check_result"] = None
                    url_info["check_time"] = None
                    url_info["markdown_path"] = None
                    url_info["error"] = None
                    reset_count += 1
            if reset_count > 0:
                self.data["last_update"] = datetime.now().isoformat()
                self._save_data()
            logger.info(f"[TRACKER] Сброшено URL: {reset_count}")

    def update_url_status(self, url: str, status: str, error: Optional[str] = None) -> None:
        """
        Обновляет статус URL.

        Args:
            url: URL для обновления
            status: Новый статус
            error: Сообщение об ошибке
        """
        logger.info(f"[TRACKER] Обновление статуса URL: {url}, status: {status}")

        with self.lock:
            if self.data and url in self.data["urls"]:
                self.data["urls"][url]["status"] = status
                self.data["urls"][url]["error"] = error
                if status == "completed":
                    self.data["urls"][url]["check_time"] = datetime.now().isoformat()
                self.data["last_update"] = datetime.now().isoformat()
                self._save_data()
            else:
                logger.warning(f"[TRACKER] URL не найден: {url}")
