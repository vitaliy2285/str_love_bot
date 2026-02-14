from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN, DATABASE_PATH
from database import Database

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is empty. Set BOT_TOKEN env var.")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=storage)
db = Database(DATABASE_PATH)
