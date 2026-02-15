"""
Telegram бот для max.ru - ПРОСТАЯ ВЕРСИЯ
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
        "👋 Бот для max.ru\n\n"
        "/qr - получить скриншот\n"
        "/check - проверить вход"
    )

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    msg = await update.message.reply_text("Загружаю страницу...")
    
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
        await msg.edit_text(f"Ошибка: {e}")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("Сначала используй /qr")
        return
    
    msg = await update.message.reply_text("Проверяю вход...")
    
    try:
        # Проверяем авторизацию
        has_auth = driver.execute_script("""
            return localStorage.getItem('__oneme_auth') !== null;
        """)
        
        if has_auth:
            # Получаем данные
            result = driver.execute_script("""
                return {
                    deviceId: localStorage.getItem('__oneme_device_id'),
                    auth: localStorage.getItem('__oneme_auth')
                };
            """)
            
            await msg.delete()
            await update.message.reply_text(
                f"✅ Вход выполнен!\n\n"
                f"Device ID: {result.get('deviceId', '')}\n\n"
                f"Auth: {result.get('auth', '')}"
            )
            
            del user_sessions[user_id]
        else:
            await msg.edit_text("❌ Вход не выполнен. Попробуй /check еще раз")
            
    except Exception as e:
        await msg.edit_text(f"Ошибка: {e}")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("check", check_command))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("Бот запущен!")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())