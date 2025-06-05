#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной модуль приложения Bookmarks Checker.
"""

import logging
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
