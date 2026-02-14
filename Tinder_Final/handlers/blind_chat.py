from aiogram import types
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, UserDeactivated

from loader import bot, db, dp


@dp.message_handler(lambda m: m.text == "🎯 Find Partner")
async def blind_find(message: types.Message):
    me = db.get_user(message.from_user.id)
    if not me or not me["gender"]:
        await message.answer("Complete registration first: /start")
        return

    db.enqueue_blind(message.from_user.id, me["gender"], me["looking_for_gender"])
    pair = db.try_match_blind(message.from_user.id)
    if pair:
        for uid in pair:
            await bot.send_message(uid, "Anonymous chat found. Send messages here.")
    else:
        await message.answer("Searching partner...")


@dp.message_handler(lambda m: m.text == "⛔ Stop Chat")
async def blind_stop(message: types.Message):
    partner = db.blind_partner(message.from_user.id)
    db.stop_blind(message.from_user.id)
    await message.answer("Blind chat stopped.")
    if partner:
        try:
            await bot.send_message(partner, "Partner left blind chat.")
        except (BotBlocked, UserDeactivated, ChatNotFound):
            db.deactivate_user(partner)


@dp.message_handler(content_types=types.ContentTypes.ANY)
async def relay_blind(message: types.Message):
    if message.text and message.text.startswith("/"):
        return
    partner = db.blind_partner(message.from_user.id)
    if not partner:
        return
    try:
        if message.text:
            await bot.send_message(partner, message.text)
        elif message.photo:
            await bot.send_photo(partner, message.photo[-1].file_id, caption=message.caption or "")
    except (BotBlocked, UserDeactivated, ChatNotFound):
        db.deactivate_user(partner)
