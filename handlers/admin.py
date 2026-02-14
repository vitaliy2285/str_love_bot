from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import ADMIN_ID, bot, db, dp
from states.forms import AdminState
from utils.fake_profiles import generate_fake_profiles


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@dp.message_handler(commands=["admin_stats"])
async def admin_stats(message: types.Message):
    if not _is_admin(message.from_user.id):
        return
    total = db.get_users_count()
    active = db.get_active_users_count()
    vip = db.get_vip_count()
    revenue = db.get_revenue()
    await message.answer(
        f"📊 Пользователей: {total}\n"
        f"🟢 Активных: {active}\n"
        f"👑 VIP: {vip}\n"
        f"💰 Revenue: {revenue}"
    )


@dp.message_handler(commands=["broadcast"])
async def broadcast_start(message: types.Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("Введи текст рассылки:")
    await AdminState.broadcast_text.set()


@dp.message_handler(state=AdminState.broadcast_text)
async def broadcast_send(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.finish()
        return

    users = db.get_all_user_ids()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, f"📢 {message.text}")
            sent += 1
        except Exception:
            pass

    await state.finish()
    await message.answer(f"Рассылка завершена. Доставлено: {sent}")


@dp.message_handler(commands=["ban"])
async def ban_user(message: types.Message):
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /ban <user_id>")
        return

    banned = db.ban_user(int(parts[1]))
    await message.answer("Пользователь забанен." if banned else "Пользователь не найден.")


@dp.message_handler(commands=["add_fakes"])
async def add_fakes(message: types.Message):
    if not _is_admin(message.from_user.id):
        return

    me = db.get_user(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся, чтобы взять твое фото для фейков.")
        return

    photo_id = me["photo_id"]
    created = 0
    for fake in generate_fake_profiles(20):
        db.add_user(
            (
                fake["user_id"],
                fake["name"],
                fake["age"],
                fake["gender"],
                fake["city"],
                None,
                None,
                photo_id,
                fake["bio"],
                None,
                100,
                0,
                None,
                1,
                None,
                None,
            )
        )
        created += 1

    await message.answer(f"✅ Добавлено {created} фейковых анкет для тестирования поиска.")
