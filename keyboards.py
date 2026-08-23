from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard(is_admin: bool, is_hr: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_admin:
        b.button(text="⚙️ Админ-панель", callback_data="admin_panel")
    if is_hr:
        b.button(text="📋 HR-функции", callback_data="hr_panel")
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
    b.button(text="⬅️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def hr_panel_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Записать нового кандидата", callback_data="hr_new_record")
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
