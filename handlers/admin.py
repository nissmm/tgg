from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import storage
from filters import IsChannelAdmin
from keyboards import (
    admin_panel_keyboard,
    cancel_keyboard,
    hr_table_filters_keyboard,
    topics_keyboard,
)
from states import AssignRole, RemoveRole

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


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ Админ-панель", reply_markup=admin_panel_keyboard())
    await callback.answer()


# ---------------------------------------------------------------- topics --
@router.callback_query(F.data == "admin_select_topic")
async def select_topic(callback: CallbackQuery):
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
        await callback.answer()
        return
    await callback.message.edit_text(
        "Выберите топик, в который бот будет отправлять уведомления:",
        reply_markup=topics_keyboard(topics),
    )
    await callback.answer()


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
    users = storage.get_users()
    text = _format_users_list(users) + "\n\nОтправьте tg id пользователя, которому нужно выдать роль HR."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=cancel_keyboard())
    await state.set_state(AssignRole.waiting_for_id)
    await callback.answer()


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
    storage.add_hr(user_id)
    await state.clear()
    await message.answer(
        f"Пользователю `{user_id}` выдана роль HR ✅",
        parse_mode="Markdown",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(F.data == "admin_remove_hr")
async def remove_hr_start(callback: CallbackQuery, state: FSMContext):
    hr_roles = storage.get_hr_roles()
    users = storage.get_users()
    if not hr_roles:
        await callback.message.edit_text("Список HR пуст.", reply_markup=admin_panel_keyboard())
        await callback.answer()
        return
    lines = ["Текущие HR:"]
    for uid in hr_roles:
        username = users.get(uid, {}).get("username", "неизвестно")
        lines.append(f"{username} — `{uid}`")
    lines.append("\nОтправьте tg id пользователя, у которого нужно снять роль HR.")
    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=cancel_keyboard())
    await state.set_state(RemoveRole.waiting_for_id)
    await callback.answer()


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
    await callback.answer()


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
    await callback.message.edit_text("Выберите период для отображения записей:", reply_markup=hr_table_filters_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("hrtable_filter:"))
async def hr_table_show(callback: CallbackQuery):
    period = callback.data.split(":", 1)[1]
    records = _filter_records(storage.get_hr_records(), period)
    if not records:
        await callback.message.edit_text("Записей за выбранный период нет.", reply_markup=hr_table_filters_keyboard())
        await callback.answer()
        return

    header = f"{'#':<4}{'Кто записал':<14}{'Кандидат':<18}{'Телефон':<14}{'Юз':<14}{'Собес':<11}"
    lines = [header, "-" * len(header)]
    for r in records:
        lines.append(
            f"{str(r['id']):<4}{r['recorded_by'][:13]:<14}{r['candidate_info'][:17]:<18}"
            f"{r['phone'][:13]:<14}{r['username'][:13]:<14}{r['interview_date'][:10]:<11}"
        )
    text = "<pre>" + "\n".join(lines) + "</pre>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=hr_table_filters_keyboard())
    await callback.answer()
