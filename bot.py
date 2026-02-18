"""
Telegram бот для max.ru - БЫСТРЫЙ QR (ИСПРАВЛЕННЫЙ)
"""

import logging
import asyncio
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

# ТОКЕН
TOKEN = "8556187422:AAEibIikC64cpyXbJMeTljkibtkl7j0fJgs"
URL = "https://web.max.ru"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный драйвер
driver = None
user_sessions = {}

def create_driver():
    """Создает новый драйвер"""
    options = Options()
    
    # Оптимизация скорости
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=800x600')
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.page_load_strategy = 'eager'
    
    # Отключаем загрузку картинок
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,
        }
    }
    options.add_experimental_option('prefs', prefs)
    
    return webdriver.Chrome(options=options)

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрое получение QR"""
    global driver  # ОБЯЗАТЕЛЬНО!
    user_id = str(update.effective_user.id)
    
    msg = await update.message.reply_text("⚡️ Получаю QR-код...")
    
    try:
        # Закрываем старый драйвер если есть
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        # Создаем новый
        driver = create_driver()
        
        # Загружаем страницу
        driver.get(URL)
        
        # Ждем немного
        time.sleep(3)
        
        # Делаем скриншот
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "qr.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="qr.png"),
            caption="✅ QR-код готов!\n\n👉 /file - после входа"
        )
        
        user_sessions[user_id] = True
        logger.info(f"QR отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
            driver = None

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение файла со скриптом"""
    global driver  # ОБЯЗАТЕЛЬНО!
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Сначала используй /qr")
        return
    
    if not driver:
        await update.message.reply_text("❌ Браузер не активен. Используй /qr")
        return
    
    msg = await update.message.reply_text("📁 Получаю данные...")
    
    try:
        # Получаем данные из localStorage
        data = driver.execute_script("""
            return {
                deviceId: localStorage.getItem('__oneme_device_id'),
                auth: localStorage.getItem('__oneme_auth')
            };
        """)
        
        if data and data['deviceId'] and data['auth']:
            # Парсим auth
            try:
                auth_data = json.loads(data['auth'])
            except:
                auth_data = {"token": data['auth'], "viewerId": "unknown"}
            
            # Форматируем JSON красиво
            auth_str = json.dumps(auth_data, indent=2, ensure_ascii=False)
            
            # Создаем скрипт
            script = f"""sessionStorage.clear();
localStorage.clear();
localStorage.setItem('__oneme_device_id', '{data['deviceId']}');
localStorage.setItem('__oneme_auth', JSON.stringify({auth_str}));
window.location.reload();"""
            
            # Создаем файл
            file_bytes = BytesIO(script.encode('utf-8'))
            file_bytes.name = "result.txt"
            
            await msg.delete()
            await update.message.reply_document(
                document=InputFile(file_bytes, filename="result.txt"),
                caption="✅ Файл готов!"
            )
            
            logger.info(f"Файл отправлен {user_id}")
            
            # Закрываем браузер
            if driver:
                driver.quit()
                driver = None
            del user_sessions[user_id]
            
        else:
            await msg.edit_text(
                "❌ Вход не выполнен\n\n"
                "1️⃣ Отсканируй QR\n"
                "2️⃣ Войди на сайт\n"
                "3️⃣ Попробуй /file еще раз"
            )
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "⚡️ **/qr** - получить QR-код (быстро)\n"
        "📁 **/file** - получить скрипт после входа\n"
        "🔄 **/reset** - сбросить браузер\n\n"
        "👉 Просто используй /qr и /file",
        parse_mode='Markdown'
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс браузера"""
    global driver  # ОБЯЗАТЕЛЬНО!
    user_id = str(update.effective_user.id)
    
    if driver:
        try:
            driver.quit()
        except:
            pass
        driver = None
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text("✅ Браузер сброшен")

def main():
    """Запуск бота"""
    print("⚡️ Запуск бота...")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    print("✅ Бот готов! Используй /qr")
    app.run_polling()

if __name__ == "__main__":
    main()
