from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove

from keyboards.reply import gender_kb, menu_kb
from loader import db, dp
from states.forms import RegState


@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user = db.get_user(message.from_user.id)
    if user:
        await message.answer(f"👋 С возвращением, <b>{user['name']}</b>!", reply_markup=menu_kb())
        return

    await message.answer(
        "👋 Привет! Это <b>Str.Love</b> — знакомства в Стерлитамаке.\n"
        "Создадим анкету. Как тебя зовут?"
    )
    await RegState.name.set()


@dp.message_handler(state=RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["name"] = message.text.strip()
    await message.answer("Сколько тебе лет?")
    await RegState.age.set()


@dp.message_handler(state=RegState.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Возраст нужно ввести цифрами.")
        return
    async with state.proxy() as data:
        data["age"] = int(message.text)
    await message.answer("Выбери пол:", reply_markup=gender_kb())
    await RegState.gender.set()


@dp.message_handler(state=RegState.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    if "Парень" in message.text:
        gender = "male"
    elif "Девушка" in message.text:
        gender = "female"
    else:
        await message.answer("Пожалуйста, используй кнопки выбора пола.")
        return

    async with state.proxy() as data:
        data["gender"] = gender
    await message.answer("Из какого ты города?", reply_markup=ReplyKeyboardRemove())
    await RegState.city.set()


@dp.message_handler(state=RegState.city)
async def reg_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["city"] = message.text.strip()
    await message.answer("Пришли фото профиля 📸")
    await RegState.photo.set()


@dp.message_handler(content_types=["photo"], state=RegState.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["photo_id"] = message.photo[-1].file_id
    await message.answer("Расскажи пару слов о себе.")
    await RegState.bio.set()


@dp.message_handler(state=RegState.photo)
async def reg_photo_fallback(message: types.Message):
    await message.answer("Нужно отправить именно фото.")


@dp.message_handler(state=RegState.bio)
async def reg_bio(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        db.add_user(
            (
                message.from_user.id,
                data["name"],
                data["age"],
                data["gender"],
                data["city"],
                data["photo_id"],
                message.text.strip(),
                message.from_user.username,
                10,
                0,
                None,
                1,
                None,
            )
        )
    await state.finish()
    await message.answer("✅ Анкета создана! Начислено 10 монет бонуса.", reply_markup=menu_kb())
