# AIOgram
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
# Асинхронность
import asyncio
# YT Music и обработка JSON
from ytmusicapi import YTMusic
import json
# База данных PostgreSQL
import asyncpg
from functools import partial

# Класс Машины состояний
class Form(StatesGroup):
  # При запуске и при команде /menu
  main_menu = State()
  # При проверке профиля
  profile = State()
  # При входе в систему
  loging = State()
  # При поиске
  search = State()
  # При оплате подписки (На будущее)
  pay = State()

# Прокси
proxies = {
}

# Получение данных из файла data.json
data = json.load(open('data.json'))
bot_token = data['bot-token']
admin_id = data['admin-id']
postgres_uri = data['postgresql-uri']

# Инициализация бота, диспетчера, API YT Music
bot = Bot(bot_token)
dp = Dispatcher()
ytmusic = YTMusic()
# Указываем параметр proxies, если нужны прокси
#ytmusic = YTMusic(proxies=proxies)

# Обработчик команды /start
async def send_welcome(message: Message, state: FSMContext, base: asyncpg.Connection):
  # Создание таблицы в PostreSQL
  await base.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id BIGINT NOT NULL,
      username VARCHAR(255) NOT NULL,
      login_status VARCHAR(5) NOT NULL
    );
  """)

  await state.set_state(Form.main_menu)
  kb_buttons = [
    [
      KeyboardButton(text="Search"),
      KeyboardButton(text="Downloads")
    ],
    [KeyboardButton(text="Profile")]
  ]
  keyboard_start = ReplyKeyboardMarkup(keyboard=kb_buttons, resize_keyboard=True)
  # Добавление пользователя в БД
  if await base.fetchrow("SELECT id FROM users WHERE id = $1", message.from_user.id) == None:
    await base.execute("INSERT INTO users (username, id, login_status) VALUES ($1, $2, $3)", message.from_user.username, message.from_user.id, "No")
  await message.answer(f"Hello, *{message.from_user.full_name}*! \nI can play, download and save any track from YouTube Music. \n\nChoose an option from below:", reply_markup=keyboard_start, parse_mode=ParseMode.MARKDOWN)

# Обработчик команды /search (для поиска по библиотеке музыки и вывода результата)
async def search(message: Message, state: FSMContext):
  await message.answer("What do you want to search?\n\nType name of track or artist", reply_markup=ReplyKeyboardRemove())
  await state.set_state(Form.search)

# Функция для загрузки треков и отправки в чат (В разработке)
async def downloads(message: Message, state: FSMContext, base: asyncpg.Connection):
  await message.answer("Function in development...")

# Профиль пользователя
async def profile(message: Message, state: FSMContext, base: asyncpg.Connection):
  user = await base.fetchrow("SELECT * FROM users WHERE id = $1", message.from_user.id)

  status = ""
  if user['id'] in dict(await base.fetch("SELECT id FROM users WHERE login_status = 'Yes'")):
    status = "Logged in"
  else: status =  "Not logged in"
  kb_buttons = [
    [KeyboardButton(text="Login"), KeyboardButton(text="Back to menu")],
  ]
  keyboard_profile = ReplyKeyboardMarkup(keyboard=kb_buttons, resize_keyboard=True)
  await state.set_state(Form.profile)
  await message.answer(f"Username: <b>{message.from_user.full_name}</b> (@{user['username']})\nProfile ID: <code>{user['id']}</code>\n\nLogin status: <i>{status}</i>", reply_markup=keyboard_profile, parse_mode=ParseMode.HTML)

# Основное меню
async def menu(message: Message, state: FSMContext):
  kb_buttons = [
    [
      KeyboardButton(text="Search"),
      KeyboardButton(text="Downloads")
    ],
    [KeyboardButton(text="Profile")]
  ]
  keyboard_menu = ReplyKeyboardMarkup(keyboard=kb_buttons, resize_keyboard=True)

  await state.set_state(Form.main_menu)
  await message.answer("Choose an option from below:", reply_markup=keyboard_menu)

# Если пользователь нажал Search, ждём от него запрос и выводим результат
async def search_query(message: Message, state: FSMContext):
  await message.reply(f"Search results: {json.dumps(ytmusic.search(message.text, limit=10))})")

# Вход в аккаунт YouTube Music (В разработке)
async def login(message: Message, state: FSMContext, base: asyncpg.Connection):
  await message.answer("Function in development...")

# Основная функция - обработка комманд и запуск бота
async def main():
  # Вход в базу данных
  db = await asyncpg.connect(postgres_uri)

  # Основное меню и команда /start
  dp.message.register(partial(send_welcome, base=db), CommandStart())
  dp.message.register(menu, Command("menu"))
  dp.message.register(menu, F.text == "Menu")
  dp.message.register(menu, F.text == "Back to menu")
  # Вход в систему
  dp.message.register(partial(login, base=db), F.text == "Login")
  # Профиль
  dp.message.register(partial(profile, base=db), F.text == "Profile")
  # Поиск
  dp.message.register(search, F.text == "Search")
  dp.message.register(search_query, Form.search)
  # Кнопка "Downloads"
  dp.message.register(partial(downloads, base=db), F.text == "Downloads")

  # Запуск бота с сервисными сообщениями для админа
  print("Bot started!")
  await bot.send_message(chat_id=admin_id, text="Bot started!")
  await dp.start_polling(bot)
  await bot.send_message(chat_id=admin_id, text="Bot stopped!")

# Запуск программы
if __name__ == '__main__':
  asyncio.run(main())
