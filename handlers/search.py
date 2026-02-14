from aiogram import types
from aiogram.dispatcher import FSMContext

from keyboards.reply import menu_kb, vote_kb
from loader import bot, db, dp
from states.forms import SearchState


async def show_next_candidate(message: types.Message, state: FSMContext):
    candidate_data = db.get_candidate(message.from_user.id)
    if not candidate_data:
        await message.answer("Пока анкеты закончились, попробуй позже.", reply_markup=menu_kb())
        return

    candidate, distance_km = candidate_data
    async with state.proxy() as data:
        data["candidate_id"] = candidate["user_id"]

    distance_line = f"📍 {int(distance_km)} km from you" if distance_km is not None else "📍 distance unknown"
    caption = f"<b>{candidate['name']}, {candidate['age']}</b>\n{distance_line}\n\n{candidate['bio']}"
    await message.answer_photo(candidate["photo_id"], caption=caption, reply_markup=vote_kb())


@dp.message_handler(text="🚀 Искать пару")
async def start_search(message: types.Message, state: FSMContext):
    await show_next_candidate(message, state)


@dp.message_handler(text=["❤️ Лайк", "👎 Дизлайк", "⭐ Суперлайк", "💤 Стоп"])
async def vote_candidate(message: types.Message, state: FSMContext):
    if message.text == "💤 Стоп":
        await state.finish()
        await message.answer("Поиск остановлен.", reply_markup=menu_kb())
        return

    async with state.proxy() as data:
        candidate_id = data.get("candidate_id")

    if not candidate_id:
        await show_next_candidate(message, state)
        return

    reaction = "dislike"
    if message.text == "❤️ Лайк":
        reaction = "like"
    elif message.text == "⭐ Суперлайк":
        if not db.decrement_superlike(message.from_user.id):
            await message.answer("Лимит суперлайков на сегодня исчерпан.")
            return
        reaction = "superlike"

    db.add_reaction(message.from_user.id, candidate_id, reaction)

    if reaction in {"like", "superlike"} and db.check_match(message.from_user.id, candidate_id):
        db.create_match(message.from_user.id, candidate_id)
        me = db.get_user(message.from_user.id)
        candidate = db.get_user(candidate_id)
        await message.answer(f"💘 It's a Match! <b>{candidate['name']}</b> тоже лайкнул(а) тебя. Нажмите, чтобы начать чат.")
        try:
            await bot.send_message(
                candidate_id,
                f"💘 It's a Match! <b>{me['name']}</b> лайкнул(а) тебя в ответ. Click here to chat.",
            )
        except Exception:
            pass

    await show_next_candidate(message, state)


@dp.message_handler(text="💌 Письмо (5 монет)")
async def send_letter_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        candidate_id = data.get("candidate_id")
    if not candidate_id:
        await message.answer("Сначала открой анкету через '🚀 Искать пару'.")
        return

    user = db.get_user(message.from_user.id)
    if user["balance"] < 5:
        await message.answer("Недостаточно монет. Открой '💎 Магазин'.", reply_markup=menu_kb())
        return

    await message.answer("Напиши короткое сообщение для отправки пользователю:")
    await SearchState.letter_text.set()


@dp.message_handler(state=SearchState.letter_text)
async def send_letter_finish(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        candidate_id = data.get("candidate_id")
    if not candidate_id:
        await state.finish()
        await message.answer("Кандидат не найден, начни поиск заново.", reply_markup=menu_kb())
        return

    if not db.change_balance(message.from_user.id, -5):
        await state.finish()
        await message.answer("Не удалось списать монеты.", reply_markup=menu_kb())
        return

    me = db.get_user(message.from_user.id)
    try:
        await bot.send_message(
            candidate_id,
            f"💌 Тебе пришло письмо до мэтча!\n"
            f"От: <b>{me['name']}</b>\n"
            f"Текст: {message.text}",
        )
    except Exception:
        pass

    await state.finish()
    await message.answer("Письмо отправлено! Списано 5 монет.", reply_markup=vote_kb())
