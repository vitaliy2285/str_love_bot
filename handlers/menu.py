from aiogram import types

from keyboards.reply import menu_kb
from loader import db, dp


@dp.message_handler(text="👤 Мой профиль")
async def my_profile(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    vip_badge = "👑 VIP" if user["is_vip"] else ""
    caption = (
        f"{vip_badge}\n"
        f"<b>{user['name']}, {user['age']}</b>\n"
        f"📍 {user['city']}\n"
        f"🪙 Баланс: {user['balance']}\n"
        f"💌 Суперлайков сегодня: {user['daily_superlikes_left']}\n\n"
        f"{user['bio']}"
    )
    await message.answer_photo(user["photo_id"], caption=caption, reply_markup=menu_kb())
