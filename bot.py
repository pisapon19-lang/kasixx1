"""
Telegram бот для max.ru - ИСПРАВЛЕННАЯ ВЕРСИЯ ДЛЯ RENDER
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
import os
import stat
import traceback

# ==================== ТВОЙ ТОКЕН ====================
TOKEN = "8556187422:AAEibIikC64cpyXbJMeTljkibtkl7j0fJgs"
URL = "https://web.max.ru"
# ====================================================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальный драйвер
driver = None
user_sessions = {}

def fix_chromedriver_permissions(driver_path):
    """Исправляет права доступа к chromedriver"""
    try:
        # Делаем файл исполняемым
        current_permissions = os.stat(driver_path).st_mode
        os.chmod(driver_path, current_permissions | stat.S_IEXEC)
        logger.info(f"✅ Права доступа исправлены для {driver_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при исправлении прав: {e}")
        return False

def find_correct_chromedriver(base_path):
    """Ищет правильный исполняемый файл chromedriver"""
    try:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file == "chromedriver" and not file.endswith('.chromedriver'):
                    full_path = os.path.join(root, file)
                    logger.info(f"✅ Найден chromedriver: {full_path}")
                    return full_path
    except Exception as e:
        logger.error(f"❌ Ошибка поиска chromedriver: {e}")
    return None

def create_driver():
    """Создает новый драйвер с исправлением ошибки"""
    logger.info("🔄 Начинаю создание драйвера...")
    
    options = Options()
    
    # Критические настройки для Render
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1280x720')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-accelerated-2d-canvas')
    
    try:
        # Получаем путь к драйверу
        logger.info("🔄 Загружаю ChromeDriver...")
        driver_path = ChromeDriverManager().install()
        logger.info(f"📁 ChromeDriver установлен по пути: {driver_path}")
        
        # Исправляем проблему с неправильным файлом
        if 'THIRD_PARTY_NOTICES' in driver_path:
            logger.warning("⚠️ Обнаружен неправильный путь! Ищем правильный chromedriver...")
            base_dir = os.path.dirname(os.path.dirname(driver_path))
            correct_path = find_correct_chromedriver(base_dir)
            
            if correct_path:
                driver_path = correct_path
                logger.info(f"✅ Найден правильный путь: {driver_path}")
            else:
                logger.error("❌ Не удалось найти правильный chromedriver")
                raise Exception("Chromedriver not found")
        
        # Делаем файл исполняемым
        fix_chromedriver_permissions(driver_path)
        
        # Создаем сервис и драйвер
        logger.info("🔄 Запускаю Chrome браузер...")
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        # Проверяем работу
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
    
    msg = await update.message.reply_text("⚡️ Запускаю процесс получения QR-кода...")
    
    try:
        # Закрываем старый драйвер
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        # Создаем новый драйвер
        await msg.edit_text("🔄 Запускаю браузер...")
        driver = create_driver()
        
        # Загружаем страницу
        await msg.edit_text("📱 Загружаю страницу max.ru...")
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
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {traceback.format_exc()}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")
        if driver:
            driver.quit()
            driver = None

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение файла"""
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
        data = driver.execute_script("""
            return {
                deviceId: localStorage.getItem('__oneme_device_id'),
                auth: localStorage.getItem('__oneme_auth')
            };
        """)
        
        if data and data.get('deviceId') and data.get('auth'):
            auth_data = json.loads(data['auth']) if isinstance(data['auth'], str) else {"token": data['auth']}
            phone_number = extract_phone_number(auth_data)
            auth_str = json.dumps(auth_data, indent=2, ensure_ascii=False)
            
            script = f"""sessionStorage.clear();
localStorage.clear();
localStorage.setItem('__oneme_device_id', '{data['deviceId']}');
localStorage.setItem('__oneme_auth', JSON.stringify({auth_str}));
window.location.reload();"""
            
            filename = f"{phone_number}.txt" if phone_number else f"{data['deviceId'][:8]}.txt"
            file_bytes = BytesIO(script.encode('utf-8'))
            file_bytes.name = filename
            
            await msg.delete()
            await update.message.reply_document(
                document=InputFile(file_bytes, filename=filename),
                caption=f"✅ Файл для {'номера ' + phone_number if phone_number else 'аккаунта'}"
            )
            
            if driver:
                driver.quit()
                driver = None
            del user_sessions[user_id]
        else:
            await msg.edit_text("❌ Вход не выполнен. Попробуй /file еще раз")
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "⚡️ **/qr** - QR-код\n"
        "📁 **/file** - файл после входа\n"
        "🔄 **/reset** - сброс",
        parse_mode='Markdown'
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global driver
    user_id = str(update.effective_user.id)
    
    if driver:
        driver.quit()
        driver = None
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text("✅ Браузер сброшен")

def main():
    print("="*60)
    print("🚀 ЗАПУСК БОТА (ИСПРАВЛЕННАЯ ВЕРСИЯ)")
    print("="*60)
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    print("✅ Бот готов!")
    app.run_polling()

if __name__ == "__main__":
    main()
