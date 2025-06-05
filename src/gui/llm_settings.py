#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль окна настроек LLM.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QFormLayout, QLineEdit, 
                           QPushButton, QVBoxLayout, QComboBox,
                           QHBoxLayout, QListWidget, QSpinBox,
                           QMessageBox, QInputDialog)

class LLMSettingsDialog(QDialog):
    """Диалог настроек LLM."""
    
    def __init__(self, settings: dict, parent=None):
        """
        Инициализация диалога настроек LLM.
        
        Args:
            settings: Словарь с текущими настройками
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Настройки LLM")
        self.setModal(True)
        self._init_ui()
        
    def _init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Список моделей
        models_layout = QHBoxLayout()
        self.models_list = QListWidget()
        self.models_list.addItems(self.settings.get("available_models", []))
        
        # Кнопки управления моделями
        models_buttons = QVBoxLayout()
        add_model_btn = QPushButton("Добавить")
        edit_model_btn = QPushButton("Изменить")
        delete_model_btn = QPushButton("Удалить")
        
        add_model_btn.clicked.connect(self._add_model)
        edit_model_btn.clicked.connect(self._edit_model)
        delete_model_btn.clicked.connect(self._delete_model)
        
        models_buttons.addWidget(add_model_btn)
        models_buttons.addWidget(edit_model_btn)
        models_buttons.addWidget(delete_model_btn)
        models_buttons.addStretch()
        
        models_layout.addWidget(self.models_list)
        models_layout.addLayout(models_buttons)
        
        form_layout.addRow("Доступные модели:", models_layout)
        
        # Выбранная модель
        self.model_combo = QComboBox()
        self.model_combo.addItems(self.settings.get("available_models", []))
        current_model = self.settings.get("model", "gpt-3.5-turbo")
        self.model_combo.setCurrentText(current_model)
        form_layout.addRow("Текущая модель:", self.model_combo)
        
        # API ключ
        self.api_key = QLineEdit()
        self.api_key.setText(self.settings.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API ключ:", self.api_key)
        
        # Базовый URL
        self.base_url = QLineEdit()
        self.base_url.setText(self.settings.get("base_url", "https://api.openai.com/v1"))
        form_layout.addRow("Базовый URL:", self.base_url)
        
        # Задержка между запросами
        self.request_delay = QSpinBox()
        self.request_delay.setRange(0, 10000)
        self.request_delay.setSingleStep(100)
        self.request_delay.setValue(self.settings.get("llm_request_delay", 1000))
        self.request_delay.setSuffix(" мс")
        form_layout.addRow("Задержка между запросами:", self.request_delay)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
    
    def _add_model(self):
        """Добавление новой модели."""
        model_name, ok = QInputDialog.getText(self, 'Добавить модель', 
                                            'Введите название модели:')
        if ok and model_name:
            if model_name not in [self.models_list.item(i).text() 
                                for i in range(self.models_list.count())]:
                self.models_list.addItem(model_name)
                self.model_combo.addItem(model_name)
            else:
                QMessageBox.warning(self, "Ошибка", 
                                  "Такая модель уже существует!")
    
    def _edit_model(self):
        """Редактирование выбранной модели."""
        current_item = self.models_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Ошибка", 
                              "Выберите модель для редактирования!")
            return
            
        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, 'Изменить модель', 
                                          'Введите новое название модели:', 
                                          text=old_name)
        
        if ok and new_name and new_name != old_name:
            if new_name not in [self.models_list.item(i).text() 
                              for i in range(self.models_list.count())]:
                current_item.setText(new_name)
                # Обновляем комбобокс
                idx = self.model_combo.findText(old_name)
                if idx >= 0:
                    self.model_combo.setItemText(idx, new_name)
                    if self.model_combo.currentText() == old_name:
                        self.model_combo.setCurrentText(new_name)
            else:
                QMessageBox.warning(self, "Ошибка", 
                                  "Такая модель уже существует!")
    
    def _delete_model(self):
        """Удаление выбранной модели."""
        current_item = self.models_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Ошибка", 
                              "Выберите модель для удаления!")
            return
            
        model_name = current_item.text()
        if self.models_list.count() <= 1:
            QMessageBox.warning(self, "Ошибка", 
                              "Нельзя удалить последнюю модель!")
            return
            
        reply = QMessageBox.question(self, 'Подтверждение', 
                                   f'Вы уверены, что хотите удалить модель "{model_name}"?',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            row = self.models_list.row(current_item)
            self.models_list.takeItem(row)
            # Удаляем из комбобокса
            idx = self.model_combo.findText(model_name)
            if idx >= 0:
                self.model_combo.removeItem(idx)
    
    def get_settings(self) -> dict:
        """
        Получение настроек из диалога.
        
        Returns:
            dict: Словарь с настройками
        """
        return {
            "model": self.model_combo.currentText(),
            "api_key": self.api_key.text(),
            "base_url": self.base_url.text(),
            "llm_request_delay": self.request_delay.value(),
            "available_models": [self.models_list.item(i).text() 
                               for i in range(self.models_list.count())]
        } 