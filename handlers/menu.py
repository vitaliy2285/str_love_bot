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
    location_line = "📍 Гео включено" if user["latitude"] is not None else "📍 Гео не указано"
    caption = (
        f"{vip_badge}\n"
        f"<b>{user['name']}, {user['age']}</b>\n"
        f"{location_line}\n"
        f"🪙 Баланс: {user['balance']}\n"
        f"⭐ Суперлайков сегодня: {user['daily_superlikes_left']}\n\n"
        f"{user['bio']}"
    )
    await message.answer_photo(user["photo_id"], caption=caption, reply_markup=menu_kb())


@dp.message_handler(text="👀 Кто меня лайкнул")
async def who_liked_me(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    if not user["is_vip"]:
        await message.answer("Функция доступна только с VIP.")
        return

    likes = db.get_who_liked_me(message.from_user.id)
    if not likes:
        await message.answer("Пока новых лайков нет.")
        return

    text = "\n".join([f"• {row['name']}, {row['age']}" for row in likes[:20]])
    await message.answer(f"Тебя лайкнули:\n{text}")
