from datetime import datetime, timedelta

from aiogram import types

from keyboards.reply import menu_kb, shop_kb
from loader import db, dp
from utils.payment import PaymentGateway

payment = PaymentGateway()


@dp.message_handler(text="💎 Магазин")
async def open_shop(message: types.Message):
    await message.answer("Выбери товар:", reply_markup=shop_kb())


@dp.message_handler(text="↩️ Назад")
async def back_to_menu(message: types.Message):
    await message.answer("Главное меню", reply_markup=menu_kb())


@dp.message_handler(text="🪙 50 монет")
async def buy_coins(message: types.Message):
    result = payment.pay(message.from_user.id, "coins_50", 99)
    if not result.success:
        await message.answer("Платеж не прошел.")
        return
    db.change_balance(message.from_user.id, 50)
    db.create_shop_order(message.from_user.id, "coins_50", 99)
    await message.answer("✅ Оплата успешна (эмуляция). Начислено 50 монет.", reply_markup=shop_kb())


@dp.message_handler(text="👑 VIP на месяц")
async def buy_vip(message: types.Message):
    result = payment.pay(message.from_user.id, "vip_month", 299)
    if not result.success:
        await message.answer("Платеж не прошел.")
        return

    vip_end = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    db.make_vip(message.from_user.id, vip_end)
    db.create_shop_order(message.from_user.id, "vip_month", 299)
    await message.answer(
        "✅ VIP активирован на 30 дней (эмуляция оплаты).\n"
        "Преимущества: корона, +5 суперлайков в день, выше в выдаче.",
        reply_markup=shop_kb(),
    )
