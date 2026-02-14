from aiogram import executor

from handlers import *  # noqa: F403,F401
from loader import dp


if __name__ == "__main__":
    print("🚀 BOT STARTED")
    executor.start_polling(dp, skip_updates=True)
