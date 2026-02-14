import logging
import asyncio
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TOKEN = "8294429332:AAHDw84FkyZ-EOHIXynS0YdgYRkLcjI8eK4"
URL_SAYTA = "https://web.max.ru"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

driver = None

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920x1080')
    return webdriver.Chrome(options=chrome_options)

async def get_qr():
    global driver
    if not driver:
        driver = create_driver()
    
    driver.get(URL_SAYTA)
    time.sleep(15)
    
    screenshot = driver.get_screenshot_as_png()
    img_io = BytesIO(screenshot)
    img_io.name = "qrcode.png"
    return img_io

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправь /qr для получения QR-кода")

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 Получаю QR-код...")
    img = await get_qr()
    await msg.delete()
    await update.message.reply_photo(photo=InputFile(img, filename="qrcode.png"))

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())