from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard(is_admin: bool, is_hr: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_admin:
        b.button(text="⚙️ Админ-панель", callback_data="admin_panel")
    if is_hr:
        b.button(text="📋 HR-функции", callback_data="hr_panel")
    b.button(text="📝 Оставить заявку", callback_data="self_apply_start")
    b.adjust(1)
    return b.as_markup()


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Таблица записей HR", callback_data="admin_hr_table")
    b.button(text="📥 Таблица самозаписей", callback_data="admin_self_apply_table")
    b.button(text="🛎️ Заявки на модерации", callback_data="admin_pending_list:0")
    b.button(text="✏️ Все записи HR", callback_data="admin_all_records:0")
    b.button(text="🎯 План на день", callback_data="admin_set_plan")
    b.button(text="📌 Выбрать топик для уведомлений", callback_data="admin_select_topic")
    b.button(text="👥 Список HR", callback_data="admin_list_hr")
    b.button(text="➕ Назначить роль HR", callback_data="admin_assign_hr")
    b.button(text="➖ Снять роль HR", callback_data="admin_remove_hr")
    b.button(text="👤 Пользователи", callback_data="admin_list_users")
    b.button(text="⬅️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def hr_panel_keyboard(shift_active: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Записать нового кандидата", callback_data="hr_new_record")
    b.button(text="🛎️ Заявки на модерацию", callback_data="hr_pending_list:0")
    b.button(text="✏️ Мои записи", callback_data="hr_my_records:0")
    b.button(text="👤 Мой профиль", callback_data="hr_profile")
    if shift_active:
        b.button(text="🔴 Закончить смену", callback_data="hr_shift_end")
    else:
        b.button(text="🟢 Начать смену", callback_data="hr_shift_start")
    b.button(text="⬅️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def topics_keyboard(topics: dict) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for topic_id, name in topics.items():
        payload = "none" if topic_id is None else str(topic_id)
        b.button(text=name, callback_data=f"set_topic:{payload}")
    b.button(text="⬅️ Назад", callback_data="admin_panel")
    b.adjust(1)
    return b.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="cancel_fsm")
    return b.as_markup()


def hr_table_filters_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Все записи", callback_data="hrtable_filter:all")
    b.button(text="За сегодня", callback_data="hrtable_filter:today")
    b.button(text="За неделю", callback_data="hrtable_filter:week")
    b.button(text="За месяц", callback_data="hrtable_filter:month")
    b.button(text="⬅️ Назад", callback_data="admin_panel")
    b.adjust(2, 2, 1)
    return b.as_markup()


def self_apply_table_filters_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Все самозаписи", callback_data="satab_filter:all")
    b.button(text="За сегодня", callback_data="satab_filter:today")
    b.button(text="За неделю", callback_data="satab_filter:week")
    b.button(text="За месяц", callback_data="satab_filter:month")
    b.button(text="⬅️ Назад", callback_data="admin_panel")
    b.adjust(2, 2, 1)
    return b.as_markup()


STATUS_EMOJIS = {
    "pending": "🆕",
    "postponed": "⏳",
    "approved": "✅",
    "rejected": "❌",
}


def records_list_keyboard(
    records: list,
    page: int,
    list_prefix: str,
    open_prefix: str,
    back_target: str,
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    start = page * page_size
    chunk = records[start : start + page_size]

    for r in chunk:
        emoji = STATUS_EMOJIS.get(r.get("status", "approved"), "📄")
        label = f"{emoji} #{r['id']} {r['candidate_info'][:18]}"
        b.button(text=label, callback_data=f"{open_prefix}:{r['id']}:{page}")

    layout = [1] * len(chunk)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(("⬅️", f"{list_prefix}:{page - 1}"))
    if start + page_size < len(records):
        nav_buttons.append(("➡️", f"{list_prefix}:{page + 1}"))
    for text, data in nav_buttons:
        b.button(text=text, callback_data=data)
    if nav_buttons:
        layout.append(len(nav_buttons))

    b.button(text="⬅️ Назад", callback_data=back_target)
    layout.append(1)

    b.adjust(*layout)
    return b.as_markup()


def edit_fields_keyboard(record_id: int, list_prefix: str, page: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    fields = [
        ("candidate_info", "Кого и сколько лет"),
        ("phone", "Телефон"),
        ("username", "Юз кандидата"),
        ("interview_datetime", "Дата и время собеса"),
    ]
    for key, label in fields:
        b.button(text=f"✏️ {label}", callback_data=f"editrec:{record_id}:{key}")
    b.button(text="🗑️ Удалить запись", callback_data=f"delrec_ask:{record_id}:{list_prefix}:{page}")
    b.button(text="⬅️ Назад", callback_data=f"{list_prefix}:{page}")
    b.adjust(1)
    return b.as_markup()


def confirm_delete_record_keyboard(record_id: int, list_prefix: str, page: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🗑️ Да, удалить запись", callback_data=f"delrec_confirm:{record_id}:{list_prefix}:{page}")
    b.button(text="❌ Отмена", callback_data=f"delrec_cancel:{record_id}:{list_prefix}:{page}")
    b.adjust(1)
    return b.as_markup()


def skip_or_cancel_keyboard(skip_data: str = "skip_username") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⏭️ Пропустить пункт", callback_data=skip_data)
    b.button(text="❌ Отмена", callback_data="cancel_fsm")
    b.adjust(1)
    return b.as_markup()


def moderation_keyboard(record_id: int, ticket_count: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Одобрить", callback_data=f"modrec:approve:{record_id}")
    b.button(text="❌ Отклонить", callback_data=f"modrec:reject:{record_id}")
    b.button(text="⏳ Отложить", callback_data=f"modrec:postpone:{record_id}")
    b.button(text="💬 Ответить на заявку", callback_data=f"modrec:reply:{record_id}")
    ticket_label = f"📜 Тикет ({ticket_count})" if ticket_count > 0 else "📜 Тикет"
    b.button(text=ticket_label, callback_data=f"modrec:ticket:{record_id}")
    b.adjust(2, 2, 1)
    return b.as_markup()


def ticket_dialog_keyboard(record_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💬 Написать сообщение", callback_data=f"modrec:reply:{record_id}")
    b.button(text="✅ Одобрить", callback_data=f"modrec:approve:{record_id}")
    b.button(text="❌ Отклонить", callback_data=f"modrec:reject:{record_id}")
    b.button(text="⏳ Отложить", callback_data=f"modrec:postpone:{record_id}")
    b.button(text="⬅️ К заявке", callback_data=f"modrec:view:{record_id}")
    b.adjust(1, 2, 2)
    return b.as_markup()


def user_ticket_keyboard(record_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💬 Ответить HR", callback_data=f"user_reply_ticket:{record_id}")
    b.adjust(1)
    return b.as_markup()
