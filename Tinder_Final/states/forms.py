from aiogram.dispatcher.filters.state import State, StatesGroup


class RegistrationForm(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    location = State()
    photo = State()
    bio = State()
    looking_for = State()


class SearchState(StatesGroup):
    browsing = State()


class AdminForm(StatesGroup):
    broadcast = State()


class ShopForm(StatesGroup):
    buy_vip = State()
    buy_coins = State()
    buy_superlikes = State()
