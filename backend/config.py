"""
Конфигурация приложения
"""

import os
import logging
import sys
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

# === Настройка логирования ===

def setup_logging():
    """Настройка логирования для всего приложения"""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Основной логгер
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Уменьшаем логи от сторонних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("WDM").setLevel(logging.WARNING)
    logging.getLogger("google.generativeai").setLevel(logging.WARNING)
    
    return logging.getLogger("competitor_monitor")

# Инициализация логгера
logger = setup_logging()

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Google Gemini API
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_text_model: str = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash-exp")
    gemini_vision_model: str = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash-exp")
    gemini_audio_model: str = os.getenv("GEMINI_AUDIO_MODEL", "gemini-2.0-flash-exp")
    gemini_generative_model: str = os.getenv("GEMINI_GENERATIVE_MODEL", "imagen-4.0-fast-generate-001")
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # История
    history_file: str = "history.json"
    max_history_items: int = 10
    
    # Парсер
    parser_timeout: int = 10
    parser_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
