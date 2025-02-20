import logging
import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    CallbackQuery, Message
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

print(re.__doc__)
load_dotenv()  # Загружаем переменные из .env



# 🔹 Загрузка переменных окружения
load_dotenv()
MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")

CONSULT_BOT_USERNAME = os.getenv("@KeyturSupport_bot")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GROUP_ID = int(os.getenv("GROUP_ID", 0))

# 🔹 Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Создаём бота и диспетчер
bot = Bot(token=MAIN_BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# 🔹 Определяем состояния пользователя
class BookingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_day = State()
    waiting_for_time = State()
    waiting_for_phone = State()

# 🔹 Словари для маппинга данных
DAYS = {
    "day_monday": "Понедельник",
    "day_tuesday": "Вторник",
    "day_wednesday": "Среда",
    "day_thursday": "Четверг",
    "day_friday": "Пятница",
}

TIMES = {
    "time_10_12": "10:00 - 12:00",
    "time_12_14": "12:00 - 14:00",
    "time_14_16": "14:00 - 16:00",
    "time_16_18": "16:00 - 18:00",
    "time_18_20": "18:00 - 20:00",
}

# 🔹 Функции для клавиатур
def main_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Записаться на консультацию", callback_data="request_access")],
        
    ])

def days_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=day, callback_data=key)] for key, day in DAYS.items()
    ])

def time_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=time, callback_data=key)] for key, time in TIMES.items()
    ])

def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# 📌 Команда /start
@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}! Выберите нужную опцию:",
        reply_markup=main_keyboard(message.from_user.id)
    )

# 📌 Запрос имени
@router.callback_query(F.data == "request_access")
async def request_access(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введите ваше *Имя и Фамилию*:")  
    await callback.answer()
    await state.set_state(BookingState.waiting_for_name)

# 📌 Получение имени
@router.message(BookingState.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"✅ Спасибо, {message.text}!\nТеперь выберите удобный день:", reply_markup=days_keyboard())
    await state.set_state(BookingState.waiting_for_day)

# 📌 Выбор дня
@router.callback_query(BookingState.waiting_for_day, F.data.startswith("day_"))
async def set_day(callback: CallbackQuery, state: FSMContext):
    day = DAYS.get(callback.data, "Неизвестный день")
    await state.update_data(day=day)
    await callback.message.answer(f"📅 Вы выбрали: *{day}*\nТеперь выберите удобное время:", reply_markup=time_keyboard(), parse_mode="Markdown")
    await callback.answer()
    await state.set_state(BookingState.waiting_for_time)

# 📌 Выбор времени
@router.callback_query(BookingState.waiting_for_time, F.data.startswith("time_"))
async def set_time(callback: CallbackQuery, state: FSMContext):
    time_slot = TIMES.get(callback.data, "Неизвестное время")
    await state.update_data(time=time_slot)
    await callback.message.answer("📞 Теперь отправьте свой номер телефона (используйте кнопку ниже):", reply_markup=phone_keyboard())
    await callback.answer()
    await state.set_state(BookingState.waiting_for_phone)

# 📌 Получение номера телефона
@router.message(BookingState.waiting_for_phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone_number = message.contact.phone_number
    await state.update_data(phone=phone_number)

    user_data = await state.get_data()
    user_name = user_data.get("name", "Неизвестный")
    day = user_data.get("day", "Неизвестный день")
    time_slot = user_data.get("time", "Неизвестное время")

    # 📌 Подтверждение записи
    confirmation_message = (
        f"🎉 Поздравляем, {user_name}! Вы успешно записаны на консультацию. \n"
        f"📅 День: *{day}*\n"
        f"🕐 Время: *{time_slot}*\n"
        f"📞 Телефон: `{phone_number}`\n\n"
        "Ожидайте, с вами свяжутся в выбранный день и время. Спасибо!"
    )
    await message.answer(confirmation_message, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

    # 📌 Отправка уведомления в группу
    group_message = (
        f"👤 *Новая запись на консультацию!*\n\n"
        f"👤 Имя: {user_name}\n"
        f"📅 День: {day}\n"
        f"🕐 Время: {time_slot}\n"
        f"📞 Телефон: `{phone_number}`"
    )
    await bot.send_message(GROUP_ID, group_message, parse_mode="Markdown")

    await state.clear()  # Завершаем состояние

# 📌 Получение ID группы
@router.message(Command("get_group_id"))
async def get_group_id(message: Message):
    await message.answer(f"📌 ID этой группы: `{message.chat.id}`", parse_mode="Markdown")

# 🚀 Запуск бота
async def main():
    logger.info("🤖 Основной бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())


