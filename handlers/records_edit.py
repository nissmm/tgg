import re
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import storage
from filters import IsChannelAdmin
from formatting import format_record_card
from keyboards import admin_panel_keyboard, cancel_keyboard, edit_fields_keyboard, hr_panel_keyboard, records_list_keyboard
from states import EditRecord

router = Router()

FIELD_LABELS = {
    "candidate_info": "Кого и сколько лет",
    "phone": "Телефон",
    "username": "Юз кандидата",
    "interview_datetime": "Дата и время собеса",
}

PHONE_RE = re.compile(r"^\+\d{10,15}$")
USERNAME_RE = re.compile(r"^(-|@[A-Za-z0-9_]{5,32})$")
DATETIME_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$")


async def _update_channel_message(bot, record: dict) -> None:
    chat_id = record.get("channel_chat_id")
    message_id = record.get("channel_message_id")
    if not chat_id or not message_id:
        return
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=format_record_card(record))
    except Exception:
        pass


# ---------------------------------------------------------- HR: свои записи
@router.callback_query(F.data.startswith("hr_my_records:"))
async def hr_my_records(callback: CallbackQuery):
    if not storage.is_hr(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    page = int(callback.data.split(":")[1])
    records = sorted(
        storage.get_records_by_hr(callback.from_user.id, status="approved"),
        key=lambda r: r["created_at"],
        reverse=True,
    )
    if not records:
        await callback.message.edit_text(
            "У вас пока нет записей.",
            reply_markup=hr_panel_keyboard(storage.is_shift_active(callback.from_user.id)),
        )
        return
    await callback.message.edit_text(
        f"Ваши записи ({len(records)}):",
        reply_markup=records_list_keyboard(records, page, "hr_my_records", "hr_edit_open", "hr_panel"),
    )


@router.callback_query(F.data.startswith("hr_edit_open:"))
async def hr_edit_open(callback: CallbackQuery):
    if not storage.is_hr(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()
    _, raw_id, raw_page = callback.data.split(":")
    record = storage.get_record(int(raw_id))
    if not record or record.get("hr_id") != callback.from_user.id:
        await callback.message.edit_text(
            "Запись не найдена.",
            reply_markup=hr_panel_keyboard(storage.is_shift_active(callback.from_user.id)),
        )
        return
    await callback.message.edit_text(
        format_record_card(record),
        reply_markup=edit_fields_keyboard(record["id"], "hr_my_records", int(raw_page)),
    )


# ------------------------------------------------------- Admin: все записи
@router.callback_query(F.data.startswith("admin_all_records:"))
async def admin_all_records(callback: CallbackQuery):
    if not await IsChannelAdmin()(callback, callback.bot):
        await callback.answer()
        return
    await callback.answer()
    page = int(callback.data.split(":")[1])
    records = sorted(storage.get_hr_records(), key=lambda r: r["created_at"], reverse=True)
    if not records:
        await callback.message.edit_text("Записей пока нет.", reply_markup=admin_panel_keyboard())
        return
    await callback.message.edit_text(
        f"Все записи ({len(records)}):",
        reply_markup=records_list_keyboard(records, page, "admin_all_records", "admin_edit_open", "admin_panel"),
    )


@router.callback_query(F.data.startswith("admin_edit_open:"))
async def admin_edit_open(callback: CallbackQuery):
    if not await IsChannelAdmin()(callback, callback.bot):
        await callback.answer()
        return
    await callback.answer()
    _, raw_id, raw_page = callback.data.split(":")
    record = storage.get_record(int(raw_id))
    if not record:
        await callback.message.edit_text("Запись не найдена.", reply_markup=admin_panel_keyboard())
        return
    await callback.message.edit_text(
        format_record_card(record),
        reply_markup=edit_fields_keyboard(record["id"], "admin_all_records", int(raw_page)),
    )


# ------------------------------------------------------------ редактирование
@router.callback_query(F.data.startswith("editrec:"))
async def start_edit_field(callback: CallbackQuery, state: FSMContext):
    _, raw_id, field = callback.data.split(":")
    record_id = int(raw_id)
    record = storage.get_record(record_id)
    if not record:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    is_admin = await IsChannelAdmin()(callback, callback.bot)
    if not is_admin and record.get("hr_id") != callback.from_user.id:
        await callback.answer("Вы можете редактировать только свои записи.", show_alert=True)
        return

    await callback.answer()
    await state.update_data(record_id=record_id, field=field, admin_scope=is_admin)
    await callback.message.edit_text(
        f"Введите новое значение для поля «{FIELD_LABELS[field]}»:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(EditRecord.waiting_value)


@router.message(EditRecord.waiting_value)
async def save_edit_field(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    record_id = data["record_id"]
    text = (message.text or "").strip()

    if field == "phone" and not PHONE_RE.match(text):
        await message.answer(
            "Некорректный номер телефона. Введите в формате +79991234567.", reply_markup=cancel_keyboard()
        )
        return
    if field == "username":
        if not USERNAME_RE.match(text):
            await message.answer(
                'Введите юзернейм в формате @username, либо "-", если его нет.',
                reply_markup=cancel_keyboard(),
            )
            return
        text = None if text == "-" else text
    if field == "interview_datetime":
        if not DATETIME_RE.match(text):
            await message.answer(
                "Некорректный формат. Введите как ДД.ММ.ГГГГ ЧЧ:ММ.", reply_markup=cancel_keyboard()
            )
            return
        try:
            datetime.strptime(text, "%d.%m.%Y %H:%M")
        except ValueError:
            await message.answer(
                "Такой даты/времени не существует. Попробуйте ещё раз.", reply_markup=cancel_keyboard()
            )
            return
    if field == "candidate_info" and (not text or not any(ch.isdigit() for ch in text)):
        await message.answer(
            "Укажите имя и возраст — должно быть число в тексте.", reply_markup=cancel_keyboard()
        )
        return

    record = storage.update_record(record_id, **{field: text})
    await state.clear()

    if record:
        await _update_channel_message(message.bot, record)

    keyboard = (
        admin_panel_keyboard()
        if data.get("admin_scope")
        else hr_panel_keyboard(storage.is_shift_active(message.from_user.id))
    )
    await message.answer("Запись обновлена ✅", reply_markup=keyboard)
