from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from loader import CITY_COORDS, GEOFENCE_RADIUS_KM, db, dp
from states.forms import RegState


OUTSIDE_TEXT = (
    "❌ Извини, но наш сервис работает только для жителей Стерлитамака, "
    "Салавата и Ишимбая. Приходи, когда будешь в городе!"
)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🔥 Искать пару", callback_data="menu:search"),
        InlineKeyboardButton("👤 Профиль", callback_data="menu:profile"),
        InlineKeyboardButton("💎 Магазин", callback_data="menu:shop"),
        InlineKeyboardButton("💬 Слепой чат", callback_data="menu:blind"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="menu:settings"),
    )


def registration_gender_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("👨 Парень", callback_data="reg:gender:male"),
        InlineKeyboardButton("👩 Девушка", callback_data="reg:gender:female"),
    )


def location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
        KeyboardButton("📍 Отправить геолокацию", request_location=True)
    )


def _inside_golden_triangle(lat: float, lon: float) -> bool:
    for city_lat, city_lon in CITY_COORDS.values():
        distance = db.haversine_km(lat, lon, city_lat, city_lon)
        if distance <= GEOFENCE_RADIUS_KM:
            return True
    return False


@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user = db.get_user(message.from_user.id)
    if user:
        await message.answer(f"👋 С возвращением, <b>{user['name']}</b>!", reply_markup=main_menu_kb())
        return

    await message.answer("👋 Привет! Это <b>Str.Love</b>.")
    await message.answer("Как тебя зовут?")
    await RegState.name.set()


@dp.message_handler(state=RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["name"] = message.text.strip()
    await message.answer("Сколько тебе лет?")
    await RegState.age.set()


@dp.message_handler(state=RegState.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not 18 <= int(message.text) <= 99:
        await message.answer("Укажи возраст числом от 18 до 99.")
        return

    async with state.proxy() as data:
        data["age"] = int(message.text)
    await message.answer("Выбери пол:", reply_markup=registration_gender_kb())
    await RegState.gender.set()


@dp.callback_query_handler(lambda c: c.data.startswith("reg:gender:"), state=RegState.gender)
async def reg_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split(":")[-1]
    async with state.proxy() as data:
        data["gender"] = gender

    await callback.message.answer(
        "Отправь геолокацию, чтобы показать анкеты рядом.",
        reply_markup=location_kb(),
    )
    await callback.answer()
    await RegState.location.set()


@dp.message_handler(content_types=types.ContentTypes.LOCATION, state=RegState.location)
async def reg_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude

    if not _inside_golden_triangle(lat, lon):
        await state.finish()
        await message.answer(OUTSIDE_TEXT, reply_markup=ReplyKeyboardRemove())
        return

    async with state.proxy() as data:
        data["latitude"] = lat
        data["longitude"] = lon

    await message.answer("Пришли фото профиля 📸", reply_markup=ReplyKeyboardRemove())
    await RegState.photo.set()


@dp.message_handler(state=RegState.location)
async def reg_location_fallback(message: types.Message):
    await message.answer("Нажми кнопку '📍 Отправить геолокацию'.")


@dp.message_handler(content_types=types.ContentTypes.PHOTO, state=RegState.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["photo_id"] = message.photo[-1].file_id
    await message.answer("Расскажи пару слов о себе.")
    await RegState.bio.set()


@dp.message_handler(state=RegState.photo)
async def reg_photo_fallback(message: types.Message):
    await message.answer("Нужно отправить фото.")


@dp.message_handler(state=RegState.bio)
async def reg_bio(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        db.add_user(
            (
                message.from_user.id,
                data["name"],
                data["age"],
                data["gender"],
                "Unknown",
                data["latitude"],
                data["longitude"],
                data["latitude"],
                data["longitude"],
                data["photo_id"],
                message.text.strip(),
                message.from_user.username,
                10,
                0,
                None,
                1,
                None,
                None,
            )
        )
    await state.finish()
    await message.answer("✅ Анкета готова!", reply_markup=main_menu_kb())


@dp.callback_query_handler(lambda c: c.data == "menu:profile")
async def menu_profile(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала зарегистрируйся через /start")
        await callback.answer()
        return

    caption = (
        f"<b>{user['name']}, {user['age']}</b>\n"
        f"🪙 Баланс: {user['balance']}\n"
        f"{user['bio']}"
    )
    await callback.message.answer_photo(user["photo_id"], caption=caption, reply_markup=main_menu_kb())
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data in {"menu:shop", "menu:blind", "menu:settings"})
async def menu_stub(callback: types.CallbackQuery):
    labels = {
        "menu:shop": "💎 Магазин",
        "menu:blind": "💬 Слепой чат",
        "menu:settings": "⚙️ Настройки",
    }
    await callback.answer()
    await callback.message.answer(f"Раздел <b>{labels[callback.data]}</b> скоро будет обновлён.", reply_markup=main_menu_kb())
