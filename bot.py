"""
Telegram бот для max.ru - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""

import logging
import asyncio
from io import BytesIO
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time

# Токен из переменных окружения
TOKEN = os.environ.get('TOKEN', '8294429332:AAEQsLd2ZnGM0Z12arZjQZmVK38X1-tJEXY')
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

def get_qr_code_screenshot():
    """Находит QR-код и делает скриншот"""
    global driver
    
    try:
        # Пробуем найти SVG элементы
        svg_elements = driver.find_elements(By.TAG_NAME, "svg")
        logger.info(f"Найдено SVG: {len(svg_elements)}")
        
        # Пробуем каждый SVG
        for i, svg in enumerate(svg_elements):
            try:
                # Проверяем размеры
                width = svg.get_attribute("width")
                height = svg.get_attribute("height")
                logger.info(f"SVG {i}: ширина={width}, высота={height}")
                
                # Пробуем сделать скриншот
                if width and height and int(width) > 0 and int(height) > 0:
                    png = svg.screenshot_as_png
                    if png:
                        img_io = BytesIO(png)
                        img_io.name = "qrcode.png"
                        logger.info(f"QR-код найден в SVG {i}")
                        return img_io
            except Exception as e:
                logger.warning(f"Не удалось сделать скриншот SVG {i}: {e}")
                continue
        
        # Если SVG не подошли, ищем canvas
        canvas_elements = driver.find_elements(By.TAG_NAME, "canvas")
        logger.info(f"Найдено canvas: {len(canvas_elements)}")
        
        for i, canvas in enumerate(canvas_elements):
            try:
                png = canvas.screenshot_as_png
                if png:
                    img_io = BytesIO(png)
                    img_io.name = "qrcode.png"
                    logger.info(f"QR-код найден в canvas {i}")
                    return img_io
            except Exception as e:
                logger.warning(f"Не удалось сделать скриншот canvas {i}: {e}")
                continue
        
        # Если ничего не нашли, делаем скриншот всей страницы
        logger.info("Делаю полный скриншот страницы")
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "page.png"
        return img_io
        
    except Exception as e:
        logger.error(f"Ошибка получения скриншота: {e}")
        return None

def check_authorization():
    """Проверяет, выполнен ли вход на сайт"""
    global driver
    
    try:
        # Проверяем наличие данных авторизации в localStorage
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
        # Ваша команда
        result = driver.execute_script("""
            let deviceId = localStorage.getItem('__oneme_device_id');
            let auth = localStorage.getItem('__oneme_auth');
            
            let result = {
                deviceId: deviceId,
                auth: auth,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href
            };
            
            return result;
        """)
        
        return result
    except Exception as e:
        logger.error(f"Ошибка выполнения команды: {e}")
        return None

async def wait_for_login_and_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    """Ожидает входа и выполняет команду"""
    global driver
    
    try:
        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔄 **Ожидание входа в аккаунт...**\n\nПосле сканирования QR-кода и входа, я автоматически выполню команду.",
            parse_mode='Markdown'
        )
        
        # Ждем входа (проверяем каждые 5 секунд, максимум 3 минуты)
        max_attempts = 36
        for attempt in range(max_attempts):
            await asyncio.sleep(5)
            
            if check_authorization():
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=status_msg.message_id,
                    text="✅ **Вход выполнен!**\n\nВыполняю команду...",
                    parse_mode='Markdown'
                )
                
                result = execute_command_and_get_result()
                
                if result:
                    result_text = f"""📊 **Результат выполнения команды:**

**Device ID:** `{result.get('deviceId', 'не найден')}`

**Auth:** `{result.get('auth', 'не найден')[:50]}...`

**Время входа:** {result.get('timestamp', '')}

**User Agent:** {result.get('userAgent', '')}

**URL:** {result.get('url', '')}"""
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=result_text,
                        parse_mode='Markdown'
                    )
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"🔑 **Полный auth:**\n`{result.get('auth', '')}`",
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Не удалось выполнить команду"
                    )
                
                if user_id in user_sessions:
                    del user_sessions[user_id]
                
                return
            
            if attempt % 6 == 0:
                remaining = (max_attempts - attempt) * 5
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=status_msg.message_id,
                    text=f"🔄 **Ожидание входа...**\n\nВремя ожидания: {remaining} секунд",
                    parse_mode='Markdown'
                )
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text="❌ **Время ожидания истекло**\n\nПопробуйте еще раз с командой /qr",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка в wait_for_login: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Ошибка: {str(e)[:200]}"
        )
    finally:
        if user_id in user_sessions:
            del user_sessions[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для авторизации на max.ru**\n\n"
        "🔹 **/qr** - получить QR-код и ожидать входа\n"
        "🔹 После сканирования QR и входа, я автоматически выполню команду\n"
        "🔹 Результат придет сюда",
        parse_mode='Markdown'
    )

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение QR-кода и ожидание входа"""
    user_id = str(update.effective_user.id)
    
    if user_id in user_sessions:
        await update.message.reply_text("⚠️ У вас уже есть активная сессия. Подождите или отмените предыдущую.")
        return
    
    msg = await update.message.reply_text("🔄 **Получаю QR-код...**", parse_mode='Markdown')
    
    try:
        driver = get_driver()
        
        # Загружаем страницу
        logger.info("Загружаю страницу...")
        driver.get(URL)
        time.sleep(10)  # Увеличил время загрузки
        
        # Получаем QR-код
        img_io = get_qr_code_screenshot()
        
        if img_io:
            await msg.delete()
            
            keyboard = [[InlineKeyboardButton("✅ Я ОТСКАНИРОВАЛ", callback_data="scanned")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_photo(
                photo=InputFile(img_io, filename="qrcode.png"),
                caption="📱 **QR-код получен!**\n\n"
                        "1️⃣ Отсканируйте код\n"
                        "2️⃣ Подтвердите вход на сайте\n"
                        "3️⃣ Нажмите кнопку 'Я ОТСКАНИРОВАЛ'",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            user_sessions[user_id] = {
                'status': 'waiting_qr',
                'message_id': msg.message_id
            }
            
        else:
            await msg.edit_text("❌ Не удалось найти QR-код на странице")
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if query.data == "scanned":
        await query.edit_message_caption(
            caption="✅ **QR-код отсканирован!**\n\n"
                    "⏳ Ожидаю подтверждения входа на сайте...",
            parse_mode='Markdown'
        )
        
        asyncio.create_task(wait_for_login_and_execute(update, context, user_id))

async def main():
    """Главная функция"""
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("✅ Бот запущен!")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        if driver:
            driver.quit()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
