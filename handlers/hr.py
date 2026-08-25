import re
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import storage
from config import TELEGRAM_CHANNEL_ID
from filters import IsHR
from formatting import format_channel_notification, format_dt, format_duration, progress_bar
from keyboards import cancel_keyboard, hr_panel_keyboard
from states import NewHRRecord

router = Router()
router.message.filter(IsHR())
router.callback_query.filter(IsHR())

PHONE_RE = re.compile(r"^\+\d{10,15}$")
USERNAME_RE = re.compile(r"^(-|@[A-Za-z0-9_]{5,32})$")
DATETIME_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$")


@router.callback_query(F.data == "hr_panel")
async def show_hr_panel(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📋 HR-функции",
        reply_markup=hr_panel_keyboard(storage.is_shift_active(callback.from_user.id)),
    )


# --------------------------------------------------------- новая запись ---
@router.callback_query(F.data == "hr_new_record")
async def new_record_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Кого и сколько лет? (например: Иван Иванов, 25 лет)",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(NewHRRecord.candidate_info)


@router.message(NewHRRecord.candidate_info)
async def step_candidate_info(message: Message, state: FSMContext):
    text = (message.text or "").strip()
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
    text = (message.text or "").strip()
    if not PHONE_RE.match(text):
        await message.answer(
            "Некорректный номер телефона. Введите в формате +79991234567.",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(phone=text)
    await message.answer(
        'Юзернейм кандидата в Telegram? (например: @username; если юзернейма нет — отправьте "-")',
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(NewHRRecord.username)


@router.message(NewHRRecord.username)
async def step_username(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not USERNAME_RE.match(text):
        await message.answer(
            'Введите юзернейм в формате @username, либо "-", если его нет.',
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(username=None if text == "-" else text)
    await message.answer(
        "Дата и время собеседования? (примерно, в формате ДД.ММ.ГГГГ ЧЧ:ММ, например 25.05.2026 14:00)",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(NewHRRecord.interview_datetime)


@router.message(NewHRRecord.interview_datetime)
async def step_interview_datetime(message: Message, state: FSMContext, bot: Bot):
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
            "Такой даты/времени не существует. Введите корректные значения.",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()
    hr_username = f"@{message.from_user.username}" if message.from_user.username else "(без username)"
    saved = storage.add_hr_record(
        {
            "candidate_info": data["candidate_info"],
            "phone": data["phone"],
            "username": data.get("username"),
            "interview_datetime": text,
            "hr_id": message.from_user.id,
            "hr_username": hr_username,
            "status": "approved",
        }
    )
    await state.clear()

    settings = storage.get_settings()
    topic_id = settings.get("target_topic_id")
    try:
        sent = await bot.send_message(
            TELEGRAM_CHANNEL_ID,
            format_channel_notification(saved),
            message_thread_id=topic_id,
        )
        storage.update_record(saved["id"], channel_chat_id=sent.chat.id, channel_message_id=sent.message_id)
        result_text = "Запись сохранена и отправлена в канал ✅"
    except Exception as e:
        result_text = f"Запись сохранена, но не удалось отправить уведомление в канал: {e}"

    await message.answer(
        result_text, reply_markup=hr_panel_keyboard(storage.is_shift_active(message.from_user.id))
    )


# -------------------------------------------------------------- профиль ---
@router.callback_query(F.data == "hr_profile")
async def hr_profile(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    profile = storage.get_hr_profile(user_id) or {}
    records = storage.get_records_by_hr(user_id, status="approved")

    total_count = len(records)
    last_record_at = max((r["created_at"] for r in records), default=None)

    today = datetime.now().date()
    records_today = [r for r in records if datetime.fromisoformat(r["created_at"]).date() == today]
    plan = storage.get_daily_plan()

    worked_seconds = profile.get("total_worked_seconds", 0.0)
    shift_active = storage.is_shift_active(user_id)
    if shift_active and profile.get("shift_start"):
        worked_seconds += (datetime.now() - datetime.fromisoformat(profile["shift_start"])).total_seconds()

    text = "\n".join(
        [
            "👤 Мой профиль",
            "",
            f"Записал всего: {total_count}",
            f"Последняя запись: {format_dt(last_record_at)}",
            f"Дата присоединения: {format_dt(profile.get('joined_at'))}",
            f"Смена: {'идёт' if shift_active else 'не начата'}",
            f"Отработано времени: {format_duration(worked_seconds)}",
            f"План на сегодня: {progress_bar(len(records_today), plan)}",
            "🏅 Ранг: скоро",
        ]
    )
    await callback.message.edit_text(text, reply_markup=hr_panel_keyboard(shift_active))


# --------------------------------------------------------------- смена ----
@router.callback_query(F.data == "hr_shift_start")
async def shift_start(callback: CallbackQuery):
    storage.start_shift(callback.from_user.id)
    await callback.answer("Смена начата 🟢")
    await callback.message.edit_text("Смена начата. Хорошей работы!", reply_markup=hr_panel_keyboard(True))


@router.callback_query(F.data == "hr_shift_end")
async def shift_end(callback: CallbackQuery):
    result = storage.end_shift(callback.from_user.id)
    await callback.answer("Смена завершена 🔴")
    if result is None:
        await callback.message.edit_text("Смена не была начата.", reply_markup=hr_panel_keyboard(False))
        return

    duration, shift_start_iso = result
    user_id = callback.from_user.id
    records_during_shift = [
        r for r in storage.get_records_by_hr(user_id, status="approved") if r["created_at"] >= shift_start_iso
    ]
    plan = storage.get_daily_plan()

    await callback.message.edit_text(
        f"Смена завершена. Отработано: {format_duration(duration)}. "
        f"Записано за смену: {len(records_during_shift)}.",
        reply_markup=hr_panel_keyboard(False),
    )

    settings = storage.get_settings()
    topic_id = settings.get("target_topic_id")
    hr_username = f"@{callback.from_user.username}" if callback.from_user.username else "(без username)"
    log_text = "\n".join(
        [
            "📋 Смена завершена",
            "",
            f"HR: {hr_username}",
            f"Длительность: {format_duration(duration)}",
            f"Записано за смену: {len(records_during_shift)}",
            f"План на сегодня: {progress_bar(len(records_during_shift), plan)}",
        ]
    )
    try:
        await callback.bot.send_message(TELEGRAM_CHANNEL_ID, log_text, message_thread_id=topic_id)
    except Exception:
        pass
