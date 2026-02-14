import logging
import sqlite3
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ================= КОНФИГУРАЦИЯ =================
API_TOKEN = '8506986812:AAG9hHfIRAQeRRwHeYBYTXAfsYgDTTcrgfg' 
ADMIN_ID = 454707643  # Твой ID для админки

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ================= БАЗА ДАННЫХ (ВНУТРИ) =================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("str_love_v2.db")
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                city TEXT,
                photo_id TEXT,
                bio TEXT,
                username TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        # Таблица лайков
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                who_id INTEGER,
                whom_id INTEGER,
                reaction TEXT
            )
        """)
        self.conn.commit()

    def add_user(self, user_id, name, age, gender, city, photo_id, bio, username):
        self.cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
                            (user_id, name, age, gender, city, photo_id, bio, username))
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_candidate(self, user_id):
        # Узнаем пол ищущего
        me = self.get_user(user_id)
        if not me: return None
        my_gender = me[3]
        
        # Ищем противоположный (или всех, если хочешь)
        target_gender = 'female' if my_gender == 'male' else 'male'
        
        # SQL: Найти того, кого я еще НЕ лайкал и НЕ дизлайкал
        sql = """
            SELECT * FROM users 
            WHERE gender = ? 
            AND user_id != ?
            AND user_id NOT IN (SELECT whom_id FROM likes WHERE who_id = ?)
            ORDER BY RANDOM() LIMIT 1
        """
        self.cursor.execute(sql, (target_gender, user_id, user_id))
        return self.cursor.fetchone()

    def add_like(self, who_id, whom_id, reaction):
        self.cursor.execute("INSERT INTO likes (who_id, whom_id, reaction) VALUES (?, ?, ?)",
                            (who_id, whom_id, reaction))
        self.conn.commit()
        
    def check_match(self, who_id, whom_id):
        # Проверяем, лайкнул ли ОН меня
        self.cursor.execute("SELECT * FROM likes WHERE who_id = ? AND whom_id = ? AND reaction = 'like'",
                            (whom_id, who_id))
        return self.cursor.fetchone()

db = Database()

# ================= СОСТОЯНИЯ =================
class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    photo = State()
    bio = State()

# ================= КЛАВИАТУРЫ (КРАСИВЫЕ) =================
def menu_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 Искать пару", "👤 Мой профиль")
    # kb.add("💎 Магазин (скоро)") # Пока уберем лишнее
    return kb

def gender_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("👨 Парень", "👩 Девушка")
    return kb

def vote_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("❤️ ЛАЙК", "👎 ДИЗЛАЙК")
    kb.add("💤 Стоп")
    return kb

# ================= ЛОГИКА БОТА =================

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user = db.get_user(message.from_user.id)
    
    if user:
        await message.answer(f"👋 С возвращением, <b>{user[1]}</b>!", reply_markup=menu_kb())
    else:
        await message.answer("👋 Привет! Это <b>Str.Love</b> — знакомства в Стерлитамаке.\n\nДавай создадим твою анкету. Как тебя зовут?")
        await RegState.name.set()

# --- РЕГИСТРАЦИЯ ---
@dp.message_handler(state=RegState.name)
async def r_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data: data['name'] = message.text
    await message.answer("Отлично! Сколько тебе лет?")
    await RegState.age.set()

@dp.message_handler(state=RegState.age)
async def r_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Пиши цифрами!")
    async with state.proxy() as data: data['age'] = int(message.text)
    await message.answer("Кто ты?", reply_markup=gender_kb())
    await RegState.gender.set()

@dp.message_handler(state=RegState.gender)
async def r_gender(message: types.Message, state: FSMContext):
    if "Парень" in message.text: gender = "male"
    elif "Девушка" in message.text: gender = "female"
    else: return await message.answer("Нажми кнопку внизу!")
    async with state.proxy() as data: data['gender'] = gender
    
    await message.answer("Из какого ты города?", reply_markup=ReplyKeyboardRemove())
    await RegState.city.set()

@dp.message_handler(state=RegState.city)
async def r_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data: data['city'] = message.text
    await message.answer("Пришли свое лучшее ФОТО 📸")
    await RegState.photo.set()

@dp.message_handler(content_types=['photo'], state=RegState.photo)
async def r_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data: data['photo'] = message.photo[-1].file_id
    await message.answer("Напиши пару слов о себе (БИО):\n<i>Например: Люблю кофе и прогулки...</i>")
    await RegState.bio.set()

@dp.message_handler(state=RegState.bio)
async def r_bio(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        db.add_user(
            message.from_user.id, data['name'], data['age'], data['gender'], 
            data['city'], data['photo'], message.text, message.from_user.username
        )
    await state.finish()
    await message.answer("✅ <b>Анкета готова!</b> Добро пожаловать.", reply_markup=menu_kb())

# --- ПОИСК ПАРЫ ---
@dp.message_handler(text="🚀 Искать пару")
async def start_search(message: types.Message, state: FSMContext):
    candidate = db.get_candidate(message.from_user.id)
    
    if not candidate:
        return await message.answer("😔 <b>Пока никого нет...</b>\nПопробуй позже или позови друзей!", reply_markup=menu_kb())
    
    # Запоминаем ID кандидата
    async with state.proxy() as data: data['candidate_id'] = candidate[0]
    
    # Красивая карточка
    caption = (
        f"<b>{candidate[1]}, {candidate[2]}</b>\n"
        f"📍 {candidate[4]}\n\n"
        f"📝 <i>{candidate[6]}</i>"
    )
    
    try:
        await message.answer_photo(candidate[5], caption=caption, reply_markup=vote_kb())
    except:
        await message.answer("Фото скрыто настройками приватности.\n" + caption, reply_markup=vote_kb())

# --- ГОЛОСОВАНИЕ ---
@dp.message_handler(text=["❤️ ЛАЙК", "👎 ДИЗЛАЙК", "💤 Стоп"])
async def voting(message: types.Message, state: FSMContext):
    if message.text == "💤 Стоп":
        await state.finish()
        return await message.answer("Поиск остановлен.", reply_markup=menu_kb())

    async with state.proxy() as data: candidate_id = data.get('candidate_id')
    if not candidate_id: return await start_search(message, state) # Если сбилось

    reaction = 'like' if "ЛАЙК" in message.text else 'dislike'
    
    # Пишем в базу
    db.add_like(message.from_user.id, candidate_id, reaction)
    
    # Если ЛАЙК - проверяем мэтч
    if reaction == 'like':
        if db.check_match(message.from_user.id, candidate_id):
            candidate = db.get_user(candidate_id)
            # Уведомляем ТЕБЯ
            await message.answer(f"🔥 <b>ЕСТЬ ПАРА!</b>\nЭто <a href='tg://user?id={candidate_id}'>{candidate[1]}</a>!", parse_mode="HTML")
            # Уведомляем ЕГО (если бот не заблокирован)
            try:
                me = db.get_user(message.from_user.id)
                await bot.send_message(candidate_id, f"🔥 <b>У тебя новая пара!</b>\nЭто <a href='tg://user?id={me[0]}'>{me[1]}</a>!", parse_mode="HTML")
            except: pass

    # Сразу следующий
    await start_search(message, state)

# --- ПРОФИЛЬ ---
@dp.message_handler(text="👤 Мой профиль")
async def my_profile(message: types.Message):
    u = db.get_user(message.from_user.id)
    caption = f"Твоя анкета:\n<b>{u[1]}, {u[2]}</b>\n{u[6]}"
    await message.answer_photo(u[5], caption=caption)


# ================= СЕКРЕТНЫЙ ГЕНЕРАТОР =================
# Напиши боту команду /admin_fill и он создаст 20 девушек
@dp.message_handler(commands=['admin_fill'])
async def fill_base(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    # Берем твое фото для фейков
    me = db.get_user(message.from_user.id)
    if not me: return await message.answer("Сначала зарегистрируйся сам!")
    photo_id = me[5] 
    
    names = ["Алина", "Катя", "Оля", "Вика", "Света", "Даша", "Лена", "Марина", "Кристина", "Настя"]
    bios = ["Люблю кофе", "Ищу парня", "Просто гуляю", "Скучно...", "Хочу на море"]
    
    await message.answer("⚙️ Создаю 20 девушек...")
    
    for i in range(20):
        fid = 777000 + i
        name = random.choice(names)
        age = random.randint(18, 30)
        db.add_user(fid, name, age, "female", "Стерлитамак", photo_id, random.choice(bios), None)
        
    await message.answer("✅ Готово! Жми 'Искать пару'.")

if __name__ == '__main__':
    print("🚀 BOT STARTED")
    executor.start_polling(dp, skip_updates=True)