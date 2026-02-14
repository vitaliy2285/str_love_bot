from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def swipe_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("👎", callback_data=f"swipe:dislike:{user_id}"),
        InlineKeyboardButton("❤️", callback_data=f"swipe:like:{user_id}"),
        InlineKeyboardButton("⭐", callback_data=f"swipe:super:{user_id}"),
    )
    return kb
