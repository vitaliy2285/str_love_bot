import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from database.db import Database

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("BOT_TOKEN", "8506986812:AAG9hHfIRAQeRRwHeYBYTXAfsYgDTTcrgfg")
ADMIN_ID = int(os.getenv("ADMIN_ID", "454707643"))

bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
db = Database("str_love_v2.db")
