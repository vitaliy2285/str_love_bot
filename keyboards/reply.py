from aiogram.types import ReplyKeyboardMarkup


def menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 Искать пару", "👤 Мой профиль")
    kb.add("💎 Магазин", "🎭 Слепой чат")
    return kb


def gender_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("👨 Парень", "👩 Девушка")
    return kb


def vote_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("❤️ Лайк", "👎 Дизлайк")
    kb.add("💌 Письмо (5 монет)", "💤 Стоп")
    return kb


def shop_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add("👑 VIP на месяц", "🪙 50 монет")
    kb.add("↩️ Назад")
    return kb


def blind_chat_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add("🕵️ Раскрыть личность", "🛑 Выйти из слепого чата")
    return kb
