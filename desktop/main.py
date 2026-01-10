"""
Мониторинг конкурентов - Desktop приложение на PyQt6 (Standalone)
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QFrame, QScrollArea,
    QFileDialog, QStackedWidget, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from styles import DARK_THEME
from gemini_client import GeminiClient
from parser import WebParser
import json

class WorkerThread(QThread):
    """Поток для выполнения долгих операций"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class DropZone(QFrame):
    """Зона для drag & drop изображений"""
    fileDropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setObjectName("uploadZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_label = QLabel("📁")
        self.icon_label.setStyleSheet("font-size: 48px;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.text_label = QLabel("Перетащите изображение или нажмите для выбора")
        self.text_label.setStyleSheet("color: #94a3b8; font-size: 14px;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.hint_label = QLabel("PNG, JPG, GIF, WEBP до 10MB")
        self.hint_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.hide()
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.preview_label)
        
        self.selected_file = None
    
    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.gif *.webp)"
        )
        if file_path:
            self.set_file(file_path)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame#uploadZone { border-color: #06b6d4; background-color: rgba(6, 182, 212, 0.1); }")
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
    
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                self.set_file(file_path)
    
    def set_file(self, file_path: str):
        self.selected_file = file_path
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(300, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(pixmap)
            self.preview_label.show()
            self.icon_label.hide()
            self.text_label.setText(Path(file_path).name)
            self.hint_label.setText("Нажмите для замены")
            self.fileDropped.emit(file_path)
    
    def clear(self):
        self.selected_file = None
        self.preview_label.hide()
        self.icon_label.show()
        self.text_label.setText("Перетащите изображение или нажмите для выбора")
        self.hint_label.setText("PNG, JPG, GIF, WEBP до 10MB")

class ResultBlock(QFrame):
    """Блок результата анализа"""
    def __init__(self, title: str, items: list, icon: str = "→"):
        super().__init__()
        self.setObjectName("resultBlock")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        
        for item in items:
            item_label = QLabel(f"{icon} {item}")
            item_label.setWordWrap(True)
            item_label.setStyleSheet("color: #94a3b8; margin-left: 8px; line-height: 1.5;")
            layout.addWidget(item_label)

class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Мониторинг конкурентов | AI Ассистент")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Применяем стили
        self.setStyleSheet(DARK_THEME)
        
        # Настройки
        self.settings = QSettings("CompetitorAI", "Settings")
        
        # Инициализируем клиенты
        self.gemini_client = None
        self.parser = WebParser()
        self.current_worker = None
        
        # История (локально в JSON)
        self.history_file = Path("history.json")
        self.history = self.load_history()
        
        # Главный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar и Content
        self.setup_sidebar(main_layout)
        self.setup_content(main_layout)
        
        # Проверяем API ключ
        self.check_api_key()
    
    def setup_sidebar(self, parent_layout):
        """Создание боковой панели"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo
        logo = QLabel("⚡ CompetitorAI")
        logo.setObjectName("logo")
        layout.addWidget(logo)
        
        # Navigation
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(12, 16, 12, 16)
        nav_layout.setSpacing(4)
        
        self.nav_buttons = []
        nav_items = [
            ("📝 Анализ текста", 0),
            ("🖼️ Анализ изображений", 1),
            ("🌐 Парсинг сайта", 2),
            ("📋 История", 3),
            ("⚙️ Настройки", 4)
        ]
        
        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=index: self.switch_tab(idx))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        self.nav_buttons[0].setChecked(True)
        nav_layout.addStretch()
        
        # Status
        self.status_label = QLabel("● Проверка API ключа...")
        self.status_label.setStyleSheet("color: #f59e0b; padding: 16px;")
        nav_layout.addWidget(self.status_label)
        
        layout.addWidget(nav_widget)
        parent_layout.addWidget(sidebar)
    
    def setup_content(self, parent_layout):
        """Создание области контента"""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 32, 40, 32)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 24)
        
        title = QLabel("Мониторинг конкурентов")
        title.setObjectName("title")
        subtitle = QLabel("AI-ассистент для анализа конкурентной среды")
        subtitle.setObjectName("subtitle")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        content_layout.addWidget(header)
        
        # Stacked widget для вкладок
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.create_text_tab())
        self.stacked_widget.addWidget(self.create_image_tab())
        self.stacked_widget.addWidget(self.create_parse_tab())
        self.stacked_widget.addWidget(self.create_history_tab())
        self.stacked_widget.addWidget(self.create_settings_tab())
        
        content_layout.addWidget(self.stacked_widget)
        
        # Results area
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.hide()
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_scroll.setWidget(self.results_widget)
        content_layout.addWidget(self.results_scroll)
        
        # Loading indicator
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedWidth(300)
        
        self.loading_label = QLabel("Анализирую данные...")
        self.loading_label.setStyleSheet("color: #94a3b8; font-size: 16px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        loading_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_label)
        self.loading_widget.hide()
        
        content_layout.addWidget(self.loading_widget)
        parent_layout.addWidget(content_widget)
    
    def create_text_tab(self) -> QWidget:
        """Вкладка анализа текста"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel("Анализ текста конкурента")
        title.setObjectName("cardTitle")
        
        desc = QLabel("Вставьте текст с сайта конкурента, из рекламы или описания продукта")
        desc.setObjectName("cardDescription")
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Вставьте текст конкурента для анализа...\n\nНапример: описание продукта, текст с лендинга, рекламное объявление...")
        self.text_input.setMinimumHeight(200)
        
        self.analyze_text_btn = QPushButton("⚡ Проанализировать")
        self.analyze_text_btn.setObjectName("primaryButton")
        self.analyze_text_btn.clicked.connect(self.analyze_text)
        
        card_layout.addWidget(title)
        card_layout.addWidget(desc)
        card_layout.addSpacing(16)
        card_layout.addWidget(self.text_input)
        card_layout.addSpacing(16)
        card_layout.addWidget(self.analyze_text_btn)
        
        layout.addWidget(card)
        layout.addStretch()
        return widget
    
    def create_image_tab(self) -> QWidget:
        """Вкладка анализа изображений"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel("Анализ изображений")
        title.setObjectName("cardTitle")
        
        desc = QLabel("Загрузите скриншот сайта, баннер или фото упаковки конкурента")
        desc.setObjectName("cardDescription")
        
        self.drop_zone = DropZone()
        
        self.analyze_image_btn = QPushButton("⚡ Проанализировать")
        self.analyze_image_btn.setObjectName("primaryButton")
        self.analyze_image_btn.clicked.connect(self.analyze_image)
        
        card_layout.addWidget(title)
        card_layout.addWidget(desc)
        card_layout.addSpacing(16)
        card_layout.addWidget(self.drop_zone)
        card_layout.addSpacing(16)
        card_layout.addWidget(self.analyze_image_btn)
        
        layout.addWidget(card)
        layout.addStretch()
        return widget
    
    def create_parse_tab(self) -> QWidget:
        """Вкладка парсинга сайта"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel("Парсинг сайта конкурента")
        title.setObjectName("cardTitle")
        
        desc = QLabel("Введите URL сайта для автоматического извлечения и анализа контента")
        desc.setObjectName("cardDescription")
        
        url_layout = QHBoxLayout()
        prefix = QLabel("https://")
        prefix.setStyleSheet("background-color: #243049; padding: 12px 16px; border-radius: 8px 0 0 8px; color: #64748b;")
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("example.com")
        self.url_input.setStyleSheet("border-radius: 0 8px 8px 0;")
        
        url_layout.addWidget(prefix)
        url_layout.addWidget(self.url_input)
        
        self.parse_btn = QPushButton("⚡ Парсить и анализировать")
        self.parse_btn.setObjectName("primaryButton")
        self.parse_btn.clicked.connect(self.parse_site)
        
        card_layout.addWidget(title)
        card_layout.addWidget(desc)
        card_layout.addSpacing(16)
        card_layout.addLayout(url_layout)
        card_layout.addSpacing(16)
        card_layout.addWidget(self.parse_btn)
        
        layout.addWidget(card)
        layout.addStretch()
        return widget
    
    def create_history_tab(self) -> QWidget:
        """Вкладка истории"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        header = QHBoxLayout()
        title = QLabel("История запросов")
        title.setObjectName("cardTitle")
        
        self.clear_history_btn = QPushButton("🗑️ Очистить")
        self.clear_history_btn.setObjectName("secondaryButton")
        self.clear_history_btn.clicked.connect(self.clear_history)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.clear_history_btn)
        layout.addLayout(header)
        
        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        
        self.history_widget = QWidget()
        self.history_layout = QVBoxLayout(self.history_widget)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.history_scroll.setWidget(self.history_widget)
        
        layout.addWidget(self.history_scroll)
        return widget
    
    def create_settings_tab(self) -> QWidget:
        """Вкладка настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel("⚙️ Настройки")
        title.setObjectName("cardTitle")
        
        desc = QLabel("Настройте Google Gemini API для работы приложения")
        desc.setObjectName("cardDescription")
        
        card_layout.addWidget(title)
        card_layout.addWidget(desc)
        card_layout.addSpacing(24)
        
        # API Key
        api_label = QLabel("Google Gemini API Key:")
        api_label.setStyleSheet("color: #f1f5f9; font-weight: 600; font-size: 14px;")
        
        api_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("AIza...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Загружаем сохранённый ключ
        saved_key = self.settings.value("gemini_api_key", "")
        if saved_key:
            self.api_key_input.setText(saved_key)
        
        self.show_key_btn = QPushButton("👁️")
        self.show_key_btn.setObjectName("secondaryButton")
        self.show_key_btn.setFixedWidth(50)
        self.show_key_btn.clicked.connect(self.toggle_key_visibility)
        
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.show_key_btn)
        
        # Ссылка на получение ключа
        help_label = QLabel('<a href="https://aistudio.google.com/apikey" style="color: #22d3ee;">Получить бесплатный API ключ →</a>')
        help_label.setOpenExternalLinks(True)
        help_label.setStyleSheet("font-size: 13px; margin-top: 8px;")
        
        # Кнопка сохранения
        self.save_settings_btn = QPushButton("💾 Сохранить настройки")
        self.save_settings_btn.setObjectName("primaryButton")
        self.save_settings_btn.clicked.connect(self.save_settings)
        
        card_layout.addWidget(api_label)
        card_layout.addLayout(api_layout)
        card_layout.addWidget(help_label)
        card_layout.addSpacing(24)
        card_layout.addWidget(self.save_settings_btn)
        
        layout.addWidget(card)
        layout.addStretch()
        return widget
    
    def toggle_key_visibility(self):
        """Показать/скрыть API ключ"""
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("🙈")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("👁️")
    
    def save_settings(self):
        """Сохранение настроек"""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API ключ!")
            return
        
        # Сохраняем в QSettings
        self.settings.setValue("gemini_api_key", api_key)
        
        # Инициализируем клиент
        try:
            self.gemini_client = GeminiClient(api_key)
            self.status_label.setText("● Gemini 2.0 активен")
            self.status_label.setStyleSheet("color: #10b981; padding: 16px;")
            QMessageBox.information(self, "Успех", "Настройки сохранены!\n\nGemini API подключён.")
        except Exception as e:
            self.status_label.setText("● Ошибка API")
            self.status_label.setStyleSheet("color: #ef4444; padding: 16px;")
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться:\n{str(e)}")
    
    def check_api_key(self):
        """Проверка наличия API ключа"""
        api_key = self.settings.value("gemini_api_key", "")
        
        if api_key:
            try:
                self.gemini_client = GeminiClient(api_key)
                self.status_label.setText("● Gemini 2.0 активен")
                self.status_label.setStyleSheet("color: #10b981; padding: 16px;")
            except Exception as e:
                self.status_label.setText("● Ошибка API")
                self.status_label.setStyleSheet("color: #ef4444; padding: 16px;")
                QMessageBox.warning(
                    self,
                    "Ошибка API",
                    f"Не удалось подключиться к Gemini:\n{str(e)}\n\nПерейдите в Настройки и проверьте API ключ."
                )
        else:
            self.status_label.setText("● Нужен API ключ")
            self.status_label.setStyleSheet("color: #f59e0b; padding: 16px;")
            QMessageBox.information(
                self,
                "Настройка API",
                "Добро пожаловать!\n\nДля работы нужен Google Gemini API ключ.\n\nПерейдите в Настройки → введите ключ."
            )
            # Автоматически открываем настройки
            self.switch_tab(4)
    
    def switch_tab(self, index: int):
        """Переключение вкладок"""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        
        self.stacked_widget.setCurrentIndex(index)
        self.results_scroll.hide()
        
        # Загружаем историю при переключении
        if index == 3:
            self.load_history_ui()
    
    def show_loading(self, message: str = "Анализирую данные..."):
        """Показать индикатор загрузки"""
        self.loading_label.setText(message)
        self.loading_widget.show()
        self.results_scroll.hide()
    
    def hide_loading(self):
        """Скрыть индикатор загрузки"""
        self.loading_widget.hide()
    
    def show_results(self, analysis: dict, request_type: str):
        """Показать результаты анализа"""
        # Очищаем предыдущие результаты
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Сильные стороны
        if analysis.get("strengths"):
            block = ResultBlock("💪 Сильные стороны", analysis["strengths"])
            self.results_layout.addWidget(block)
        
        # Слабые стороны
        if analysis.get("weaknesses"):
            block = ResultBlock("⚠️ Слабые стороны", analysis["weaknesses"])
            self.results_layout.addWidget(block)
        
        # УТП
        if analysis.get("unique_offers"):
            block = ResultBlock("🎯 Уникальные предложения", analysis["unique_offers"])
            self.results_layout.addWidget(block)
        
        # ЦА
        if analysis.get("target_audience"):
            block = ResultBlock("👥 Целевая аудитория", analysis["target_audience"])
            self.results_layout.addWidget(block)
        
        # Маркетинговые инсайты
        if analysis.get("marketing_insights"):
            block = ResultBlock("💡 Маркетинговые инсайты", analysis["marketing_insights"])
            self.results_layout.addWidget(block)
        
        # Рекомендации
        if analysis.get("recommendations"):
            block = ResultBlock("📋 Рекомендации", analysis["recommendations"])
            self.results_layout.addWidget(block)
        
        self.results_layout.addStretch()
        self.results_scroll.show()
        
        # Сохраняем в историю
        self.save_to_history(request_type, analysis)
    
    def show_error(self, message: str):
        """Показать ошибку"""
        QMessageBox.critical(self, "Ошибка", message)
    
    # === API методы ===
    
    def analyze_text(self):
        """Анализ текста"""
        if not self.gemini_client:
            QMessageBox.warning(self, "Ошибка", "Настройте API ключ в разделе Настройки!")
            return
        
        text = self.text_input.toPlainText().strip()
        if len(text) < 10:
            self.show_error("Введите текст минимум 10 символов")
            return
        
        self.show_loading("Анализирую текст через Gemini...")
        self.current_worker = WorkerThread(self.gemini_client.analyze_text, text)
        self.current_worker.finished.connect(self.on_text_complete)
        self.current_worker.error.connect(lambda e: self.on_error(e))
        self.current_worker.start()
    
    def on_text_complete(self, result: dict):
        """Обработка результата анализа текста"""
        self.hide_loading()
        if result.get("success") and result.get("analysis"):
            self.show_results(result["analysis"], "text")
        else:
            self.show_error(result.get("error", "Неизвестная ошибка"))
    
    def analyze_image(self):
        """Анализ изображения"""
        if not self.gemini_client:
            QMessageBox.warning(self, "Ошибка", "Настройте API ключ в разделе Настройки!")
            return
        
        if not self.drop_zone.selected_file:
            self.show_error("Выберите изображение для анализа")
            return
        
        self.show_loading("Анализирую изображение через Gemini Vision...")
        self.current_worker = WorkerThread(self.gemini_client.analyze_image, self.drop_zone.selected_file)
        self.current_worker.finished.connect(self.on_image_complete)
        self.current_worker.error.connect(lambda e: self.on_error(e))
        self.current_worker.start()
    
    def on_image_complete(self, result: dict):
        """Обработка результата анализа изображения"""
        self.hide_loading()
        if result.get("success") and result.get("analysis"):
            self.show_results(result["analysis"], "image")
        else:
            self.show_error(result.get("error", "Неизвестная ошибка"))
    
    def parse_site(self):
        """Парсинг сайта"""
        if not self.gemini_client:
            QMessageBox.warning(self, "Ошибка", "Настройте API ключ в разделе Настройки!")
            return
        
        url = self.url_input.text().strip()
        if not url:
            self.show_error("Введите URL сайта")
            return
        
        self.show_loading("Парсинг сайта...")
        self.current_worker = WorkerThread(self._parse_and_analyze, url)
        self.current_worker.finished.connect(self.on_parse_complete)
        self.current_worker.error.connect(lambda e: self.on_error(e))
        self.current_worker.start()
    
    def _parse_and_analyze(self, url: str) -> dict:
        """Парсинг + анализ"""
        # Шаг 1: Парсим
        parse_result = self.parser.parse_url(url)
        if not parse_result.get("success"):
            return parse_result
        
        # Шаг 2: Анализируем
        analysis_result = self.gemini_client.analyze_parsed_content(
            parse_result["title"],
            parse_result["h1"],
            parse_result["screenshot"]
        )
        
        return analysis_result
    
    def on_parse_complete(self, result: dict):
        """Обработка результата парсинга"""
        self.hide_loading()
        if result.get("success") and result.get("analysis"):
            self.show_results(result["analysis"], "parse")
        else:
            self.show_error(result.get("error", "Неизвестная ошибка"))
    
    def on_error(self, error: str):
        """Обработка ошибки"""
        self.hide_loading()
        self.show_error(error)
    
    # === История ===
    
    def load_history(self) -> list:
        """Загрузка истории из JSON"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_to_history(self, request_type: str, analysis: dict):
        """Сохранение в историю"""
        item = {
            "timestamp": datetime.now().isoformat(),
            "request_type": request_type,
            "analysis": analysis
        }
        
        self.history.insert(0, item)
        self.history = self.history[:10]  # Только последние 10
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def load_history_ui(self):
        """Загрузка истории в UI"""
        # Очищаем
        while self.history_layout.count():
            child = self.history_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if self.history:
            for item in self.history:
                frame = QFrame()
                frame.setObjectName("historyItem")
                layout = QHBoxLayout(frame)
                
                icons = {"text": "📝", "image": "🖼️", "parse": "🌐"}
                icon = QLabel(icons.get(item.get("request_type", ""), "📄"))
                icon.setStyleSheet("font-size: 24px;")
                
                content = QWidget()
                content_layout = QVBoxLayout(content)
                content_layout.setContentsMargins(0, 0, 0, 0)
                
                type_labels = {"text": "Анализ текста", "image": "Анализ изображения", "parse": "Парсинг сайта"}
                type_label = QLabel(type_labels.get(item.get("request_type", ""), ""))
                type_label.setStyleSheet("color: #22d3ee; font-size: 12px; font-weight: bold;")
                
                timestamp = item.get("timestamp", "")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%d.%m %H:%M")
                    except:
                        time_str = timestamp[:16]
                else:
                    time_str = ""
                
                time_label = QLabel(time_str)
                time_label.setStyleSheet("color: #64748b; font-size: 12px;")
                
                content_layout.addWidget(type_label)
                content_layout.addWidget(time_label)
                
                layout.addWidget(icon)
                layout.addWidget(content, stretch=1)
                
                self.history_layout.addWidget(frame)
        else:
            empty_label = QLabel("📋 История пуста")
            empty_label.setStyleSheet("color: #64748b; font-size: 16px; padding: 40px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(empty_label)
        
        self.history_layout.addStretch()
    
    def clear_history(self):
        """Очистка истории"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите очистить историю?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history = []
            if self.history_file.exists():
                self.history_file.unlink()
            self.load_history_ui()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
