from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.reply import menu_kb
from loader import bot, db, dp
from states.forms import SearchState


SEARCH_CARD_PREFIX = "search:"


def _card_keyboard(is_vip: bool, compliment_enabled: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("❤️ Like", callback_data=f"{SEARCH_CARD_PREFIX}like"),
        InlineKeyboardButton("👎 Dislike", callback_data=f"{SEARCH_CARD_PREFIX}dislike"),
    )
    kb.add(InlineKeyboardButton("⭐ Superlike", callback_data=f"{SEARCH_CARD_PREFIX}superlike"))
    if compliment_enabled:
        kb.add(InlineKeyboardButton("💬 Message (20 coins)", callback_data=f"{SEARCH_CARD_PREFIX}compliment"))
    if is_vip:
        kb.add(InlineKeyboardButton("↩️ Rewind", callback_data=f"{SEARCH_CARD_PREFIX}rewind"))
    kb.add(
        InlineKeyboardButton("⚙️ Settings", callback_data=f"{SEARCH_CARD_PREFIX}settings"),
        InlineKeyboardButton("🏠 Menu", callback_data=f"{SEARCH_CARD_PREFIX}menu"),
    )
    return kb


def _format_card(candidate, distance_km, liked_me: bool) -> str:
    lines = [f"<b>{candidate['name']}, {candidate['age']}</b>"]
    if liked_me:
        lines.append("<b>💘 Matched with you</b>")
    if distance_km is None:
        lines.append("📍 <i>Distance unknown</i>")
    else:
        lines.append(f"📍 <b>{int(distance_km)}</b> km away")
    lines.append("")
    lines.append(f"{candidate['bio']}")
    return "\n".join(lines)


async def _show_next_candidate(chat_id: int, user_id: int, state: FSMContext, card_message_id: int | None = None):
    candidate_data = db.get_candidate(user_id)
    if not candidate_data:
        from handlers.menu import send_or_edit_menu

        await send_or_edit_menu(chat_id=chat_id, user_id=user_id, menu_message_id=card_message_id)
        return

    candidate, distance_km, liked_me = candidate_data
    me = db.get_user(user_id)
    async with state.proxy() as data:
        data["candidate_id"] = candidate["user_id"]
        data["card_message_id"] = card_message_id

    state_data = await state.get_data()
    caption = _format_card(candidate, distance_km, liked_me)
    keyboard = _card_keyboard(is_vip=bool(me["is_vip"]), compliment_enabled=bool(state_data.get("superlike_target_id")))

    if card_message_id is None:
        sent = await bot.send_photo(chat_id, candidate["photo_id"], caption=caption, reply_markup=keyboard)
        await state.update_data(card_message_id=sent.message_id)
        return

    await bot.edit_message_caption(
        chat_id=chat_id,
        message_id=card_message_id,
        caption=caption,
        reply_markup=keyboard,
    )


@dp.callback_query_handler(lambda c: c.data == "menu:start_search")
async def start_search_from_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await _show_next_candidate(call.message.chat.id, call.from_user.id, state)


@dp.callback_query_handler(lambda c: c.data.startswith(SEARCH_CARD_PREFIX))
async def process_swipe(call: types.CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    await call.answer()

    if action == "menu":
        from handlers.menu import send_or_edit_menu

        await send_or_edit_menu(chat_id=call.message.chat.id, user_id=call.from_user.id, menu_message_id=call.message.message_id)
        return

    if action == "settings":
        from handlers.menu import open_settings_panel

        await open_settings_panel(call.message, call.from_user.id)
        return

    data = await state.get_data()
    candidate_id = data.get("candidate_id")
    card_message_id = call.message.message_id
    if not candidate_id and action != "rewind":
        await _show_next_candidate(call.message.chat.id, call.from_user.id, state, card_message_id)
        return

    if action == "like":
        db.add_reaction(call.from_user.id, candidate_id, "like")
        if db.check_match(call.from_user.id, candidate_id):
            db.create_match(call.from_user.id, candidate_id)
            me = db.get_user(call.from_user.id)
            candidate = db.get_user(candidate_id)
            await bot.send_message(call.from_user.id, f"💘 It's a Match! <b>{candidate['name']}</b> liked you too.")
            try:
                await bot.send_message(candidate_id, f"💘 It's a Match! <b>{me['name']}</b> liked you too.")
            except Exception:
                pass
        await state.update_data(last_swipe=None)

    elif action == "dislike":
        db.add_reaction(call.from_user.id, candidate_id, "dislike")
        await state.update_data(last_swipe={"candidate_id": candidate_id, "reaction": "dislike"})

    elif action == "superlike":
        if not db.decrement_superlike(call.from_user.id):
            await call.answer("No superlikes left for today.", show_alert=True)
            return
        db.add_reaction(call.from_user.id, candidate_id, "superlike")
        await state.update_data(superlike_target_id=candidate_id, last_swipe=None)
        if db.check_match(call.from_user.id, candidate_id):
            db.create_match(call.from_user.id, candidate_id)

    elif action == "compliment":
        superlike_target_id = data.get("superlike_target_id")
        if not superlike_target_id:
            await call.answer("Send superlike first.", show_alert=True)
            return
        await SearchState.compliment_text.set()
        await state.update_data(card_message_id=card_message_id)
        await bot.send_message(call.from_user.id, "Type a compliment up to 100 characters (20 coins).")
        return

    elif action == "rewind":
        me = db.get_user(call.from_user.id)
        if not me or not me["is_vip"]:
            await call.answer("VIP only", show_alert=True)
            return
        last_swipe = data.get("last_swipe")
        if not last_swipe or last_swipe.get("reaction") != "dislike":
            await call.answer("Nothing to rewind", show_alert=True)
            return
        db.delete_reaction(call.from_user.id, last_swipe["candidate_id"])
        db.add_reaction(call.from_user.id, last_swipe["candidate_id"], "like")
        await state.update_data(last_swipe=None)

    await _show_next_candidate(call.message.chat.id, call.from_user.id, state, card_message_id)


@dp.message_handler(state=SearchState.compliment_text)
async def send_compliment(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text or len(text) > 100:
        await message.answer("Message must be from 1 to 100 characters.")
        return

    data = await state.get_data()
    candidate_id = data.get("superlike_target_id")
    card_message_id = data.get("card_message_id")

    if not candidate_id:
        await state.finish()
        await message.answer("Superlike context expired.", reply_markup=menu_kb())
        return

    if not db.change_balance(message.from_user.id, -20):
        await message.answer("Not enough coins for a paid message.")
        return

    me = db.get_user(message.from_user.id)
    try:
        await bot.send_message(
            candidate_id,
            f"💬 <b>{me['name']}</b> sent you an icebreaker:\n<i>{text}</i>",
        )
    except Exception:
        pass

    await SearchState.finish()
    await state.update_data(superlike_target_id=None)
    await message.answer("Icebreaker sent. 20 coins charged.")

    if card_message_id:
        await _show_next_candidate(message.chat.id, message.from_user.id, state, card_message_id)
