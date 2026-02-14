from aiogram.dispatcher.filters.state import State, StatesGroup


class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    photo = State()
    bio = State()


class SearchState(StatesGroup):
    letter_text = State()


class AdminState(StatesGroup):
    broadcast_text = State()
