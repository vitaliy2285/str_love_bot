from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from loader import bot, db, dp

CARD_PREFIX = "search:vote:"


def vote_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("❌", callback_data=f"{CARD_PREFIX}dislike"),
        InlineKeyboardButton("❤️", callback_data=f"{CARD_PREFIX}like"),
        InlineKeyboardButton("⭐ Super", callback_data=f"{CARD_PREFIX}superlike"),
    )


def _distance_text(distance_km):
    if distance_km is None:
        return "неизвестно"
    if distance_km < 1:
        return "совсем рядом"
    return f"{round(distance_km, 1)}"


async def show_next_candidate(target: Union[types.Message, types.CallbackQuery], state: FSMContext):
    message = target.message if isinstance(target, types.CallbackQuery) else target
    user_id = target.from_user.id if isinstance(target, types.CallbackQuery) else target.from_user.id

    candidate_data = db.get_candidate(user_id)
    if not candidate_data:
        await message.answer("Пока анкеты закончились.")
        return

    candidate, _ = candidate_data
    me = db.get_user(user_id)
    distance_km = None
    if me:
        me_lat, me_lon = db._row_lat(me), db._row_lon(me)
        cand_lat, cand_lon = db._row_lat(candidate), db._row_lon(candidate)
        if None not in (me_lat, me_lon, cand_lat, cand_lon):
            distance_km = db.haversine_km(me_lat, me_lon, cand_lat, cand_lon)

    async with state.proxy() as data:
        data["candidate_id"] = candidate["user_id"]

    distance_text = _distance_text(distance_km)
    caption = (
        f"<b>{candidate['name']}, {candidate['age']}</b>\n"
        f"📍 В {distance_text} км от тебя\n"
        f"<i>{candidate['bio']}</i>"
    )
    await message.answer_photo(candidate["photo_id"], caption=caption, reply_markup=vote_kb())


@dp.callback_query_handler(lambda c: c.data == "menu:search")
async def start_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_next_candidate(callback, state)


@dp.callback_query_handler(lambda c: c.data.startswith(CARD_PREFIX))
async def vote_candidate(callback: types.CallbackQuery, state: FSMContext):
    reaction = callback.data.replace(CARD_PREFIX, "")
    async with state.proxy() as data:
        candidate_id = data.get("candidate_id")

    if not candidate_id:
        await callback.answer("Открой поиск заново.", show_alert=False)
        await show_next_candidate(callback, state)
        return

    if reaction == "superlike" and not db.decrement_superlike(callback.from_user.id):
        await callback.answer("Лимит суперлайков исчерпан", show_alert=True)
        return

    db.add_reaction(callback.from_user.id, candidate_id, reaction)

    if reaction in {"like", "superlike"} and db.check_match(callback.from_user.id, candidate_id):
        db.create_match(callback.from_user.id, candidate_id)
        me = db.get_user(callback.from_user.id)
        candidate = db.get_user(candidate_id)
        await callback.message.answer(f"💘 Это мэтч! <b>{candidate['name']}</b> тоже поставил(а) лайк.")
        try:
            await bot.send_message(candidate_id, f"💘 Это мэтч! <b>{me['name']}</b> лайкнул(а) тебя в ответ.")
        except Exception:
            pass

    await callback.answer()
    await show_next_candidate(callback, state)
