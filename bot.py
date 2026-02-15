"""
Telegram бот для max.ru - ОТПРАВКА В .TXT ФАЙЛЕ
"""

import logging
import asyncio
from io import BytesIO, StringIO
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
    # Форматируем точно как в примере
    script = f"sessionStorage.clear();localStorage.clear();localStorage.setItem('__oneme_device_id', '{device_id}');localStorage.setItem('__oneme_auth', '{auth}');window.location.reload();"
    return script

def create_txt_file(device_id, auth, script):
    """Создает txt файл с результатом"""
    content = f"""{script}"""
    
    txt_io = StringIO()
    txt_io.write(content)
    txt_io.seek(0)
    
    # Конвертируем в BytesIO для отправки
    bytes_io = BytesIO(txt_io.read().encode('utf-8'))
    bytes_io.name = "result.txt"
    
    return bytes_io

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 Бот для max.ru\n\n"
        "/qr - получить скриншот\n"
        "/check - получить результат в .txt"
    )

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение скриншота"""
    user_id = str(update.effective_user.id)
    
    msg = await update.message.reply_text("🔄 Загружаю страницу...")
    
    try:
        driver = get_driver()
        driver.get(URL)
        time.sleep(15)
        
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "page.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="page.png"),
            caption="Скриншот готов. Отсканируй QR и напиши /check"
        )
        
        user_sessions[user_id] = True
        
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка входа и отправка .txt файла"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Сначала используй /qr")
        return
    
    msg = await update.message.reply_text("🔄 Проверяю вход...")
    
    try:
        if check_authorization():
            data = get_auth_data()
            
            if data and data.get('deviceId') and data.get('auth'):
                device_id = data['deviceId']
                auth = data['auth']
                
                # Создаем скрипт
                script = format_script(device_id, auth)
                
                # Создаем txt файл
                txt_file = create_txt_file(device_id, auth, script)
                
                await msg.delete()
                
                # Отправляем только txt файл
                await update.message.reply_document(
                    document=InputFile(txt_file, filename="result.txt")
                )
                
                del user_sessions[user_id]
            else:
                await msg.edit_text("❌ Ошибка получения данных")
        else:
            await msg.edit_text("❌ Вход не выполнен. Попробуй /check еще раз")
            
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

async def main():
    """Главная функция"""
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("check", check_command))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("✅ Бот запущен! Отправляет результат в .txt")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        if driver:
            driver.quit()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
