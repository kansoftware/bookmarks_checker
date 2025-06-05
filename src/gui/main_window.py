#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль главного окна приложения.
"""

import asyncio
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QGroupBox,
                           QHBoxLayout, QLabel, QMainWindow, QPushButton,
                           QSpinBox, QTextEdit, QVBoxLayout, QWidget,
                            QAction, QProgressBar)

from core.checker import URLChecker
from core.parser import BookmarksParser
from core.content_processor import ContentProcessor
from utils.config import Config
from utils.logger import setup_logger
from utils.settings import Settings
from gui.llm_settings import LLMSettingsDialog

class CheckerThread(QThread):
    """Поток для проверки URL"""

    progress = pyqtSignal(str)
    url_checked = pyqtSignal(str, bool, str)  # url, success, error
    finished = pyqtSignal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._is_running = True

    def stop(self):
        """Остановка проверки"""
        self._is_running = False

    async def check_urls(self):
        """Асинхронная проверка URL"""
        parser = BookmarksParser(self.config.bookmarks_file)
        root_bookmark = parser.parse()

        if not root_bookmark:
            self.progress.emit("Ошибка при парсинге файла закладок")
            return

        urls = parser.get_all_urls(root_bookmark)
        total_urls = len(urls)
        processed = 0

        async with URLChecker(
            timeout=self.config.timeout, max_retries=self.config.retries, max_redirects_count=self.config.max_redirects
        ) as checker:
            for url in urls:
                if not self._is_running:
                    break

                try:
                    result = await checker.check_url(url)
                    status = "доступен" if result.is_available else "недоступен"
                    error = None if result.is_available else result.error
                    
                    # Отправляем результат проверки
                    self.url_checked.emit(url, result.is_available, error)
                    
                    # Обновляем прогресс
                    processed += 1
                    progress = f"Проверено {processed} из {total_urls} URL ({int(processed/total_urls*100)}%)"
                    self.progress.emit(progress)
                    
                except Exception as e:
                    error_msg = str(e)
                    self.progress.emit(f"Ошибка при проверке {url}: {error_msg}")
                    self.url_checked.emit(url, False, error_msg)
                    processed += 1

    def run(self):
        """Запуск проверки"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.check_urls())
        finally:
            loop.close()
        self.finished.emit()


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self) -> None:
        """Инициализация главного окна."""
        super().__init__()
        
        # Инициализация компонентов
        self.config = Config()
        self.logger = setup_logger()
        self.checker_thread: Optional[CheckerThread] = None
        self.settings = Settings()
        self.content_processor: Optional[ContentProcessor] = None
        
        self.setWindowTitle("Bookmarks Checker")
        self.setMinimumSize(800, 600)
        
        # Создание меню
        self._create_menu()
        
        # Инициализация интерфейса
        self._init_ui()
        self._connect_signals()
        
        # Загрузка настроек (после создания всех виджетов)
        self._load_settings()

    def _create_menu(self) -> None:
        """Создание главного меню."""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu('Файл')
        
        # Действие "Завершить работу"
        exit_action = QAction('Завершить работу', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Настройки
        settings_menu = menubar.addMenu('Настройки')
        
        # Действие "Настройки LLM"
        llm_settings_action = QAction('Настройки LLM', self)
        llm_settings_action.triggered.connect(self._show_llm_settings)
        settings_menu.addAction(llm_settings_action)
        
        # Меню Справка
        help_menu = menubar.addMenu('Справка')
        
        # Действие "Об авторе"
        about_action = QAction('Об авторе', self)
        about_action.triggered.connect(lambda: webbrowser.open('https://kansoftware.ru'))
        help_menu.addAction(about_action)

    def _init_ui(self) -> None:
        """Инициализация пользовательского интерфейса."""
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        layout = QVBoxLayout(central_widget)

        # Группа настроек проверки
        check_settings = QGroupBox("Настройки проверки")
        check_layout = QFormLayout()

        # Таймаут
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 30)
        self.timeout_spin.setValue(self.config.timeout)
        self.timeout_spin.setSuffix(" сек")
        check_layout.addRow("Таймаут:", self.timeout_spin)

        # Количество попыток
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(1, 10)
        self.retries_spin.setValue(self.config.retries)
        check_layout.addRow("Количество попыток:", self.retries_spin)

        # Количество потоков
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 32)
        self.threads_spin.setValue(self.config.threads)
        check_layout.addRow("Количество потоков:", self.threads_spin)

        check_settings.setLayout(check_layout)
        layout.addWidget(check_settings)

        # Группа настроек браузера
        browser_settings = QGroupBox("Настройки браузера")
        browser_layout = QFormLayout()

        # Выбор браузера
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chrome", "Yandex Browser"])
        self.browser_combo.setCurrentText(self.config.browser)
        browser_layout.addRow("Браузер:", self.browser_combo)

        # Путь к файлу закладок
        bookmarks_layout = QHBoxLayout()
        self.bookmarks_path = QLabel("Не выбран")
        self.bookmarks_path.setStyleSheet("border: 1px solid gray; padding: 2px;")
        bookmarks_btn = QPushButton("Выбрать")
        bookmarks_btn.clicked.connect(self.select_bookmarks_file)
        bookmarks_layout.addWidget(self.bookmarks_path)
        bookmarks_layout.addWidget(bookmarks_btn)
        browser_layout.addRow("Файл закладок:", bookmarks_layout)

        browser_settings.setLayout(browser_layout)
        layout.addWidget(browser_settings)

        # Группа настроек сохранения
        save_settings = QGroupBox("Настройки сохранения")
        save_layout = QFormLayout()

        # Путь для сохранения результатов
        results_layout = QHBoxLayout()
        self.results_path = QLabel("Не выбран")
        self.results_path.setStyleSheet("border: 1px solid gray; padding: 2px;")
        results_btn = QPushButton("Выбрать")
        results_btn.clicked.connect(self.select_results_dir)
        results_layout.addWidget(self.results_path)
        results_layout.addWidget(results_btn)
        save_layout.addRow("Директория результатов:", results_layout)

        save_settings.setLayout(save_layout)
        layout.addWidget(save_settings)

        # Кнопки управления
        buttons_layout = QHBoxLayout()
        self.start_btn = QPushButton("Начать проверку")
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setEnabled(False)
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        layout.addLayout(buttons_layout)

        # Прогресс
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v из %m (%p%)")
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(QLabel("Лог:"))
        layout.addWidget(self.log_text)

    def _connect_signals(self) -> None:
        """Подключение сигналов к слотам."""
        self.start_btn.clicked.connect(self._start_checking)
        self.stop_btn.clicked.connect(self._stop_checking)

    def _load_settings(self) -> None:
        """Загрузка настроек."""
        # Загрузка настроек окна
        window_settings = self.settings.get_window_settings()
        if window_settings:
            self.resize(*window_settings["size"])
            self.move(*window_settings["position"])
        
        # Загрузка настроек проверки
        checker_settings = self.settings.get_checker_settings()
        if checker_settings:
            self.config.timeout = checker_settings["timeout"]
            self.config.retries = checker_settings["retries"]
            self.config.threads = checker_settings["threads"]
            self.config.browser = checker_settings["browser"]
            
            # Загружаем путь к файлу закладок
            if "bookmarks_file" in checker_settings and checker_settings["bookmarks_file"]:
                self.config.bookmarks_file = checker_settings["bookmarks_file"]
                self.bookmarks_path.setText(checker_settings["bookmarks_file"])

    def _save_settings(self) -> None:
        """Сохранение настроек."""
        # Сохранение настроек окна
        window_settings = {
            "size": [self.width(), self.height()],
            "position": [self.x(), self.y()]
        }
        self.settings.update_window_settings(window_settings)
        
        # Сохранение настроек проверки
        checker_settings = {
            "timeout": self.timeout_spin.value(),
            "retries": self.retries_spin.value(),
            "threads": self.threads_spin.value(),
            "browser": self.browser_combo.currentText(),
            "bookmarks_file": self.config.bookmarks_file
        }
        self.settings.update_checker_settings(checker_settings)

    def _show_llm_settings(self) -> None:
        """Показ диалога настроек LLM."""
        dialog = LLMSettingsDialog(self.settings.get_llm_settings(), self)
        if dialog.exec_():
            self.settings.update_llm_settings(dialog.get_settings())

    def select_bookmarks_file(self) -> None:
        """Выбор файла закладок."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл закладок", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_name:
            self.bookmarks_path.setText(file_name)
            self.config.bookmarks_file = file_name
            self.logger.info(f"Выбран файл: {file_name}")

    def select_results_dir(self) -> None:
        """Выбор директории для сохранения результатов."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите директорию для сохранения результатов",
            str(Path.home())
        )
        if dir_path:
            self.results_path.setText(dir_path)
            self.config.results_dir = dir_path

    def _start_checking(self) -> None:
        """Запуск проверки."""
        if not self.config.bookmarks_file:
            self._update_log("Выберите файл закладок")
            return

        if not self.config.results_dir:
            self._update_log("Выберите директорию для сохранения результатов")
            return

        # Обновляем конфигурацию
        self.config.timeout = self.timeout_spin.value()
        self.config.retries = self.retries_spin.value()
        self.config.threads = self.threads_spin.value()
        self.config.browser = self.browser_combo.currentText()

        # Создаем процессор контента
        self.content_processor = ContentProcessor(
            Path(self.config.results_dir),
            max_workers=self.config.threads
        )

        # Создаем и запускаем поток проверки
        self.checker_thread = CheckerThread(self.config)
        self.checker_thread.progress.connect(self._update_log)
        self.checker_thread.url_checked.connect(self._update_url_checked)
        self.checker_thread.finished.connect(self._checking_finished)

        # Отключаем кнопки
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Очищаем лог
        self.log_text.clear()

        # Запускаем проверку
        self.checker_thread.start()

        # Запускаем обработку контента
        self.content_processor.start_processing()

        self._update_log("Проверка запущена")

    def _stop_checking(self) -> None:
        """Остановка проверки."""
        if self.checker_thread and self.checker_thread.isRunning():
            self.checker_thread.stop()
            self.checker_thread.wait()

        if self.content_processor:
            self.content_processor.stop_processing()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._update_log("Проверка остановлена")

    def _update_log(self, message: str) -> None:
        """Обновление лога"""
        self.log_text.append(message)

    def _update_url_checked(self, url: str, success: bool, error: str) -> None:
        """Обновление результата проверки URL"""
        status = "доступен" if success else "недоступен"
        self.log_text.append(f"URL {url}: {status}")
        if not success:
            self.log_text.append(f"Ошибка: {error}")

    def _checking_finished(self) -> None:
        """Обработка завершения проверки."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._update_log("Проверка завершена")

        # Останавливаем обработку контента
        if self.content_processor:
            self.content_processor.stop_processing()
            self.content_processor = None

    def closeEvent(self, event) -> None:
        """Обработка закрытия окна."""
        # Останавливаем все процессы
        self._stop_checking()
        
        # Сохраняем настройки
        self._save_settings()
        
        event.accept()
