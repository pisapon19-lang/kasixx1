"""
Telegram бот для max.ru - ИСПОЛЬЗУЕМ maxapi-python
"""

import logging
import os
import sys
import time
import json
import re
import asyncio
from io import BytesIO
from datetime import datetime

# Telegram
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes

# MAX API
try:
    from maxapi_python import MaxAPI
    from maxapi_python.utils import ProxyManager
    MAXAPI_AVAILABLE = True
except ImportError:
    MAXAPI_AVAILABLE = False
    print("⚠️ maxapi-python не установлен. Установи: pip install maxapi-python")

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

# Прокси SOCKS5 для MAX API
PROXIES = [
    {
        'proxy_type': 'socks5',
        'addr': '185.181.246.198',
        'port': 9101,
        'username': 'SP8lc12fs5',
        'password': 'Zmgff17J'
    },
    {
        'proxy_type': 'socks5',
        'addr': '45.15.72.253',
        'port': 9101,
        'username': 'SP8lc12fs5',
        'password': 'Zmgff17J'
    },
    {
        'proxy_type': 'socks5',
        'addr': '45.11.20.108',
        'port': 9101,
        'username': 'SP8lc12fs5',
        'password': 'Zmgff17J'
    }
]
# ==================================

# Глобальные переменные
api_clients = {}
user_sessions = {}

class MaxAPIBot:
    def __init__(self, proxy_config=None):
        """Инициализация MAX API с прокси"""
        self.proxy_config = proxy_config
        self.api = None
        self.device_id = None
        self.auth_data = None
        
        if proxy_config:
            logger.info(f"Инициализация MAX API с прокси: {proxy_config['addr']}:{proxy_config['port']}")
        else:
            logger.info("Инициализация MAX API без прокси")
    
    def initialize(self):
        """Создает экземпляр MAX API"""
        try:
            if self.proxy_config:
                # Создаем прокси менеджер
                proxy_manager = ProxyManager(
                    proxy_type=self.proxy_config['proxy_type'],
                    addr=self.proxy_config['addr'],
                    port=self.proxy_config['port'],
                    username=self.proxy_config.get('username'),
                    password=self.proxy_config.get('password')
                )
                
                # Создаем API с прокси
                self.api = MaxAPI(proxy=proxy_manager.get_proxy())
            else:
                # Создаем API без прокси
                self.api = MaxAPI()
            
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации MAX API: {e}")
            return False
    
    def get_qr(self):
        """Получает QR-код через MAX API"""
        try:
            if not self.api:
                if not self.initialize():
                    return None, "Не удалось инициализировать API"
            
            # Получаем QR-код
            qr_data = self.api.get_qr()
            
            if qr_data and 'qr_code' in qr_data:
                self.device_id = qr_data.get('device_id')
                return qr_data['qr_code'], None
            else:
                return None, "QR-код не получен"
                
        except Exception as e:
            logger.error(f"Ошибка получения QR: {e}")
            return None, str(e)
    
    def wait_for_auth(self, timeout=60):
        """Ожидает авторизацию"""
        try:
            if not self.api:
                return False, "API не инициализирован"
            
            # Ожидаем авторизацию
            auth_result = self.api.wait_for_auth(timeout=timeout)
            
            if auth_result and auth_result.get('success'):
                self.auth_data = auth_result
                return True, auth_result
            else:
                return False, "Авторизация не выполнена"
                
        except Exception as e:
            logger.error(f"Ошибка ожидания авторизации: {e}")
            return False, str(e)
    
    def get_auth_data(self):
        """Возвращает данные авторизации"""
        return {
            'device_id': self.device_id,
            'auth_data': self.auth_data
        }
    
    def extract_phone(self):
        """Извлекает номер телефона из данных авторизации"""
        try:
            if not self.auth_data:
                return None
            
            phone = None
            
            # Поиск номера в разных полях
            if 'phone' in self.auth_data:
                phone = self.auth_data['phone']
            elif 'user' in self.auth_data and isinstance(self.auth_data['user'], dict):
                if 'phone' in self.auth_data['user']:
                    phone = self.auth_data['user']['phone']
            elif 'profile' in self.auth_data and isinstance(self.auth_data['profile'], dict):
                if 'phone' in self.auth_data['profile']:
                    phone = self.auth_data['profile']['phone']
            
            if phone:
                # Очищаем номер
                phone = re.sub(r'\D', '', str(phone))
                if len(phone) > 10:
                    phone = phone[-10:]
                return phone
            
            return None
        except Exception as e:
            logger.error(f"Ошибка извлечения номера: {e}")
            return None
    
    def generate_script(self):
        """Генерирует скрипт для входа"""
        if not self.device_id or not self.auth_data:
            return None
        
        phone = self.extract_phone() or "неизвестный"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        script = f"""// MAX.RU Авторизация через MAX API
// Создано: {timestamp}
// Номер: {phone}

// Данные для входа
const DEVICE_ID = '{self.device_id}';
const AUTH_DATA = {json.dumps(self.auth_data, indent=2, ensure_ascii=False)};

// Очищаем старые данные
sessionStorage.clear();
localStorage.clear();

// Устанавливаем новые данные
localStorage.setItem('__oneme_device_id', DEVICE_ID);
localStorage.setItem('__oneme_auth', JSON.stringify(AUTH_DATA));

// Перезагружаем страницу
window.location.reload();

console.log('✅ Авторизация выполнена для номера', '{phone}');
"""
        return script

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    text = (
        "👋 **Бот для MAX.RU (через maxapi-python)**\n\n"
        "**📱 Как пользоваться:**\n"
        "1️⃣ /qr - получить QR-код\n"
        "2️⃣ Отсканировать в приложении MAX\n"
        "3️⃣ /file - скачать файл с номером\n\n"
        "**⚙️ Команды:**\n"
        "• /qr - новый QR-код\n"
        "• /file - файл с данными\n"
        "• /proxy - список прокси\n"
        "• /reset - сброс сессии\n"
        "• /status - статус API\n\n"
        f"**📡 Прокси:** {len(PROXIES)} шт.\n"
        "**✅ Библиотека:** maxapi-python"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение QR-кода через MAX API"""
    user_id = str(update.effective_user.id)
    
    if not MAXAPI_AVAILABLE:
        await update.message.reply_text(
            "❌ **maxapi-python не установлен**\n\n"
            "Установи библиотеку:\n"
            "`pip install maxapi-python`",
            parse_mode='Markdown'
        )
        return
    
    msg = await update.message.reply_text("🔄 **Инициализация MAX API...**", parse_mode='Markdown')
    
    # Выбираем случайный прокси
    proxy_config = random.choice(PROXIES) if PROXIES else None
    
    # Создаем клиент
    client = MaxAPIBot(proxy_config)
    
    # Получаем QR
    await msg.edit_text("🔄 **Получение QR-кода...**", parse_mode='Markdown')
    qr_data, error = client.get_qr()
    
    if error:
        await msg.edit_text(
            f"❌ **Ошибка:**\n`{error}`\n\n"
            "Попробуй другой прокси или /reset",
            parse_mode='Markdown'
        )
        return
    
    if qr_data:
        # Сохраняем клиента в сессию
        user_sessions[user_id] = {
            'client': client,
            'time': time.time()
        }
        
        # Отправляем QR
        try:
            # Если qr_data это строка с base64 изображением
            if isinstance(qr_data, str) and qr_data.startswith('data:image'):
                import base64
                # Извлекаем base64 данные
                base64_data = qr_data.split(',')[1]
                qr_bytes = base64.b64decode(base64_data)
                img_io = BytesIO(qr_bytes)
                img_io.name = "qr.png"
            else:
                # Если это уже байты
                img_io = BytesIO(qr_data)
                img_io.name = "qr.png"
            
            await msg.delete()
            await update.message.reply_photo(
                photo=InputFile(img_io, filename="qr.png"),
                caption=(
                    "✅ **QR-код получен!**\n\n"
                    "📱 **Инструкция:**\n"
                    "1️⃣ Отсканируй QR в приложении MAX\n"
                    "2️⃣ Подтверди вход\n"
                    "3️⃣ Отправь /file для получения данных\n\n"
                    f"🌐 Прокси: {proxy_config['addr'] if proxy_config else 'без прокси'}"
                ),
                parse_mode='Markdown'
            )
            
            # Запускаем ожидание авторизации в фоне
            asyncio.create_task(wait_for_auth_task(user_id, update.effective_chat.id))
            
        except Exception as e:
            logger.error(f"Ошибка отправки QR: {e}")
            await msg.edit_text(f"❌ Ошибка отправки QR: {e}")
    else:
        await msg.edit_text("❌ Не удалось получить QR-код")

async def wait_for_auth_task(user_id, chat_id):
    """Фоновая задача ожидания авторизации"""
    await asyncio.sleep(2)
    
    if user_id in user_sessions:
        client = user_sessions[user_id]['client']
        
        # Ожидаем авторизацию
        success, result = client.wait_for_auth(timeout=60)
        
        if success:
            # Уведомляем пользователя
            try:
                phone = client.extract_phone()
                phone_text = f" для номера +7{phone}" if phone else ""
                
                await Application.builder().token(TOKEN).build().bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Авторизация выполнена{phone_text}!**\n📁 Используй /file для получения файла",
                    parse_mode='Markdown'
                )
            except:
                pass

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение файла с данными"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text(
            "❌ **Сначала получи QR-код**\n"
            "Используй команду /qr",
            parse_mode='Markdown'
        )
        return
    
    msg = await update.message.reply_text("📁 **Генерация файла...**", parse_mode='Markdown')
    
    client = user_sessions[user_id]['client']
    
    # Проверяем, есть ли данные авторизации
    if not client.auth_data:
        # Пробуем еще раз подождать
        success, result = client.wait_for_auth(timeout=10)
        if not success:
            await msg.edit_text(
                "❌ **Авторизация не выполнена**\n\n"
                "1️⃣ Отсканируй QR\n"
                "2️⃣ Подтверди вход в приложении\n"
                "3️⃣ Попробуй /file снова",
                parse_mode='Markdown'
            )
            return
    
    # Генерируем скрипт
    script = client.generate_script()
    
    if not script:
        await msg.edit_text(
            "❌ **Ошибка генерации скрипта**\n"
            "Попробуй /qr заново",
            parse_mode='Markdown'
        )
        return
    
    # Извлекаем номер для имени файла
    phone = client.extract_phone()
    
    if phone:
        filename = f"max_{phone}.txt"
        caption = f"✅ **Файл для номера**\n`+7{phone}`"
    else:
        filename = f"max_{client.device_id[:8]}.txt"
        caption = "✅ **Файл готов**"
    
    # Отправляем файл
    file_bytes = BytesIO(script.encode('utf-8'))
    file_bytes.name = filename
    
    await msg.delete()
    await update.message.reply_document(
        document=InputFile(file_bytes, filename=filename),
        caption=caption,
        parse_mode='Markdown'
    )
    
    # Очищаем сессию
    if user_id in user_sessions:
        del user_sessions[user_id]

async def proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о прокси"""
    text = "📡 **Прокси для MAX API:**\n\n"
    for i, proxy in enumerate(PROXIES, 1):
        text += f"• Прокси {i}: `{proxy['addr']}:{proxy['port']}` (SOCKS5)\n"
    text += f"\nВсего: {len(PROXIES)} прокси\n"
    text += "Статус: ✅ Готовы к использованию"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс сессии"""
    user_id = str(update.effective_user.id)
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text("✅ **Сессия сброшена**", parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус API"""
    if MAXAPI_AVAILABLE:
        text = "✅ **maxapi-python установлен**\n"
        text += f"📦 Версия: 1.2.5\n"
        text += f"📡 Прокси: {len(PROXIES)} шт.\n"
        text += f"👤 Активных сессий: {len(user_sessions)}"
    else:
        text = "❌ **maxapi-python не установлен**\n"
        text += "Установи: `pip install maxapi-python`"
    
    await update.message.reply_text(text, parse_mode='Markdown')

def main():
    """Запуск бота"""
    print("=" * 60)
    print("🚀 БОТ ДЛЯ MAX.RU (maxapi-python)")
    print("=" * 60)
    print(f"✅ Токен: {TOKEN[:10]}...")
    print(f"📦 Библиотека: maxapi-python==1.2.5")
    print(f"📡 Прокси: {len(PROXIES)}")
    
    # Проверяем наличие библиотеки
    if not MAXAPI_AVAILABLE:
        print("⚠️ maxapi-python не установлен!")
        print("💡 Установи: pip install maxapi-python")
        print("=" * 60)
    
    print("🔄 Запуск бота...")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(CommandHandler("proxy", proxy_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("status", status_command))
    
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
