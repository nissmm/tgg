import html
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.types.input_rich_message import InputRichMessage

import storage
from filters import IsChannelAdmin
from keyboards import (
    admin_panel_keyboard,
    cancel_keyboard,
    hr_table_filters_keyboard,
    moderation_keyboard,
    records_list_keyboard,
    topics_keyboard,
)
from states import AssignRole, RemoveRole, SetPlan

router = Router()
router.message.filter(IsChannelAdmin())
router.callback_query.filter(IsChannelAdmin())


def _format_users_list(users: dict) -> str:
    if not users:
        return "Пока никто не писал боту /start."
    lines = ["Пользователи, которые запускали бота:"]
    for uid, info in users.items():
        lines.append(f"{info['username']} — `{uid}`")
    lines.append("\nНажмите на id, чтобы скопировать его.")
    return "\n".join(lines)


def _format_users_plain(users: dict) -> str:
    if not users:
        return "Пока никто не писал боту /start."
    lines = ["Пользователи, которые запускали бота:"]
    for uid, info in users.items():
        lines.append(f"{info['username']} - {uid}")
    return "\n".join(lines)


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("⚙️ Админ-панель", reply_markup=admin_panel_keyboard())


@router.callback_query(F.data == "admin_list_users")
async def list_users(callback: CallbackQuery):
    await callback.answer()
    text = _format_users_plain(storage.get_users())
    await callback.message.edit_text(text, reply_markup=admin_panel_keyboard())


# ---------------------------------------------------------------- topics --
@router.callback_query(F.data == "admin_select_topic")
async def select_topic(callback: CallbackQuery):
    await callback.answer()
    topics = storage.get_topics()
    if not topics:
        await callback.message.edit_text(
            "Пока не обнаружено ни одного топика.\n\n"
            "Telegram Bot API не даёт боту способа заранее получить список "
            "топиков форума — бот запоминает топик, как только в нём "
            "появляется хотя бы одно сообщение. Напишите любое сообщение в "
            "нужном топике целевой группы, затем откройте этот пункт снова.",
            reply_markup=admin_panel_keyboard(),
        )
        return
    await callback.message.edit_text(
        "Выберите топик, в который бот будет отправлять уведомления:",
        reply_markup=topics_keyboard(topics),
    )


@router.callback_query(F.data.startswith("set_topic:"))
async def set_topic(callback: CallbackQuery):
    raw = callback.data.split(":", 1)[1]
    topic_id = None if raw == "none" else int(raw)
    storage.set_target_topic(topic_id)
    await callback.answer("Топик установлен ✅", show_alert=True)
    await callback.message.edit_text("⚙️ Админ-панель", reply_markup=admin_panel_keyboard())


# ------------------------------------------------------------- hr roles ---
@router.callback_query(F.data == "admin_assign_hr")
async def assign_hr_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    users = storage.get_users()
    text = _format_users_list(users) + "\n\nОтправьте tg id пользователя, которому нужно выдать роль HR."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=cancel_keyboard())
    await state.set_state(AssignRole.waiting_for_id)


@router.message(AssignRole.waiting_for_id)
async def assign_hr_finish(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(
            "Некорректный tg id — нужно ввести число. Попробуйте ещё раз или отмените.",
            reply_markup=cancel_keyboard(),
        )
        return
    user_id = int(raw)
    users = storage.get_users()
    username = users.get(user_id, {}).get("username", "")
    storage.add_hr(user_id, username)
    await state.clear()
    await message.answer(
        f"Пользователю `{user_id}` выдана роль HR ✅",
        parse_mode="Markdown",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(F.data == "admin_remove_hr")
async def remove_hr_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    hr_roles = storage.get_hr_roles()
    users = storage.get_users()
    if not hr_roles:
        await callback.message.edit_text("Список HR пуст.", reply_markup=admin_panel_keyboard())
        return
    lines = ["Текущие HR:"]
    for uid in hr_roles:
        username = users.get(uid, {}).get("username", "неизвестно")
        lines.append(f"{username} — `{uid}`")
    lines.append("\nОтправьте tg id пользователя, у которого нужно снять роль HR.")
    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=cancel_keyboard())
    await state.set_state(RemoveRole.waiting_for_id)


@router.message(RemoveRole.waiting_for_id)
async def remove_hr_finish(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(
            "Некорректный tg id — нужно ввести число. Попробуйте ещё раз или отмените.",
            reply_markup=cancel_keyboard(),
        )
        return
    user_id = int(raw)
    storage.remove_hr(user_id)
    await state.clear()
    await message.answer(
        f"У пользователя `{user_id}` снята роль HR ✅",
        parse_mode="Markdown",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(F.data == "admin_list_hr")
async def list_hr(callback: CallbackQuery):
    await callback.answer()
    hr_roles = storage.get_hr_roles()
    users = storage.get_users()
    if not hr_roles:
        text = "Список HR пуст."
    else:
        lines = ["Текущие HR:"]
        for uid in hr_roles:
            username = users.get(uid, {}).get("username", "неизвестно")
            lines.append(f"{username} — `{uid}`")
        text = "\n".join(lines)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel_keyboard())


# -------------------------------------------------------------- hr table --
def _filter_records(records: list, period: str) -> list:
    if period == "all":
        return records
    now = datetime.now()
    if period == "today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        cutoff = now - timedelta(days=7)
    elif period == "month":
        cutoff = now - timedelta(days=30)
    else:
        return records
    return [r for r in records if datetime.fromisoformat(r["created_at"]) >= cutoff]


@router.callback_query(F.data == "admin_hr_table")
async def hr_table_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Выберите период для отображения записей:", reply_markup=hr_table_filters_keyboard()
    )


def _build_hr_table_html(records: list) -> str:
    headers = ("Кто записал", "Кого и сколько лет", "Телефон", "Юз", "Дата и время собеса")
    header_row = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"

    body_rows = []
    for r in records:
        cells = (
            r.get("hr_username") or r.get("recorded_by") or "—",
            r["candidate_info"],
            r["phone"],
            r.get("username") or "—",
            r.get("interview_datetime", r.get("interview_date", "—")),
        )
        body_rows.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in cells) + "</tr>")

    return "<table bordered striped>" + header_row + "".join(body_rows) + "</table>"


@router.callback_query(F.data.startswith("hrtable_filter:"))
async def hr_table_show(callback: CallbackQuery):
    await callback.answer()
    period = callback.data.split(":", 1)[1]
    records = _filter_records([r for r in storage.get_hr_records() if r.get("status", "approved") == "approved"], period)
    keyboard = hr_table_filters_keyboard()

    if not records:
        await callback.message.edit_text("Записей за выбранный период нет.", reply_markup=keyboard)
        return

    rich_message = InputRichMessage(html=_build_hr_table_html(records))
    await callback.bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        rich_message=rich_message,
        reply_markup=keyboard,
    )


# ------------------------------------------------------ заявки на модерации
@router.callback_query(F.data.startswith("admin_pending_list:"))
async def admin_pending_list(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    pending = sorted(storage.get_pending_records(), key=lambda r: r["created_at"])
    if not pending:
        await callback.message.edit_text("Заявок на модерации нет.", reply_markup=admin_panel_keyboard())
        return
    await callback.message.edit_text(
        f"Заявки на модерации ({len(pending)}):",
        reply_markup=records_list_keyboard(pending, page, "admin_pending_list", "admin_pending_view", "admin_panel"),
    )


@router.callback_query(F.data.startswith("admin_pending_view:"))
async def admin_pending_view(callback: CallbackQuery):
    await callback.answer()
    _, raw_id, raw_page = callback.data.split(":")
    record = storage.get_record(int(raw_id))
    if not record or record.get("status") != "pending":
        await callback.message.edit_text("Заявка не найдена или уже обработана.", reply_markup=admin_panel_keyboard())
        return
    text = "\n".join(
        [
            f"Заявка #{record['id']}",
            "",
            f"От: {record.get('requester_username', '—')}",
            f"Кандидат: {record['candidate_info']}",
            f"Телефон: {record['phone']}",
            f"Юз: {record.get('username') or '—'}",
            f"Желаемое время собеса: {record.get('interview_datetime', '—')}",
        ]
    )
    await callback.message.edit_text(text, reply_markup=moderation_keyboard(record["id"]))


# ------------------------------------------------------------------- план --
@router.callback_query(F.data == "admin_set_plan")
async def admin_set_plan_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    current = storage.get_daily_plan()
    await callback.message.edit_text(
        f"Текущий план на день: {current}\nВведите новое значение (целое число):",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(SetPlan.waiting_value)


@router.message(SetPlan.waiting_value)
async def admin_set_plan_finish(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("Введите положительное целое число.", reply_markup=cancel_keyboard())
        return
    storage.set_daily_plan(int(text))
    await state.clear()
    await message.answer(f"План на день установлен: {text} ✅", reply_markup=admin_panel_keyboard())
