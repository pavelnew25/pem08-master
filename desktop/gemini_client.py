"""
Клиент для прямой работы с Google Gemini API
"""
from google import genai
from google.genai import types
from PIL import Image
import json
import re
from typing import Dict, Any

class GeminiClient:
    """Клиент для Google Gemini 2.0 Flash"""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.text_model = "gemini-2.0-flash-exp"
        self.vision_model = "gemini-2.0-flash-exp"
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Анализ текста конкурента"""
        try:
            prompt = """Ты — эксперт по конкурентному анализу и маркетингу. 
Проанализируй текст конкурента и верни структурированный JSON:

{
  "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
  "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
  "unique_offers": ["уникальное предложение 1", ...],
  "target_audience": ["ЦА 1", "ЦА 2", ...],
  "marketing_insights": ["инсайт 1", "инсайт 2", ...],
  "recommendations": ["рекомендация 1", "рекомендация 2", ...],
  "summary": "краткая суммарная оценка"
}

Текст для анализа:
"""
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt + text
            )
            
            # Парсим JSON из ответа
            data = self._parse_json(response.text)
            
            return {
                "success": True,
                "analysis": {
                    "strengths": data.get("strengths", []),
                    "weaknesses": data.get("weaknesses", []),
                    "unique_offers": data.get("unique_offers", []),
                    "target_audience": data.get("target_audience", []),
                    "marketing_insights": data.get("marketing_insights", []),
                    "recommendations": data.get("recommendations", []),
                    "summary": data.get("summary", "")
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Анализ изображения конкурента"""
        try:
            # Открываем изображение
            image = Image.open(image_path)
            
            prompt = """Ты — эксперт по визуальному маркетингу и дизайну.
Проанализируй изображение конкурента и верни JSON:

{
  "description": "детальное описание что изображено",
  "marketing_insights": ["маркетинговый инсайт 1", "инсайт 2", ...],
  "visual_style_score": 7,
  "visual_style_analysis": "анализ визуального стиля и композиции",
  "color_palette": ["цвет 1", "цвет 2", ...],
  "target_audience": ["ЦА 1", "ЦА 2"],
  "emotional_tone": "эмоциональный тон",
  "recommendations": ["рекомендация 1", "рекомендация 2", ...]
}

visual_style_score от 0 до 10."""
            
            response = self.client.models.generate_content(
                model=self.vision_model,
                contents=[prompt, image]
            )
            
            data = self._parse_json(response.text)
            
            return {
                "success": True,
                "analysis": {
                    "description": data.get("description", ""),
                    "marketing_insights": data.get("marketing_insights", []),
                    "visual_style_score": data.get("visual_style_score", 5),
                    "visual_style_analysis": data.get("visual_style_analysis", ""),
                    "color_palette": data.get("color_palette", []),
                    "target_audience": data.get("target_audience", []),
                    "emotional_tone": data.get("emotional_tone", ""),
                    "recommendations": data.get("recommendations", [])
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_parsed_content(self, title: str, h1: str, screenshot_path: str) -> Dict[str, Any]:
        """Анализ распарсенного контента сайта"""
        try:
            image = Image.open(screenshot_path)
            
            prompt = f"""Ты — эксперт по веб-маркетингу и UX/UI дизайну.
Проанализируй сайт конкурента и верни JSON:

{{
  "strengths": ["сильная сторона 1", ...],
  "weaknesses": ["слабая сторона 1", ...],
  "unique_offers": ["УТП 1", ...],
  "target_audience": ["ЦА 1", ...],
  "marketing_insights": ["инсайт 1", ...],
  "visual_style_score": 7,
  "visual_style_analysis": "анализ визуального стиля",
  "recommendations": ["рекомендация 1", ...]
}}

Title сайта: {title}
H1 заголовок: {h1}

Проанализируй также скриншот сайта."""
            
            response = self.client.models.generate_content(
                model=self.vision_model,
                contents=[prompt, image]
            )
            
            data = self._parse_json(response.text)
            
            return {
                "success": True,
                "analysis": {
                    "strengths": data.get("strengths", []),
                    "weaknesses": data.get("weaknesses", []),
                    "unique_offers": data.get("unique_offers", []),
                    "target_audience": data.get("target_audience", []),
                    "marketing_insights": data.get("marketing_insights", []),
                    "visual_style_score": data.get("visual_style_score", 5),
                    "visual_style_analysis": data.get("visual_style_analysis", ""),
                    "recommendations": data.get("recommendations", [])
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_json(self, content: str) -> dict:
        """Извлечение JSON из markdown или текста"""
        # Пробуем извлечь из markdown
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
        
        # Пробуем найти JSON объект
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)
        
        try:
            return json.loads(content)
        except:
            return {}
