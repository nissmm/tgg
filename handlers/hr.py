import re
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import storage
from config import TELEGRAM_CHANNEL_ID
from filters import IsHR
from keyboards import cancel_keyboard, hr_panel_keyboard
from states import NewHRRecord

router = Router()
router.message.filter(IsHR())
router.callback_query.filter(IsHR())

PHONE_RE = re.compile(r"^\+\d{10,15}$")
USERNAME_RE = re.compile(r"^@[A-Za-z0-9_]{5,32}$")
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


@router.callback_query(F.data == "hr_panel")
async def show_hr_panel(callback: CallbackQuery):
    await callback.message.edit_text("📋 HR-функции", reply_markup=hr_panel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "hr_new_record")
async def new_record_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Кто записал? (введите имя)", reply_markup=cancel_keyboard())
    await state.set_state(NewHRRecord.recorded_by)
    await callback.answer()


@router.message(NewHRRecord.recorded_by)
async def step_recorded_by(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Поле не может быть пустым. Введите, кто записал.", reply_markup=cancel_keyboard())
        return
    await state.update_data(recorded_by=text)
    await message.answer("Кого и сколько лет? (например: Иван Иванов, 25 лет)", reply_markup=cancel_keyboard())
    await state.set_state(NewHRRecord.candidate_info)


@router.message(NewHRRecord.candidate_info)
async def step_candidate_info(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not text or not any(ch.isdigit() for ch in text):
        await message.answer(
            "Укажите имя кандидата и возраст — в тексте должно быть число. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(candidate_info=text)
    await message.answer("Номер телефона? (например: +79991234567)", reply_markup=cancel_keyboard())
    await state.set_state(NewHRRecord.phone)


@router.message(NewHRRecord.phone)
async def step_phone(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not PHONE_RE.match(text):
        await message.answer(
            "Некорректный номер телефона. Введите в формате +79991234567.",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(phone=text)
    await message.answer("Юзернейм кандидата в Telegram? (например: @username)", reply_markup=cancel_keyboard())
    await state.set_state(NewHRRecord.username)


@router.message(NewHRRecord.username)
async def step_username(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    if not USERNAME_RE.match(text):
        await message.answer(
            "Некорректный юзернейм. Введите в формате @username.",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(username=text)
    await message.answer("Дата собеседования? (в формате ДД.ММ.ГГГГ)", reply_markup=cancel_keyboard())
    await state.set_state(NewHRRecord.interview_date)


@router.message(NewHRRecord.interview_date)
async def step_interview_date(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip() if message.text else ""
    if not DATE_RE.match(text):
        await message.answer("Некорректная дата. Введите в формате ДД.ММ.ГГГГ.", reply_markup=cancel_keyboard())
        return
    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Такой даты не существует. Введите корректную дату.", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    record = {
        "recorded_by": data["recorded_by"],
        "candidate_info": data["candidate_info"],
        "phone": data["phone"],
        "username": data["username"],
        "interview_date": text,
    }
    saved = storage.add_hr_record(record)
    await state.clear()

    settings = storage.get_settings()
    topic_id = settings.get("target_topic_id")

    notification = (
        "🆕 Новая запись HR\n\n"
        f"Кто записал: {saved['recorded_by']}\n"
        f"Кандидат: {saved['candidate_info']}\n"
        f"Телефон: {saved['phone']}\n"
        f"Юз: {saved['username']}\n"
        f"Дата собеса: {saved['interview_date']}"
    )
    try:
        await bot.send_message(TELEGRAM_CHANNEL_ID, notification, message_thread_id=topic_id)
        result_text = "Запись сохранена и отправлена в канал ✅"
    except Exception as e:
        result_text = f"Запись сохранена, но не удалось отправить уведомление в канал: {e}"

    await message.answer(result_text, reply_markup=hr_panel_keyboard())
