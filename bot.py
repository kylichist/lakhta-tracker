import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytz
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from scraper import get_tickets, get_link_by_timestamp, get_dates, BASE_URL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
FREQUENCY = int(os.getenv('FREQUENCY', 5))
DATA_DIR = '/app/data'
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, 'subscribers.json')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

moscow_tz = pytz.timezone('Europe/Moscow')

user_data_dir = tempfile.mkdtemp()
chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")

CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
service = Service(CHROMEDRIVER_PATH, kill_browser_processes=True)
service.start()

driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(BASE_URL) # открытая страница для поддержания сессии и минимизации зомби-процессов

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r') as file:
            logger.info("Начата загрузка подписчиков")
            subscribers_set = set(json.load(file))
            logger.info("Подписчики загружены")
            return subscribers_set
    except FileNotFoundError:
        logger.error("Не найден файл с подписчиками")
        return set()


def save_subscribers(subscribers_set):
    with open(SUBSCRIBERS_FILE, 'w') as file:
        logger.info("Начата запись подписчиков")
        json.dump(list(subscribers_set), file)
        logger.info("Подписчики записаны")


subscribers = load_subscribers()

scheduler = AsyncIOScheduler()


async def broadcast_all(ticket, message=None):
    logger.info(f"Найден билет: {ticket}")
    if ticket.amount > 0:
        message_text = f"Найдены билеты: {ticket}. Ссылка: {get_link_by_timestamp(ticket.date)}"
        for user_id in subscribers:
            await bot.send_message(user_id, message_text)
            logger.info(f"Сообщение отправлено пользователю {user_id}")


async def broadcast_raw(ticket, message=None):
    logger.info(f"Raw вывод {ticket}")
    await message.answer(str(ticket))


async def regular_check(operation, message=None):
    logger.info("Начата регулярная проверка")
    dates = await get_dates(driver)
    for date in dates:
        tickets = await get_tickets(driver, date)
        logger.info(f"Найдено билетов: {len(tickets)}")
        for ticket in tickets:
            await operation(ticket, message)
    else:
        logger.info("Даты не обнаружены")

@dp.message(Command("start"))
async def send_welcome(message: Message):
    logger.info("Команда /start")
    user_id = message.from_user.id
    if user_id not in subscribers:
        subscribers.add(user_id)
        save_subscribers(subscribers)
        logger.info("Пользователь подписался на рассылку")
        await message.answer("Вы подписались на рассылку.")
    else:
        logger.info("Пользователь переподписался на рассылку")
        await message.answer("Вы уже подписаны на рассылку.")


@dp.message(Command("stop"))
async def stop_messages(message: Message):
    logger.info("Команда /stop")
    user_id = message.from_user.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        logger.info("Пользователь отписался от рассылки")
        await message.answer("Вы отписались от рассылки.")
    else:
        logger.info("Пользователь попытался отписаться от рассылки, но не был подписан")
        await message.answer("Вы и так не были подписаны на рассылку.")


@dp.message(Command("raw"))
async def stop_messages(message: Message):
    logger.info("Команда /raw")
    await regular_check(broadcast_raw, message)


@dp.message(Command("status"))
async def stop_messages(message: Message):
    logger.info("Команда /status")
    await message.answer("Бот жив.")
    jobs = scheduler.get_jobs()
    if jobs:
        next_run_time = jobs[0].next_run_time
        next_run_time_formatted = next_run_time.astimezone(moscow_tz)
        await message.answer(f"Время следующего обновления: {next_run_time_formatted}")


async def main():
    logger.info("Бот запущен")
    logger.info("Добавлена задача регулярной проверки")
    scheduler.add_job(regular_check, 'interval', minutes=FREQUENCY, args=[broadcast_all])
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        await asyncio.to_thread(driver.quit)
        service.stop()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())

