from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔥 Search", "💬 Blind Chat")
    kb.add("🛒 Shop", "👤 Profile")
    kb.add("⚙️ Settings")
    return kb


def shop_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💎 Buy VIP", "🪙 Buy Coins")
    kb.add("⭐ Buy Superlikes", "👀 Who liked me")
    kb.add("⬅️ Back")
    return kb


def blind_chat_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎯 Find Partner", "⛔ Stop Chat")
    kb.add("⬅️ Back")
    return kb
