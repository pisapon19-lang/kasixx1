"""
Telegram бот для max.ru - УПРОЩЕННАЯ ВЕРСИЯ
Без Selenium, используем requests
"""

import logging
import asyncio
import random
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
import time
import json
import re
import requests
from requests.auth import HTTPProxyAuth
import urllib3

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ТОКЕН
TOKEN = "8269401428:AAEavNiKkP5d_YyRhHQTqV0C18rm_DbaVE4"
URL = "https://web.max.ru"

# ПРОКСИ СПИСОК (SOCKS5)
PROXIES = [
    {
        'http': 'socks5://SP8lc12fs5:Zmgff17J@185.181.246.198:9101',
        'https': 'socks5://SP8lc12fs5:Zmgff17J@185.181.246.198:9101'
    },
    {
        'http': 'socks5://SP8lc12fs5:Zmgff17J@45.15.72.253:9101',
        'https': 'socks5://SP8lc12fs5:Zmgff17J@45.15.72.253:9101'
    },
    {
        'http': 'socks5://SP8lc12fs5:Zmgff17J@45.11.20.108:9101',
        'https': 'socks5://SP8lc12fs5:Zmgff17J@45.11.20.108:9101'
    }
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Хранилище сессий
user_sessions = {}

def test_proxy(proxy):
    """Тестирует работу прокси"""
    try:
        response = requests.get(
            'https://httpbin.org/ip',
            proxies=proxy,
            timeout=10,
            verify=False
        )
        if response.status_code == 200:
            ip_data = response.json()
            logger.info(f"Прокси работает. IP: {ip_data.get('origin', 'unknown')}")
            return True
    except Exception as e:
        logger.error(f"Прокси не работает: {e}")
    return False

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение QR кода"""
    user_id = str(update.effective_user.id)
    
    msg = await update.message.reply_text("🔍 Проверяю прокси...")
    
    # Проверяем прокси
    working_proxies = []
    for proxy in PROXIES:
        if test_proxy(proxy):
            working_proxies.append(proxy)
    
    if not working_proxies:
        await msg.edit_text(
            "❌ Ни один прокси не работает\n\n"
            "Попробуй:\n"
            "1️⃣ Подключиться через VPN\n"
            "2️⃣ Проверить интернет\n"
            "3️⃣ Использовать другой прокси"
        )
        return
    
    await msg.edit_text(
        f"✅ Найдено {len(working_proxies)} рабочих прокси\n"
        "📱 Но для QR кода нужен браузер...\n\n"
        "⚠️ В Pydroid Selenium не работает.\n\n"
        "Решение:\n"
        "1. Запусти этот код на ПК\n"
        "2. Или используй онлайн сервис\n"
        "3. Или установи Termux"
    )

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о файлах"""
    await update.message.reply_text(
        "📁 **Для получения файла нужно:**\n\n"
        "1️⃣ Запустить бота на ПК\n"
        "2️⃣ Получить QR через /qr\n"
        "3️⃣ Отсканировать QR\n"
        "4️⃣ Использовать /file\n\n"
        "⚠️ В Pydroid браузер не работает",
        parse_mode='Markdown'
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    welcome_text = (
        "👋 **Бот для max.ru**\n\n"
        "⚠️ **Важное предупреждение:**\n"
        "В Pydroid (Android) Selenium не работает!\n\n"
        "**Варианты решения:**\n"
        "💻 **Запусти на ПК**\n"
        "   - Установи Python\n"
        "   - Установи Chrome\n"
        "   - Запусти этот код\n\n"
        "📱 **Termux на Android**\n"
        "   - Установи Termux\n"
        "   - Установи Python\n"
        "   - Установи Chrome\n\n"
        "🌐 **Онлайн сервисы**\n"
        "   - Google Colab\n"
        "   - Replit\n"
        "   - PythonAnywhere\n\n"
        "**Команды:**\n"
        "/qr - проверить прокси\n"
        "/file - информация\n"
        "/proxy - список прокси"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка прокси"""
    msg = await update.message.reply_text("🔍 Проверяю прокси...")
    
    results = []
    for i, proxy in enumerate(PROXIES, 1):
        try:
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxy,
                timeout=10,
                verify=False
            )
            if response.status_code == 200:
                ip = response.json().get('origin', 'unknown')
                results.append(f"✅ Прокси {i}: работает (IP: {ip})")
            else:
                results.append(f"❌ Прокси {i}: не работает")
        except Exception as e:
            results.append(f"❌ Прокси {i}: ошибка - {str(e)[:30]}")
    
    await msg.edit_text(
        "📡 **Результаты проверки прокси:**\n\n" + 
        "\n".join(results) + 
        "\n\n⚠️ Для QR кода нужен браузер, который не работает в Pydroid",
        parse_mode='Markdown'
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс сессии"""
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text("✅ Сессия сброшена")

def main():
    """Запуск бота"""
    print("=" * 60)
    print("🚀 Бот для max.ru (УПРОЩЕННАЯ ВЕРСИЯ)")
    print("=" * 60)
    print(f"✅ Токен: {TOKEN[:10]}...")
    print(f"📡 Прокси: {len(PROXIES)} шт.")
    print("⚠️ Режим: только проверка прокси")
    print("=" * 60)
    print("❌ Selenium НЕ РАБОТАЕТ в Pydroid")
    print("💡 Запусти этот код на ПК")
    print("=" * 60)
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
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
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
