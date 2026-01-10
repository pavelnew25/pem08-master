"""
Парсер сайтов с помощью Selenium
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import tempfile
from typing import Dict, Any

class WebParser:
    """Парсер для извлечения данных с сайтов"""
    
    def __init__(self):
        self.options = Options()
        self.options.add_argument('--headless=new')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-software-rasterizer')
        self.options.page_load_strategy = 'eager'
        
        # Отключаем изображения для скорости
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'profile.default_content_setting_values.notifications': 2
        }
        self.options.add_experimental_option('prefs', prefs)
    
    def parse_url(self, url: str) -> Dict[str, Any]:
        """Парсинг URL сайта"""
        driver = None
        screenshot_path = None
        
        try:
            # Добавляем протокол если нет
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            driver = webdriver.Chrome(options=self.options)
            driver.set_page_load_timeout(30)
            
            # Загружаем страницу
            driver.get(url)
            
            # Ждём загрузки body
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Извлекаем данные
            title = driver.title or "Без заголовка"
            
            try:
                h1 = driver.find_element(By.TAG_NAME, "h1").text
            except NoSuchElementException:
                h1 = "H1 не найден"
            
            # Делаем скриншот
            screenshot_path = os.path.join(
                tempfile.gettempdir(), 
                f"screenshot_{hash(url)}.png"
            )
            driver.save_screenshot(screenshot_path)
            
            return {
                "success": True,
                "title": title,
                "h1": h1,
                "screenshot": screenshot_path,
                "url": url
            }
            
        except TimeoutException:
            return {
                "success": False,
                "error": "Превышено время ожидания загрузки страницы"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if driver:
                driver.quit()
