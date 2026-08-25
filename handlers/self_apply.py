import html
import re
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import storage
from config import TELEGRAM_CHANNEL_ID
from filters import IsChannelAdmin
from formatting import format_moderation_card
from keyboards import cancel_keyboard, main_menu_keyboard, moderation_keyboard, skip_or_cancel_keyboard
from states import SelfApply

router = Router()

PHONE_RE = re.compile(r"^\+\d{10,15}$")
USERNAME_RE = re.compile(r"^(-|@[A-Za-z0-9_]{5,32})$")
DATETIME_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$")


@router.callback_query(F.data == "self_apply_start")
async def self_apply_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Заявка на собеседование.\nКак вас зовут и сколько вам лет? (например: Иван Иванов, 25 лет)",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(SelfApply.candidate_info)


@router.message(SelfApply.candidate_info)
async def sa_candidate_info(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text or not any(ch.isdigit() for ch in text):
        await message.answer(
            "Укажите имя и возраст — в тексте должно быть число. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(candidate_info=text)
    await message.answer("Ваш номер телефона? (например: +79991234567)", reply_markup=cancel_keyboard())
    await state.set_state(SelfApply.phone)


@router.message(SelfApply.phone)
async def sa_phone(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not PHONE_RE.match(text):
        await message.answer(
            "Некорректный номер телефона. Введите в формате +79991234567.",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(phone=text)
    await message.answer(
        'Ваш юзернейм в Telegram? (например: @username; если юзернейма нет — нажмите «Пропустить пункт» или отправьте "-")',
        reply_markup=skip_or_cancel_keyboard("sa_skip_username"),
    )
    await state.set_state(SelfApply.username)


@router.callback_query(F.data == "sa_skip_username", SelfApply.username)
async def sa_skip_username(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(username=None)
    await callback.message.edit_text(
        "Когда вам удобно на собеседование? (примерно, в формате ДД.ММ.ГГГГ ЧЧ:ММ, например 25.05.2026 14:00)",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(SelfApply.interview_datetime)


@router.message(SelfApply.username)
async def sa_username(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not USERNAME_RE.match(text):
        await message.answer(
            'Введите юзернейм в формате @username, нажмите кнопку «Пропустить пункт», либо отправьте "-".',
            reply_markup=skip_or_cancel_keyboard("sa_skip_username"),
        )
        return
    await state.update_data(username=None if text == "-" else text)
    await message.answer(
        "Когда вам удобно на собеседование? (примерно, в формате ДД.ММ.ГГГГ ЧЧ:ММ, например 25.05.2026 14:00)",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(SelfApply.interview_datetime)


@router.message(SelfApply.interview_datetime)
async def sa_interview_datetime(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not DATETIME_RE.match(text):
        await message.answer(
            "Некорректный формат. Введите как ДД.ММ.ГГГГ ЧЧ:ММ, например 25.05.2026 14:00.",
            reply_markup=cancel_keyboard(),
        )
        return
    try:
        datetime.strptime(text, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(
            "Такой даты/времени не существует. Попробуйте ещё раз.", reply_markup=cancel_keyboard()
        )
        return

    data = await state.get_data()
    requester_username = (
        f"@{message.from_user.username}" if message.from_user.username else "(без username)"
    )
    record = storage.add_hr_record(
        {
            "candidate_info": data["candidate_info"],
            "phone": data["phone"],
            "username": data.get("username"),
            "interview_datetime": text,
            "hr_id": None,
            "hr_username": "Самозапись",
            "status": "pending",
            "requester_id": message.from_user.id,
            "requester_username": requester_username,
        }
    )
    await state.clear()

    is_admin = await IsChannelAdmin()(message, message.bot)
    await message.answer(
        "Заявка отправлена, дождитесь подтверждения от HR ✅",
        reply_markup=main_menu_keyboard(is_admin, storage.is_hr(message.from_user.id)),
    )

    settings = storage.get_settings()
    topic_id = settings.get("target_topic_id")
    card = format_moderation_card(record)
    try:
        sent = await message.bot.send_message(
            TELEGRAM_CHANNEL_ID,
            card,
            message_thread_id=topic_id,
            parse_mode="HTML",
            reply_markup=moderation_keyboard(record["id"]),
        )
        storage.update_record(record["id"], channel_chat_id=sent.chat.id, channel_message_id=sent.message_id)
    except Exception:
        pass
