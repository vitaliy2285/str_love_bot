from aiogram import types
from aiogram.dispatcher import FSMContext

from config import DEFAULT_CITY, DEFAULT_LAT, DEFAULT_LON
from keyboards.reply import main_menu
from loader import db, dp
from states.forms import RegistrationForm


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    db.upsert_user(message.from_user.id, message.from_user.username)
    user = db.get_user(message.from_user.id)
    if user and user["name"] and user["photo_id"]:
        await message.answer("Welcome back!", reply_markup=main_menu())
        return

    await RegistrationForm.name.set()
    await message.answer("Let's create profile. What's your name?")


@dp.message_handler(state=RegistrationForm.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip()[:40])
    await RegistrationForm.next()
    await message.answer("How old are you? (18-80)")


@dp.message_handler(state=RegistrationForm.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not 18 <= int(message.text) <= 80:
        await message.answer("Enter valid age from 18 to 80.")
        return
    await state.update_data(age=int(message.text))
    await RegistrationForm.next()
    await message.answer("Your gender? (M/F)")


@dp.message_handler(state=RegistrationForm.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    value = message.text.strip().upper()
    if value not in {"M", "F"}:
        await message.answer("Use only M or F.")
        return
    await state.update_data(gender=value)
    await RegistrationForm.next()
    await message.answer(f"City? (default: {DEFAULT_CITY})")


@dp.message_handler(state=RegistrationForm.city)
async def reg_city(message: types.Message, state: FSMContext):
    city = message.text.strip() or DEFAULT_CITY
    await state.update_data(city=city)
    await RegistrationForm.next()
    await message.answer("Send location (or type 'skip').")


@dp.message_handler(content_types=types.ContentTypes.LOCATION, state=RegistrationForm.location)
async def reg_location_geo(message: types.Message, state: FSMContext):
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await RegistrationForm.next()
    await message.answer("Send your best photo.")


@dp.message_handler(state=RegistrationForm.location)
async def reg_location_skip(message: types.Message, state: FSMContext):
    await state.update_data(lat=DEFAULT_LAT, lon=DEFAULT_LON)
    await RegistrationForm.next()
    await message.answer("Send your best photo.")


@dp.message_handler(content_types=types.ContentTypes.PHOTO, state=RegistrationForm.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await RegistrationForm.next()
    await message.answer("Write short bio.")


@dp.message_handler(state=RegistrationForm.photo)
async def reg_photo_invalid(message: types.Message):
    await message.answer("Please send photo only.")


@dp.message_handler(state=RegistrationForm.bio)
async def reg_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text[:300])
    await RegistrationForm.next()
    await message.answer("Who are you looking for? (M/F/ANY)")


@dp.message_handler(state=RegistrationForm.looking_for)
async def reg_done(message: types.Message, state: FSMContext):
    looking_for = message.text.strip().upper()
    if looking_for not in {"M", "F", "ANY"}:
        await message.answer("Use M, F or ANY")
        return
    data = await state.get_data()
    data["looking_for_gender"] = looking_for.lower()
    db.complete_profile(message.from_user.id, data)
    await state.finish()
    await message.answer("Profile saved ✅", reply_markup=main_menu())
