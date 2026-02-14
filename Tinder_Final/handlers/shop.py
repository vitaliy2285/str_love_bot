from aiogram import types

from keyboards.reply import shop_menu
from loader import db, dp


@dp.message_handler(lambda m: m.text == "💎 Buy VIP")
async def buy_vip(message: types.Message):
    db.set_vip(message.from_user.id, days=30)
    await message.answer("VIP activated for 30 days", reply_markup=shop_menu())


@dp.message_handler(lambda m: m.text == "🪙 Buy Coins")
async def buy_coins(message: types.Message):
    db.add_balance(message.from_user.id, 100)
    await message.answer("Added 100 coins (demo). 10 coins = X rub.")


@dp.message_handler(lambda m: m.text == "⭐ Buy Superlikes")
async def buy_superlikes(message: types.Message):
    ok = db.buy_superlikes(message.from_user.id, count=5, price=50)
    await message.answer("Bought 5 superlikes" if ok else "Not enough balance")


@dp.message_handler(lambda m: m.text == "👀 Who liked me")
async def who_liked_me(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user or not user["is_vip"]:
        await message.answer("This feature is VIP only.")
        return
    rows = db.who_liked_me(message.from_user.id)
    if not rows:
        await message.answer("Nobody liked you yet.")
        return
    names = "\n".join(f"• {x['name']} ({x['age']})" for x in rows[:20])
    await message.answer(f"Liked you:\n{names}")


@dp.message_handler(commands=["rewind"])
async def rewind(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user or not user["is_vip"]:
        await message.answer("Rewind is VIP only.")
        return
    target = db.rewind_last_swipe(message.from_user.id)
    await message.answer("Rewind complete." if target else "No swipes to rewind.")
