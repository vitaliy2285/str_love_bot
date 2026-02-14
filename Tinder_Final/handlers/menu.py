from aiogram import types

from keyboards.reply import blind_chat_menu, main_menu, shop_menu
from loader import dp


@dp.message_handler(lambda m: m.text == "🛒 Shop")
async def open_shop(message: types.Message):
    await message.answer("Shop opened", reply_markup=shop_menu())


@dp.message_handler(lambda m: m.text == "💬 Blind Chat")
async def open_blind(message: types.Message):
    await message.answer("Blind chat menu", reply_markup=blind_chat_menu())


@dp.message_handler(lambda m: m.text == "⬅️ Back")
async def back_menu(message: types.Message):
    await message.answer("Main menu", reply_markup=main_menu())
