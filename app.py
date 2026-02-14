import asyncio

from aiogram import executor

from handlers import *  # noqa: F403,F401
from handlers.blind_chat import cleanup_expired_blind_messages
from loader import db, dp


async def blind_messages_gc_loop():
    while True:
        await cleanup_expired_blind_messages()
        await asyncio.sleep(300)


async def on_startup(_):
    db.create_tables()
    asyncio.create_task(cleanup_loop())


if __name__ == "__main__":
    print("🚀 BOT STARTED")
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
