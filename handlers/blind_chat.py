from aiogram import types

from keyboards.reply import blind_chat_kb, menu_kb
from loader import bot, db, dp
from utils.time_rules import is_blind_chat_time


def _partner_id(chat_row, user_id: int) -> int:
    return chat_row["user_b"] if chat_row["user_a"] == user_id else chat_row["user_a"]


async def cleanup_expired_blind_messages() -> int:
    expired = db.get_expired_blind_messages(older_than_hours=24)
    deleted_count = 0
    for row in expired:
        try:
            await bot.delete_message(chat_id=row["receiver_id"], message_id=row["receiver_message_id"])
        except Exception:
            pass
        db.mark_blind_message_deleted(row["id"])
        deleted_count += 1
    return deleted_count


@dp.message_handler(text="🎭 Слепой чат")
async def blind_chat_entry(message: types.Message):
    if not is_blind_chat_time():
        await message.answer("Слепой чат работает только с пятницы 20:00 до субботы 02:00.", reply_markup=menu_kb())
        return

    active = db.get_active_blind_chat(message.from_user.id)
    if active:
        await message.answer("Ты уже в слепом чате.", reply_markup=blind_chat_kb())
        return

    partner_id = db.find_blind_partner(message.from_user.id)
    if not partner_id:
        db.queue_blind_chat(message.from_user.id)
        await message.answer("Ищем собеседника... Ожидай в очереди.", reply_markup=blind_chat_kb())
        return

    db.create_blind_chat(message.from_user.id, partner_id)
    await message.answer("Собеседник найден! Пиши сообщения в этот чат.", reply_markup=blind_chat_kb())
    await bot.send_message(partner_id, "Собеседник найден! Пиши сообщения в этот чат.", reply_markup=blind_chat_kb())


@dp.message_handler(text="🕵️ Раскрыть личность")
async def reveal_identity(message: types.Message):
    active = db.get_active_blind_chat(message.from_user.id)
    if not active:
        await message.answer("Ты не в слепом чате.", reply_markup=menu_kb())
        return

    db.set_reveal_consent(active["id"], message.from_user.id)
    refreshed = db.get_active_blind_chat(message.from_user.id)
    partner_id = _partner_id(refreshed, message.from_user.id)

    if refreshed["reveal_a"] and refreshed["reveal_b"]:
        me = db.get_user(message.from_user.id)
        partner = db.get_user(partner_id)
        await message.answer(f"Личности раскрыты! Твой собеседник: <b>{partner['name']}</b> (@{partner['username'] or 'без username'}).")
        await bot.send_message(partner_id, f"Личности раскрыты! Твой собеседник: <b>{me['name']}</b> (@{me['username'] or 'без username'}).")
    else:
        await message.answer("Запрос отправлен. Ждем согласия второго участника.")
        await bot.send_message(partner_id, "Собеседник хочет раскрыть личность. Нажми '🕵️ Раскрыть личность'.")


@dp.message_handler(text="🛑 Выйти из слепого чата")
async def exit_blind_chat(message: types.Message):
    db.remove_from_blind_queue(message.from_user.id)
    active = db.get_active_blind_chat(message.from_user.id)
    if active:
        partner_id = _partner_id(active, message.from_user.id)
        db.close_blind_chat(active["id"])
        await bot.send_message(partner_id, "Собеседник завершил слепой чат.", reply_markup=menu_kb())
    await message.answer("Ты вышел из слепого чата.", reply_markup=menu_kb())


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def relay_blind_chat_message(message: types.Message):
    if message.text in {
        "🚀 Искать пару", "👤 Мой профиль", "💎 Магазин", "🎭 Слепой чат", "👀 Кто меня лайкнул",
        "❤️ Лайк", "👎 Дизлайк", "⭐ Суперлайк", "💤 Стоп", "💌 Письмо (5 монет)",
        "👑 VIP на месяц", "🪙 50 монет", "🚀 Boost (50 монет)", "↩️ Назад", "🕵️ Раскрыть личность", "🛑 Выйти из слепого чата"
    }:
        return

    active = db.get_active_blind_chat(message.from_user.id)
    if not active:
        return

    partner_id = _partner_id(active, message.from_user.id)
    sent = await bot.send_message(partner_id, f"🎭 Аноним: {message.text}")
    db.register_blind_message(active["id"], message.from_user.id, partner_id, sent.message_id)
    db.register_blind_message(active["id"], message.from_user.id, message.from_user.id, message.message_id)
