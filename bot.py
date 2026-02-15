"""
Telegram бот для max.ru - ДИАГНОСТИЧЕСКАЯ ВЕРСИЯ
"""

import logging
import asyncio
from io import BytesIO
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os
import time

# Токен из переменных окружения
TOKEN = os.environ.get('TOKEN', '8294429332:AAEQsLd2ZnGM0Z12arZjQZmVK38X1-tJEXY')
URL = "https://web.max.ru"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Диагностическая команда - показывает все элементы на странице"""
    msg = await update.message.reply_text("🔍 Анализирую страницу...")
    
    try:
        driver = get_driver()
        driver.get(URL)
        time.sleep(10)
        
        # Собираем информацию обо всех элементах
        debug_info = "📊 **Анализ страницы:**\n\n"
        
        # SVG элементы
        svg_elements = driver.find_elements(By.TAG_NAME, "svg")
        debug_info += f"**SVG элементов:** {len(svg_elements)}\n"
        for i, svg in enumerate(svg_elements):
            width = svg.get_attribute("width")
            height = svg.get_attribute("height")
            debug_info += f"  {i}: размер {width}x{height}\n"
        
        # Canvas элементы
        canvas_elements = driver.find_elements(By.TAG_NAME, "canvas")
        debug_info += f"\n**Canvas элементов:** {len(canvas_elements)}\n"
        for i, canvas in enumerate(canvas_elements):
            width = canvas.get_attribute("width")
            height = canvas.get_attribute("height")
            debug_info += f"  {i}: размер {width}x{height}\n"
        
        # Картинки
        img_elements = driver.find_elements(By.TAG_NAME, "img")
        debug_info += f"\n**Картинок:** {len(img_elements)}\n"
        for i, img in enumerate(img_elements):
            src = img.get_attribute("src")[:50] + "..." if img.get_attribute("src") else "нет src"
            debug_info += f"  {i}: {src}\n"
        
        # Делаем скриншот всей страницы
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "page.png"
        
        await msg.delete()
        
        # Отправляем анализ
        await update.message.reply_text(debug_info, parse_mode='Markdown')
        
        # Отправляем скриншот страницы
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="page.png"),
            caption="📸 Скриншот всей страницы"
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенная команда получения QR-кода"""
    msg = await update.message.reply_text("🔄 Ищу QR-код...")
    
    try:
        driver = get_driver()
        driver.get(URL)
        time.sleep(10)
        
        # Пробуем разные способы найти QR-код
        
        # 1. Ищем SVG с реальными размерами
        svg_elements = driver.find_elements(By.TAG_NAME, "svg")
        for svg in svg_elements:
            try:
                width = svg.get_attribute("width")
                height = svg.get_attribute("height")
                
                # Пробуем преобразовать в число
                try:
                    w = int(width) if width else 0
                    h = int(height) if height else 0
                except:
                    w, h = 0, 0
                
                if w > 100 and h > 100:  # QR код обычно 200-300px
                    png = svg.screenshot_as_png
                    if png:
                        img_io = BytesIO(png)
                        img_io.name = "qrcode.png"
                        await msg.delete()
                        await update.message.reply_photo(
                            photo=InputFile(img_io, filename="qrcode.png"),
                            caption="✅ QR-код найден (SVG)"
                        )
                        return
            except:
                continue
        
        # 2. Ищем canvas
        canvas_elements = driver.find_elements(By.TAG_NAME, "canvas")
        for canvas in canvas_elements:
            try:
                width = canvas.get_attribute("width")
                height = canvas.get_attribute("height")
                
                if width and height and int(width) > 100 and int(height) > 100:
                    png = canvas.screenshot_as_png
                    if png:
                        img_io = BytesIO(png)
                        img_io.name = "qrcode.png"
                        await msg.delete()
                        await update.message.reply_photo(
                            photo=InputFile(img_io, filename="qrcode.png"),
                            caption="✅ QR-код найден (Canvas)"
                        )
                        return
            except:
                continue
        
        # 3. Если ничего не нашли, показываем скриншот страницы
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "page.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="page.png"),
            caption="⚠️ QR-код не найден. Вот скриншот страницы.\n\nИспользуйте /debug для анализа."
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "🔹 **/qr** - получить QR-код\n"
        "🔹 **/debug** - диагностика страницы\n"
        "🔹 **/help** - помощь"
    )

async def main():
    """Главная функция"""
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("debug", debug_command))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("✅ Диагностический бот запущен!")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        if driver:
            driver.quit()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
