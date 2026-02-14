from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, UserDeactivated

from config import ADMIN_IDS
from loader import bot, db, dp
from states.forms import AdminForm


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@dp.message_handler(commands=["stats"])
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    s = db.stats()
    await message.answer(f"Users: {s['users']}\nActive: {s['active']}\nLikes: {s['likes']}\nMatches: {s['matches']}")


@dp.message_handler(commands=["broadcast"])
async def admin_broadcast_start(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await AdminForm.broadcast.set()
    await message.answer("Send broadcast text")


@dp.message_handler(state=AdminForm.broadcast)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.finish()
        return
    users = db.conn.execute("SELECT user_id FROM users WHERE is_active=1").fetchall()
    ok = 0
    for row in users:
        uid = row["user_id"]
        try:
            await bot.send_message(uid, message.text)
            ok += 1
        except (BotBlocked, UserDeactivated, ChatNotFound):
            db.deactivate_user(uid)
    await state.finish()
    await message.answer(f"Broadcast sent: {ok}")
