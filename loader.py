import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from database.db import Database

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("BOT_TOKEN", "8506986812:AAG9hHfIRAQeRRwHeYBYTXAfsYgDTTcrgfg")
ADMIN_ID = int(os.getenv("ADMIN_ID", "543692070"))

bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
db = Database("str_love_v2.db")

CITY_COORDS = {
    "Стерлитамак": (53.63, 55.95),
    "Салават": (53.36, 55.93),
    "Ишимбай": (53.45, 56.04),
}
GEOFENCE_RADIUS_KM = 50
