"""
Сервис для работы с Google Gemini API
"""

import json
import re
import time
import logging
import base64
import io
from typing import Optional
from PIL import Image
from google import genai

from backend.config import settings
from backend.models.schemas import CompetitorAnalysis, ImageAnalysis

# Логгер для сервиса
logger = logging.getLogger("competitor_monitor.gemini")

class GeminiService:
    """Сервис для анализа через Google Gemini API"""
    
    def __init__(self):
        logger.info("=" * 50)
        logger.info("Инициализация Gemini сервиса")
        logger.info(f" Модель текста: {settings.gemini_text_model}")
        logger.info(f" Модель vision: {settings.gemini_vision_model}")
        logger.info(f" API ключ: {'*' * 10}...{settings.gemini_api_key[-4:] if settings.gemini_api_key else 'НЕ ЗАДАН'}")
        
        # Создание клиента Gemini API
        self.client = genai.Client(api_key=settings.gemini_api_key)
        
        self.text_model = settings.gemini_text_model
        self.vision_model = settings.gemini_vision_model
        
        logger.info("Gemini сервис инициализирован успешно ✓")
        logger.info("=" * 50)
    
    def _parse_json_response(self, content: str) -> dict:
        """Извлечь JSON из ответа модели"""
        logger.debug(f"Парсинг JSON ответа, длина: {len(content)} символов")
        
        # Пробуем найти JSON в markdown блоке
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
            logger.debug("JSON найден в markdown блоке")
        
        # Пробуем найти JSON объект
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)
            logger.debug("JSON объект извлечён")
        
        try:
            result = json.loads(content)
            logger.debug(f"JSON успешно распарсен, ключей: {len(result)}")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка парсинга JSON: {e}")
            logger.debug(f"Проблемный контент: {content[:200]}...")
            return {}
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int, has_image: bool = False) -> dict:
        """Подсчёт стоимости запроса"""
        # Цены для Gemini 2.0 Flash (Developer API)
        INPUT_TEXT_COST = 0.0000001  # $0.10 per 1M tokens
        OUTPUT_TEXT_COST = 0.0000004  # $0.40 per 1M tokens
        
        input_cost = input_tokens * INPUT_TEXT_COST
        output_cost = output_tokens * OUTPUT_TEXT_COST
        total_cost = input_cost + output_cost
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "model": self.text_model if not has_image else self.vision_model
        }
    
    async def analyze_text(self, text: str) -> CompetitorAnalysis:
        """Анализ текста конкурента"""
        logger.info("=" * 50)
        logger.info("📝 АНАЛИЗ ТЕКСТА КОНКУРЕНТА")
        logger.info(f" Длина текста: {len(text)} символов")
        logger.info(f" Превью: {text[:100]}...")
        logger.info(f" Модель: {self.text_model}")
        
        prompt = f"""Ты — эксперт по конкурентному анализу. Проанализируй предоставленный текст конкурента и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{{
  "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
  "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
  "unique_offers": ["уникальное предложение 1", "уникальное предложение 2", ...],
  "recommendations": ["рекомендация 1", "рекомендация 2", ...],
  "summary": "Краткое резюме анализа"
}}

Важно:
- Каждый массив должен содержать 3-5 пунктов
- Пиши на русском языке
- Будь конкретен и практичен в рекомендациях

Проанализируй текст конкурента:

{text}"""
        
        start_time = time.time()
        logger.info(" Отправка запроса к Gemini API...")
        
        try:
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt
            )
            
            elapsed = time.time() - start_time
            logger.info(f" ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.text
            logger.info(f" Длина ответа: {len(content)} символов")
            
            # Получаем usage данные
            usage = response.usage_metadata if hasattr(response, 'usage_metadata') else None
            if usage:
                input_tokens = usage.prompt_token_count
                output_tokens = usage.candidates_token_count
                cost_info = self._calculate_cost(input_tokens, output_tokens)
                
                logger.info(f" 💰 Использовано токенов:")
                logger.info(f"    Input: {cost_info['input_tokens']} токенов (${cost_info['input_cost_usd']})")
                logger.info(f"    Output: {cost_info['output_tokens']} токенов (${cost_info['output_cost_usd']})")
                logger.info(f"    Итого: {cost_info['total_tokens']} токенов (${cost_info['total_cost_usd']})")
            
            data = self._parse_json_response(content)
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                recommendations=data.get("recommendations", []),
                summary=data.get("summary", "")
            )
            
            logger.info(f" Результат: {len(result.strengths)} сильных, {len(result.weaknesses)} слабых сторон")
            logger.info("=" * 50)
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f" ✗ Ошибка Gemini API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_image(self, image_base64: str, mime_type: str = "image/jpeg") -> ImageAnalysis:
        """Анализ изображения (баннер, сайт, упаковка)"""
        logger.info("=" * 50)
        logger.info("🖼️ АНАЛИЗ ИЗОБРАЖЕНИЯ")
        logger.info(f" Размер base64: {len(image_base64)} символов")
        logger.info(f" MIME тип: {mime_type}")
        logger.info(f" Модель: {self.vision_model}")
        
        # Декодируем base64 в изображение PIL
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        prompt = """Ты — эксперт по визуальному маркетингу и дизайну. Проанализируй изображение конкурента (баннер, сайт, упаковка товара и т.д.) и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{
  "description": "Детальное описание того, что изображено",
  "marketing_insights": ["инсайт 1", "инсайт 2", ...],
  "visual_style_score": 7,
  "visual_style_analysis": "Анализ визуального стиля конкурента",
  "recommendations": ["рекомендация 1", "рекомендация 2", ...]
}

Важно:
- visual_style_score от 0 до 10
- Каждый массив должен содержать 3-5 пунктов
- Пиши на русском языке
- Оценивай: цветовую палитру, типографику, композицию, UX/UI элементы

Проанализируй это изображение конкурента с точки зрения маркетинга и дизайна."""
        
        start_time = time.time()
        logger.info(" Отправка запроса к Gemini Vision API...")
        
        try:
            response = self.client.models.generate_content(
                model=self.vision_model,
                contents=[prompt, image]
            )
            
            elapsed = time.time() - start_time
            logger.info(f" ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.text
            logger.info(f" Длина ответа: {len(content)} символов")
            
            # Получаем usage данные
            usage = response.usage_metadata if hasattr(response, 'usage_metadata') else None
            if usage:
                input_tokens = usage.prompt_token_count
                output_tokens = usage.candidates_token_count
                cost_info = self._calculate_cost(input_tokens, output_tokens, has_image=True)
                
                logger.info(f" 💰 Использовано токенов:")
                logger.info(f"    Input: {cost_info['input_tokens']} токенов (${cost_info['input_cost_usd']})")
                logger.info(f"    Output: {cost_info['output_tokens']} токенов (${cost_info['output_cost_usd']})")
                logger.info(f"    Итого: {cost_info['total_tokens']} токенов (${cost_info['total_cost_usd']})")
            
            data = self._parse_json_response(content)
            
            result = ImageAnalysis(
                description=data.get("description", ""),
                marketing_insights=data.get("marketing_insights", []),
                visual_style_score=data.get("visual_style_score", 5),
                visual_style_analysis=data.get("visual_style_analysis", ""),
                recommendations=data.get("recommendations", [])
            )
            
            logger.info(f" Результат: оценка стиля {result.visual_style_score}/10")
            logger.info(f" Инсайтов: {len(result.marketing_insights)}, рекомендаций: {len(result.recommendations)}")
            logger.info("=" * 50)
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f" ✗ Ошибка Gemini Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_parsed_content(
        self,
        title: Optional[str],
        h1: Optional[str],
        paragraph: Optional[str]
    ) -> CompetitorAnalysis:
        """Анализ распарсенного контента сайта"""
        logger.info("📄 Анализ распарсенного контента")
        logger.info(f" Title: {title[:50] if title else 'N/A'}...")
        logger.info(f" H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f" Абзац: {paragraph[:50] if paragraph else 'N/A'}...")
        
        content_parts = []
        if title:
            content_parts.append(f"Заголовок страницы (title): {title}")
        if h1:
            content_parts.append(f"Главный заголовок (H1): {h1}")
        if paragraph:
            content_parts.append(f"Первый абзац: {paragraph}")
        
        combined_text = "\n\n".join(content_parts)
        
        if not combined_text.strip():
            logger.warning(" ⚠ Контент пустой, возвращаем пустой анализ")
            return CompetitorAnalysis(
                summary="Не удалось извлечь контент для анализа"
            )
        
        return await self.analyze_text(combined_text)
    
    async def analyze_website_screenshot(
        self,
        screenshot_base64: str,
        url: str,
        title: Optional[str] = None,
        h1: Optional[str] = None,
        first_paragraph: Optional[str] = None
    ) -> CompetitorAnalysis:
        """Комплексный анализ сайта конкурента по скриншоту"""
        logger.info("=" * 50)
        logger.info("🌐 КОМПЛЕКСНЫЙ АНАЛИЗ САЙТА")
        logger.info(f" URL: {url}")
        logger.info(f" Title: {title[:50] if title else 'N/A'}...")
        logger.info(f" H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f" Размер скриншота: {len(screenshot_base64)} символов base64")
        logger.info(f" Модель: {self.vision_model}")
        
        # Декодируем base64 в изображение PIL
        image_data = base64.b64decode(screenshot_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Формируем контекст из извлечённых данных
        context_parts = [f"URL сайта: {url}"]
        if title:
            context_parts.append(f"Title страницы: {title}")
        if h1:
            context_parts.append(f"Главный заголовок (H1): {h1}")
        if first_paragraph:
            context_parts.append(f"Текст на странице: {first_paragraph[:300]}")
        
        context = "\n".join(context_parts)
        logger.debug(f" Контекст:\n{context}")
        
        prompt = f"""Ты — эксперт по конкурентному анализу и UX/UI дизайну. Проанализируй скриншот сайта конкурента и верни структурированный JSON-ответ.

Формат ответа (строго JSON):
{{
  "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
  "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
  "unique_offers": ["уникальное предложение/фича 1", "уникальное предложение/фича 2", ...],
  "recommendations": ["рекомендация 1", "рекомендация 2", ...],
  "summary": "Комплексное резюме анализа сайта конкурента"
}}

При анализе обращай внимание на:
- Дизайн и визуальный стиль (цвета, шрифты, композиция)
- UX/UI: навигация, расположение элементов, CTA кнопки
- Контент: заголовки, тексты, призывы к действию
- Уникальные торговые предложения (УТП)
- Целевая аудитория (на кого ориентирован сайт)
- Технологичность и современность дизайна

Важно:
- Каждый массив должен содержать 4-6 конкретных пунктов
- Пиши на русском языке
- Будь конкретен и практичен
- Давай actionable рекомендации

Проведи комплексный конкурентный анализ этого сайта:

{context}"""
        
        start_time = time.time()
        logger.info(" Отправка скриншота в Gemini Vision API...")
        
        try:
            response = self.client.models.generate_content(
                model=self.vision_model,
                contents=[prompt, image]
            )
            
            elapsed = time.time() - start_time
            logger.info(f" ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.text
            logger.info(f" Длина ответа: {len(content)} символов")
            
            # Получаем usage данные
            usage = response.usage_metadata if hasattr(response, 'usage_metadata') else None
            if usage:
                input_tokens = usage.prompt_token_count
                output_tokens = usage.candidates_token_count
                cost_info = self._calculate_cost(input_tokens, output_tokens, has_image=True)
                
                logger.info(f" 💰 Использовано токенов:")
                logger.info(f"    Input: {cost_info['input_tokens']} токенов (${cost_info['input_cost_usd']})")
                logger.info(f"    Output: {cost_info['output_tokens']} токенов (${cost_info['output_cost_usd']})")
                logger.info(f"    Итого: {cost_info['total_tokens']} токенов (${cost_info['total_cost_usd']})")
            
            data = self._parse_json_response(content)
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                recommendations=data.get("recommendations", []),
                summary=data.get("summary", "")
            )
            
            logger.info(f" Результат:")
            logger.info(f" - Сильных сторон: {len(result.strengths)}")
            logger.info(f" - Слабых сторон: {len(result.weaknesses)}")
            logger.info(f" - УТП: {len(result.unique_offers)}")
            logger.info(f" - Рекомендаций: {len(result.recommendations)}")
            logger.info(f" Резюме: {result.summary[:100]}...")
            logger.info("=" * 50)
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f" ✗ Ошибка Gemini Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise

# Глобальный экземпляр
logger.info("Создание глобального экземпляра Gemini сервиса...")
gemini_service = GeminiService()
