from datetime import datetime
from typing import Optional


def format_dt(value: Optional[str]) -> str:
    """ISO-строка -> ДД.ММ.ГГГГ ЧЧ:ММ, либо '—', если значения нет."""
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value


def format_duration(seconds: float) -> str:
    total_minutes = int(seconds // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}ч {minutes}м"


def progress_bar(current: int, target: int, length: int = 10) -> str:
    if target <= 0:
        return f"{current}/0"
    filled = min(length, round(length * current / target))
    bar = "▓" * filled + "░" * (length - filled)
    suffix = " 👍" if current >= target else ""
    return f"{bar} {current}/{target}{suffix}"


def format_channel_notification(record: dict) -> str:
    return "\n".join(
        [
            "🆕 Новая запись HR",
            "",
            f"Записал: {record.get('hr_username') or '—'}",
            f"Кандидат: {record['candidate_info']}",
            f"Телефон: {record['phone']}",
            f"Юз: {record.get('username') or '—'}",
            f"Время собеса: {record.get('interview_datetime', '—')}",
        ]
    )


def format_record_card(record: dict) -> str:
    return "\n".join(
        [
            f"Запись #{record['id']}",
            "",
            f"Кого и сколько лет: {record['candidate_info']}",
            f"Телефон: {record['phone']}",
            f"Юз: {record.get('username') or '—'}",
            f"Дата и время собеса: {record.get('interview_datetime', record.get('interview_date', '—'))}",
            f"Записал: {record.get('hr_username') or record.get('recorded_by') or '—'}",
            f"Статус: {record.get('status', 'approved')}",
        ]
    )
