"""
Telegram бот для max.ru - ПОЛНАЯ ВЕРСИЯ ДЛЯ ПК
"""

import logging
import os
import sys
import time
import json
import re
import random
from io import BytesIO
from datetime import datetime

# Telegram
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = "8269401428:AAEavNiKkP5d_YyRhHQTqV0C18rm_DbaVE4"
URL = "https://web.max.ru"

# Прокси SOCKS5
PROXIES = [
    "socks5://SP8lc12fs5:Zmgff17J@185.181.246.198:9101",
    "socks5://SP8lc12fs5:Zmgff17J@45.15.72.253:9101",
    "socks5://SP8lc12fs5:Zmgff17J@45.11.20.108:9101"
]

# Путь к ChromeDriver (если в той же папке)
CHROME_DRIVER_PATH = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
# ==================================

# Глобальные переменные
driver = None
user_sessions = {}

def create_driver(proxy=None):
    """Создает драйвер Chrome с настройками"""
    options = Options()
    
    # Основные настройки
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280x720')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Отключаем картинки для скорости
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,
            'javascript': 1,
            'cookies': 1,
            'plugins': 2,
            'popups': 2
        }
    }
    options.add_experimental_option('prefs', prefs)
    
    # Прокси
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
        logger.info(f"Использую прокси")
    
    # Путь к ChromeDriver
    if os.path.exists(CHROME_DRIVER_PATH):
        service = Service(executable_path=CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Если chromedriver.exe нет в папке, используем системный PATH
        driver = webdriver.Chrome(options=options)
    
    # Убираем признаки автоматизации
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extract_phone_number(auth_data):
    """Извлекает номер телефона из auth данных"""
    try:
        if isinstance(auth_data, str):
            data = json.loads(auth_data)
        else:
            data = auth_data
        
        phone = None
        
        # Поиск номера в разных полях
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
    
    msg = await update.message.reply_text("🔄 Запускаю браузер...")
    
    # Закрываем старый драйвер если есть
    if driver:
        try:
            driver.quit()
        except:
            pass
        driver = None
    
    # Пробуем прокси по очереди
    for i, proxy in enumerate(PROXIES, 1):
        try:
            await msg.edit_text(f"🔄 Попытка {i} из {len(PROXIES)}...")
            
            driver = create_driver(proxy)
            driver.set_page_load_timeout(30)
            
            # Загружаем страницу
            driver.get(URL)
            
            # Ждем загрузки QR
            time.sleep(5)
            
            # Проверяем наличие QR
            page_source = driver.page_source.lower()
            if "qr" in page_source or "qrcode" in page_source:
                # Делаем скриншот
                screenshot = driver.get_screenshot_as_png()
                img_io = BytesIO(screenshot)
                img_io.name = "qr.png"
                
                await msg.delete()
                await update.message.reply_photo(
                    photo=InputFile(img_io, filename="qr.png"),
                    caption=(
                        "✅ **QR-код получен!**\n\n"
                        "📱 **Инструкция:**\n"
                        "1️⃣ Отсканируй QR в приложении max.ru\n"
                        "2️⃣ Подтверди вход в приложении\n"
                        "3️⃣ Отправь /file для получения данных\n\n"
                        f"🌐 Прокси: {i}/{len(PROXIES)}"
                    ),
                    parse_mode='Markdown'
                )
                
                user_sessions[user_id] = {
                    'active': True,
                    'time': time.time()
                }
                return
            else:
                await msg.edit_text(f"⚠️ QR не найден, пробую другой прокси...")
                
        except Exception as e:
            logger.error(f"Ошибка с прокси {i}: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None
            continue
    
    # Если ничего не помогло
    await msg.edit_text(
        "❌ **Не удалось получить QR-код**\n\n"
        "**Возможные причины:**\n"
        "• Все прокси не работают\n"
        "• Сайт max.ru недоступен\n"
        "• Блокировка по IP\n\n"
        "**Попробуй:**\n"
        "• /reset - сбросить\n"
        "• Подождать 5 минут\n"
        "• Использовать VPN на ПК",
        parse_mode='Markdown'
    )

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение файла с данными"""
    global driver
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text(
            "❌ **Сначала получи QR-код**\n"
            "Используй команду /qr",
            parse_mode='Markdown'
        )
        return
    
    if not driver:
        await update.message.reply_text(
            "❌ **Браузер не активен**\n"
            "Используй /qr заново",
            parse_mode='Markdown'
        )
        if user_id in user_sessions:
            del user_sessions[user_id]
        return
    
    msg = await update.message.reply_text("📁 **Получаю данные...**", parse_mode='Markdown')
    
    try:
        # Ждем загрузки
        time.sleep(3)
        
        # Получаем данные из localStorage
        data = driver.execute_script("""
            try {
                return {
                    deviceId: localStorage.getItem('__oneme_device_id'),
                    auth: localStorage.getItem('__oneme_auth'),
                    url: window.location.href,
                    title: document.title
                };
            } catch(e) {
                return {deviceId: null, auth: null, url: null, title: null};
            }
        """)
        
        if data and data.get('deviceId') and data.get('auth'):
            # Парсим auth
            try:
                auth_data = json.loads(data['auth'])
            except:
                auth_data = {"token": data['auth'], "viewerId": "unknown"}
            
            # Извлекаем номер
            phone_number = extract_phone_number(auth_data)
            
            # Форматируем JSON
            auth_str = json.dumps(auth_data, indent=2, ensure_ascii=False)
            
            # Создаем скрипт
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            script = f"""// MAX.RU Авторизация
// Создано: {timestamp}
// Номер: {phone_number if phone_number else 'не найден'}

// 1. Очищаем старые данные
sessionStorage.clear();
localStorage.clear();

// 2. Устанавливаем новые данные
localStorage.setItem('__oneme_device_id', '{data['deviceId']}');
localStorage.setItem('__oneme_auth', JSON.stringify({auth_str}));

// 3. Перезагружаем страницу
window.location.reload();

console.log('✅ Готово! Авторизация выполнена');
"""
            
            # Имя файла
            if phone_number:
                filename = f"max_{phone_number}.txt"
                caption = f"✅ **Файл для номера**\n`+7{phone_number}`"
            else:
                filename = f"max_{data['deviceId'][:8]}.txt"
                caption = "✅ **Файл готов** (номер не определен)"
            
            # Отправляем файл
            file_bytes = BytesIO(script.encode('utf-8'))
            file_bytes.name = filename
            
            await msg.delete()
            await update.message.reply_document(
                document=InputFile(file_bytes, filename=filename),
                caption=caption,
                parse_mode='Markdown'
            )
            
            logger.info(f"Файл {filename} отправлен пользователю {user_id}")
            
            # Закрываем браузер
            if driver:
                driver.quit()
                driver = None
            if user_id in user_sessions:
                del user_sessions[user_id]
                
        else:
            await msg.edit_text(
                "❌ **Данные не найдены**\n\n"
                "**Проверь:**\n"
                "✅ QR отсканирован?\n"
                "✅ Вход подтвержден в приложении?\n"
                "✅ Страница загружена?\n\n"
                "**Попробуй:**\n"
                "1️⃣ /qr - новый QR\n"
                "2️⃣ Войти заново\n"
                "3️⃣ /file снова",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(
            f"❌ **Ошибка:**\n`{str(e)[:100]}`\n\n"
            "Используй /qr заново",
            parse_mode='Markdown'
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    text = (
        "👋 **Бот для MAX.RU**\n\n"
        "**📱 Как пользоваться:**\n"
        "1️⃣ /qr - получить QR-код\n"
        "2️⃣ Отсканировать в приложении MAX\n"
        "3️⃣ /file - скачать файл с номером\n\n"
        "**⚙️ Команды:**\n"
        "• /qr - новый QR-код\n"
        "• /file - файл с данными\n"
        "• /proxy - список прокси\n"
        "• /reset - сброс браузера\n"
        "• /help - помощь\n\n"
        f"**🌐 Прокси:** {len(PROXIES)} шт.\n"
        "**✅ Статус:** Работает на ПК"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о прокси"""
    text = "📡 **Доступные прокси:**\n\n"
    for i, proxy in enumerate(PROXIES, 1):
        text += f"• Прокси {i}: SOCKS5\n"
    text += f"\nВсего: {len(PROXIES)} прокси\n"
    text += "Статус: ✅ Активны"
    await update.message.reply_text(text, parse_mode='Markdown')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс браузера"""
    global driver
    user_id = str(update.effective_user.id)
    
    if driver:
        try:
            driver.quit()
        except:
            pass
        driver = None
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text("✅ **Браузер сброшен**", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    await start(update, context)

def main():
    """Запуск бота"""
    print("=" * 60)
    print("🚀 БОТ ДЛЯ MAX.RU (ПК ВЕРСИЯ)")
    print("=" * 60)
    print(f"✅ Токен: {TOKEN[:10]}...")
    print(f"📁 Папка: {os.path.dirname(__file__)}")
    print(f"🌐 Прокси: {len(PROXIES)}")
    
    # Проверяем ChromeDriver
    if os.path.exists(CHROME_DRIVER_PATH):
        print(f"✅ ChromeDriver найден: {CHROME_DRIVER_PATH}")
    else:
        print("⚠️ ChromeDriver должен быть в PATH")
    
    print("=" * 60)
    print("🔄 Запуск бота...")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(CommandHandler("proxy", proxy_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    print("✅ Бот запущен!")
    print("📱 Нажми Ctrl+C для остановки")
    print("=" * 60)
    
    # Запускаем
    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
