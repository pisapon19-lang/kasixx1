"""
Telegram бот для max.ru с выполнением JS команд и получением результата
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
import json

# Токен из переменных окружения
TOKEN = os.environ.get('TOKEN', '8294429332:AAHDw84Fkyz-E0HIXynS0YdGRkLcjI8ek4')
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

def execute_and_get_result():
    """Выполняет JS команду и возвращает результат"""
    global driver
    
    try:
        # Ваша JS команда
        js_command = """
        let deviceId = localStorage.getItem('__oneme_device_id');
        let auth = localStorage.getItem('__oneme_auth');
        
        // Формируем результат
        let result = {
            deviceId: deviceId,
            auth: auth,
            timestamp: new Date().toISOString(),
            script: `
sessionStorage.clear();
localStorage.clear();
localStorage.setItem('__oneme_device_id', '${deviceId}');
localStorage.setItem('__oneme_auth', '${auth}');
window.location.reload();
            `
        };
        
        // Выводим в консоль (для логов)
        console.log('Device ID:', deviceId);
        console.log('Auth:', auth);
        
        // Возвращаем результат
        return result;
        """
        
        # Выполняем команду и получаем результат
        result = driver.execute_script(js_command)
        
        # Форматируем результат для отправки
        formatted_result = f"""📊 **Результат выполнения JS:**

**Device ID:** `{result.get('deviceId', 'не найден')}`

**Auth:** `{result.get('auth', 'не найден')}`

**Время:** {result.get('timestamp', '')}

**Сгенерированный скрипт:**
```javascript
{result.get('script', '')}
```"""
        
        return formatted_result, result
        
    except Exception as e:
        logger.error(f"Ошибка выполнения JS: {e}")
        return f"❌ Ошибка выполнения JS: {str(e)}", None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Бот для max.ru**\n\n"
        "🔹 **/js** - выполнить JS команду и показать результат\n"
        "🔹 **/qr** - получить QR-код\n"
        "🔹 **/full** - выполнить JS + получить QR-код\n"
        "🔹 **/status** - проверить статус",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает")

async def js_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполняет JS и присылает результат"""
    msg = await update.message.reply_text("🔄 Выполняю JS команду...")
    
    try:
        driver = get_driver()
        
        # Загружаем страницу
        logger.info("Загружаю страницу...")
        driver.get(URL)
        time.sleep(5)
        
        # Выполняем JS и получаем результат
        result_text, result_data = execute_and_get_result()
        
        # Отправляем результат
        await msg.delete()
        
        # Если результат слишком длинный, разбиваем на части
        if len(result_text) > 4000:
            parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(result_text, parse_mode='Markdown')
        
        # Если есть auth, покажем первые символы
        if result_data and result_data.get('auth'):
            auth_preview = result_data['auth'][:50] + "..."
            await update.message.reply_text(f"🔑 Auth (первые 50 символов): `{auth_preview}`", parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Только QR-код"""
    msg = await update.message.reply_text("🔄 Получаю QR-код...")
    
    try:
        driver = get_driver()
        driver.get(URL)
        time.sleep(10)
        
        # Ищем QR-код
        screenshot = driver.get_screenshot_as_png()
        img_io = BytesIO(screenshot)
        img_io.name = "qrcode.png"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="qrcode.png"),
            caption="✅ QR-код получен!"
        )
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def full_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполняет JS, присылает результат и QR-код"""
    msg = await update.message.reply_text("🔄 Выполняю полную последовательность...")
    
    try:
        driver = get_driver()
        
        # Шаг 1: Загружаем страницу
        await msg.edit_text("📡 Загружаю страницу...")
        driver.get(URL)
        time.sleep(5)
        
        # Шаг 2: Выполняем JS
        await msg.edit_text("⚙️ Выполняю JS команду...")
        result_text, result_data = execute_and_get_result()
        
        # Шаг 3: Отправляем результат JS
        await msg.edit_text("📤 Отправляю результат...")
        await update.message.reply_text(result_text, parse_mode='Markdown')
        
        # Шаг 4: Обновляем страницу (если нужно)
        if result_data and result_data.get('deviceId'):
            await update.message.reply_text("🔄 Обновляю страницу...")
            driver.refresh()
            time.sleep(5)
        
        # Шаг 5: Получаем QR-код
        await update.message.reply_text("🔍 Ищу QR-код...")
        
        # Ищем SVG или делаем скриншот
        svg_elements = driver.find_elements(By.TAG_NAME, "svg")
        if svg_elements:
            screenshot = svg_elements[0].screenshot_as_png
        else:
            screenshot = driver.get_screenshot_as_png()
        
        img_io = BytesIO(screenshot)
        img_io.name = "qrcode.png"
        
        await update.message.reply_photo(
            photo=InputFile(img_io, filename="qrcode.png"),
            caption="✅ Готово!"
        )
        
        await msg.delete()
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")

async def main():
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем все команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("js", js_command))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("full", full_command))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("✅ Бот запущен!")
    logger.info("Команды: /js, /qr, /full")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        if driver:
            driver.quit()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
