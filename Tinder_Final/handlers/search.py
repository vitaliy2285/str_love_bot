from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, UserDeactivated

from keyboards.inline import swipe_kb
from loader import bot, db, dp
from states.forms import SearchState


def render_profile(user: types.User, target) -> str:
    return (
        f"<b>{target['name']}, {target['age']}</b>\n"
        f"{target['city']}\n"
        f"{target['bio'] or 'No bio'}\n"
        f"Rating: {round(target['rating_score'], 1)}"
    )


async def show_next_candidate(chat_id: int, state: FSMContext, source_message: types.Message = None):
    data = await state.get_data()
    feed = data.get("feed", [])
    idx = data.get("idx", 0)

    if idx >= len(feed):
        await state.finish()
        if source_message:
            await source_message.answer("No more profiles nearby right now.")
        else:
            await bot.send_message(chat_id, "No more profiles nearby right now.")
        return

    target_id = feed[idx]
    target = db.get_user(target_id)
    if not target:
        await state.update_data(idx=idx + 1)
        return await show_next_candidate(chat_id, state, source_message)

    caption = (
        f"<b>{target['name']}, {target['age']}</b>\n"
        f"{target['city']}\n"
        f"{target['bio'] or 'No bio'}"
    )
    kb = swipe_kb(target_id)
    if source_message and source_message.photo:
        await source_message.edit_caption(caption=caption, reply_markup=kb)
    elif source_message:
        await source_message.answer_photo(photo=target["photo_id"], caption=caption, reply_markup=kb)
    else:
        await bot.send_photo(chat_id=chat_id, photo=target["photo_id"], caption=caption, reply_markup=kb)


@dp.message_handler(lambda m: m.text == "🔥 Search")
async def search_start(message: types.Message, state: FSMContext):
    candidates = db.get_candidates(message.from_user.id)
    feed = [x["user_id"] for x in candidates]
    await SearchState.browsing.set()
    await state.update_data(feed=feed, idx=0)
    await show_next_candidate(message.chat.id, state, message)


@dp.callback_query_handler(lambda c: c.data.startswith("swipe:"), state=SearchState.browsing)
async def swipe_callback(call: types.CallbackQuery, state: FSMContext):
    _, action, target_id_raw = call.data.split(":")
    me = call.from_user.id
    target_id = int(target_id_raw)

    if action == "like":
        is_match = db.add_like(me, target_id, 0)
        if is_match:
            for uid in (me, target_id):
                try:
                    await bot.send_message(uid, "💘 It's a match!")
                except (BotBlocked, UserDeactivated, ChatNotFound):
                    db.deactivate_user(uid)
    elif action == "super":
        user = db.get_user(me)
        if user["superlikes_left"] <= 0:
            await call.answer("No superlikes left", show_alert=True)
            return
        db.conn.execute("UPDATE users SET superlikes_left = superlikes_left - 1 WHERE user_id=?", (me,))
        db.conn.commit()
        db.add_like(me, target_id, 1)
    else:
        db.add_dislike(me, target_id)

    data = await state.get_data()
    await state.update_data(idx=data.get("idx", 0) + 1)
    await call.answer("Saved")
    await show_next_candidate(call.message.chat.id, state, call.message)
