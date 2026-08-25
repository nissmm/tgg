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
    b.button(text="📌 Выбрать топик для уведомлений", callback_data="admin_select_topic")
    b.button(text="👤 Пользователи", callback_data="admin_list_users")
    b.button(text="➕ Назначить роль HR", callback_data="admin_assign_hr")
    b.button(text="➖ Снять роль HR", callback_data="admin_remove_hr")
    b.button(text="👥 Список HR", callback_data="admin_list_hr")
    b.button(text="📊 Таблица записей HR", callback_data="admin_hr_table")
    b.button(text="✏️ Все записи", callback_data="admin_all_records:0")
    b.button(text="🛎️ Заявки на модерации", callback_data="admin_pending_list:0")
    b.button(text="🎯 План на день", callback_data="admin_set_plan")
    b.button(text="⬅️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def hr_panel_keyboard(shift_active: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Записать нового кандидата", callback_data="hr_new_record")
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
        label = f"#{r['id']} {r['candidate_info'][:22]}"
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
    b.button(text="⬅️ Назад", callback_data=f"{list_prefix}:{page}")
    b.adjust(1)
    return b.as_markup()


def moderation_keyboard(record_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Одобрить", callback_data=f"modrec:approve:{record_id}")
    b.button(text="❌ Отклонить", callback_data=f"modrec:reject:{record_id}")
    b.adjust(2)
    return b.as_markup()
