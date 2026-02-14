from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.reply import menu_kb
from loader import db, dp


def _menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🚀 Start search", callback_data="menu:start_search"))
    kb.add(InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"))
    kb.add(InlineKeyboardButton("👤 My profile", callback_data="menu:profile"))
    kb.add(InlineKeyboardButton("👀 Who liked me", callback_data="menu:likes"))
    return kb


def _settings_keyboard(user) -> InlineKeyboardMarkup:
    min_age = int(user["min_age"] or 18)
    max_age = int(user["max_age"] or 99)
    radius = int(user["search_radius"] or 50)

    kb = InlineKeyboardMarkup(row_width=4)
    kb.row(
        InlineKeyboardButton("Min age", callback_data="settings:noop"),
        InlineKeyboardButton("-", callback_data="settings:min:-1"),
        InlineKeyboardButton(str(min_age), callback_data="settings:noop"),
        InlineKeyboardButton("+", callback_data="settings:min:1"),
    )
    kb.row(
        InlineKeyboardButton("Max age", callback_data="settings:noop"),
        InlineKeyboardButton("-", callback_data="settings:max:-1"),
        InlineKeyboardButton(str(max_age), callback_data="settings:noop"),
        InlineKeyboardButton("+", callback_data="settings:max:1"),
    )
    kb.row(
        InlineKeyboardButton("Radius km", callback_data="settings:noop"),
        InlineKeyboardButton("-", callback_data="settings:radius:-1"),
        InlineKeyboardButton(str(radius), callback_data="settings:noop"),
        InlineKeyboardButton("+", callback_data="settings:radius:1"),
    )
    kb.add(InlineKeyboardButton("💾 Save", callback_data="settings:save"))
    kb.add(InlineKeyboardButton("⬅️ Back", callback_data="settings:back"))
    return kb


def _menu_text(user) -> str:
    return (
        f"<b>Welcome, {user['name']}</b>\n"
        f"🪙 Balance: <b>{user['balance']}</b>\n"
        f"⭐ Superlikes left: <b>{user['daily_superlikes_left']}</b>\n"
        f"🔎 Filters: <b>{user['min_age']}-{user['max_age']}</b> years, <b>{user['search_radius']}</b> km"
    )


async def send_or_edit_menu(chat_id: int, user_id: int, menu_message_id: int | None = None):
    user = db.get_user(user_id)
    if not user:
        return

    text = _menu_text(user)
    if menu_message_id:
        await dp.bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=menu_message_id,
            reply_markup=_menu_keyboard(),
        )
        return

    await dp.bot.send_message(chat_id, text, reply_markup=_menu_keyboard())


async def open_settings_panel(message: types.Message, user_id: int):
    user = db.get_user(user_id)
    if not user:
        return
    await message.edit_text(
        "<b>Search settings</b>\nAdjust age and radius filters.",
        reply_markup=_settings_keyboard(user),
    )


@dp.message_handler(text="👤 Мой профиль")
async def my_profile(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    vip_badge = "👑 VIP" if user["is_vip"] else ""
    location_line = "📍 Гео включено" if user["latitude"] is not None else "📍 Гео не указано"
    caption = (
        f"<b>{vip_badge}</b>\n"
        f"<b>{user['name']}, {user['age']}</b>\n"
        f"{location_line}\n"
        f"🪙 Баланс: <b>{user['balance']}</b>\n"
        f"⭐ Суперлайков сегодня: <b>{user['daily_superlikes_left']}</b>\n\n"
        f"{user['bio']}"
    )
    await message.answer_photo(user["photo_id"], caption=caption, reply_markup=menu_kb())


@dp.message_handler(text="🚀 Искать пару")
async def open_single_window_menu(message: types.Message):
    await send_or_edit_menu(chat_id=message.chat.id, user_id=message.from_user.id)


@dp.callback_query_handler(lambda c: c.data == "menu:settings")
async def menu_settings(call: types.CallbackQuery):
    await call.answer()
    await open_settings_panel(call.message, call.from_user.id)


@dp.callback_query_handler(lambda c: c.data.startswith("settings:"))
async def settings_callbacks(call: types.CallbackQuery):
    payload = call.data.split(":")
    action = payload[1]
    user = db.get_user(call.from_user.id)
    if not user:
        await call.answer()
        return

    if action == "noop":
        await call.answer()
        return

    if action == "back":
        await call.answer()
        await send_or_edit_menu(call.message.chat.id, call.from_user.id, call.message.message_id)
        return

    if action == "save":
        await call.answer("Saved")
        await send_or_edit_menu(call.message.chat.id, call.from_user.id, call.message.message_id)
        return

    target = payload[1]
    delta = int(payload[2])

    min_age = int(user["min_age"] or 18)
    max_age = int(user["max_age"] or 99)
    radius = int(user["search_radius"] or 50)

    if target == "min":
        min_age = max(18, min(99, min_age + delta))
        if min_age > max_age:
            max_age = min_age
    elif target == "max":
        max_age = max(18, min(99, max_age + delta))
        if max_age < min_age:
            min_age = max_age
    elif target == "radius":
        radius = max(1, min(100, radius + delta))

    db.update_search_preferences(call.from_user.id, min_age, max_age, radius)
    await call.answer()
    await open_settings_panel(call.message, call.from_user.id)


@dp.callback_query_handler(lambda c: c.data == "menu:profile")
async def menu_profile(call: types.CallbackQuery):
    await call.answer()
    user = db.get_user(call.from_user.id)
    if not user:
        return
    caption = (
        f"<b>{user['name']}, {user['age']}</b>\n"
        f"🪙 Balance: <b>{user['balance']}</b>\n"
        f"🔎 Prefs: <b>{user['min_age']}-{user['max_age']}</b> y/o, <b>{user['search_radius']}</b> km\n\n"
        f"{user['bio']}"
    )
    await call.message.edit_text(caption, reply_markup=_menu_keyboard())


@dp.callback_query_handler(lambda c: c.data == "menu:likes")
async def who_liked_me(call: types.CallbackQuery):
    await call.answer()
    user = db.get_user(call.from_user.id)
    if not user:
        return

    if not user["is_vip"]:
        await call.answer("VIP only feature", show_alert=True)
        return

    likes = db.get_who_liked_me(call.from_user.id)
    if not likes:
        await call.message.edit_text("<b>No new likes yet.</b>", reply_markup=_menu_keyboard())
        return

    text = "\n".join([f"• <b>{row['name']}</b>, {row['age']}" for row in likes[:20]])
    await call.message.edit_text(f"<b>People who liked you:</b>\n{text}", reply_markup=_menu_keyboard())
