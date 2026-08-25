import html
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


def get_hr_rank(count: int) -> dict:
    RANKS = [
        (0, "🥉 Стажёр HR", 5, "🥈 Младший HR"),
        (5, "🥈 Младший HR", 15, "🥇 HR Специалист"),
        (15, "🥇 HR Специалист", 30, "💎 Ведущий HR"),
        (30, "💎 Ведущий HR", 50, "👑 HR Master"),
        (50, "👑 HR Master", None, None),
    ]
    current_rank = RANKS[0]
    for r in RANKS:
        if count >= r[0]:
            current_rank = r
        else:
            break

    _, title, next_threshold, next_title = current_rank
    if next_threshold is None:
        progress_text = "👑 Максимальный ранг!"
    else:
        prev_min = current_rank[0]
        span = next_threshold - prev_min
        progress_in_span = count - prev_min
        needed = next_threshold - count
        bar = progress_bar(progress_in_span, span, length=8)
        progress_text = f"{bar} (ещё {needed} до {next_title})"

    return {
        "title": title,
        "progress_text": progress_text,
    }


def format_hr_profile(user_id: int, profile: dict, records: list, plan: int, shift_active: bool) -> str:
    total_count = len(records)
    today = datetime.now().date()
    records_today = [
        r
        for r in records
        if datetime.fromisoformat(r.get("created_at", datetime.now().isoformat())).date() == today
    ]

    last_rec = max(records, key=lambda r: r.get("created_at", ""), default=None)
    last_interview_dt = (
        last_rec.get("interview_datetime") or last_rec.get("interview_date") or "—"
        if last_rec
        else "—"
    )
    last_created_at = format_dt(last_rec.get("created_at")) if last_rec else "—"
    joined_at_str = format_dt(profile.get("joined_at"))

    rank_info = get_hr_rank(total_count)

    worked_seconds = profile.get("total_worked_seconds", 0.0)
    current_shift_str = ""
    if shift_active and profile.get("shift_start"):
        try:
            curr_shift_sec = (datetime.now() - datetime.fromisoformat(profile["shift_start"])).total_seconds()
            worked_seconds += curr_shift_sec
            current_shift_str = f" (идёт {format_duration(curr_shift_sec)})"
        except Exception:
            pass

    days_joined = "—"
    if profile.get("joined_at"):
        try:
            joined_dt = datetime.fromisoformat(profile["joined_at"])
            delta_days = (datetime.now() - joined_dt).days
            days_joined = f"{max(delta_days, 1)} дн."
        except Exception:
            pass

    shift_status = "🟢 Смена активна" + current_shift_str if shift_active else "⚪ Не на смене"
    username = profile.get("username") or f"ID {user_id}"

    return "\n".join(
        [
            f"👤 <b>Профиль участника (HR):</b> {html.escape(str(username))}",
            "",
            "📊 <b>Статистика:</b>",
            f"1. <b>Сколько записал:</b> {total_count} (сегодня: {len(records_today)})",
            f"2. <b>Последняя запись (важное время):</b> {html.escape(str(last_interview_dt))}",
            f"3. <b>Время последней анкеты:</b> {last_created_at}",
            f"4. <b>Дата присоединения:</b> {joined_at_str} (стаж: {days_joined})",
            f"5. <b>Визуал по рангам:</b> {rank_info['title']}",
            f"   └ <i>{rank_info['progress_text']}</i>",
            f"6. <b>Время работы:</b>",
            f"   • Всего на сменах: {format_duration(worked_seconds)}",
            f"   • Текущий статус: {shift_status}",
            "",
            f"🎯 <b>План на сегодня:</b> {progress_bar(len(records_today), plan)}",
        ]
    )


def format_channel_notification(record: dict) -> str:
    return "\n".join(
        [
            "🆕 <b>Новая запись HR</b>",
            "",
            f"Записал: {html.escape(str(record.get('hr_username') or '—'))}",
            f"Кандидат: {html.escape(str(record['candidate_info']))}",
            f"Телефон: <code>{html.escape(str(record['phone']))}</code>",
            f"Юз: {html.escape(str(record.get('username') or '—'))}",
            f"Время собеса: {html.escape(str(record.get('interview_datetime', '—')))}",
        ]
    )


def format_moderation_card(record: dict) -> str:
    status_label = {
        "pending": "🆕 На модерации",
        "postponed": "⏳ Отложена на рассмотрение",
        "approved": "✅ Одобрена",
        "rejected": "❌ Отклонена",
    }.get(record.get("status", "pending"), record.get("status"))

    lines = [
        f"<b>Заявка #{record['id']}</b> ({status_label})",
        "",
        f"От: {html.escape(str(record.get('requester_username') or '—'))} (<code>{record.get('requester_id') or '—'}</code>)",
        f"Кандидат: {html.escape(str(record['candidate_info']))}",
        f"Телефон: <code>{html.escape(str(record['phone']))}</code>",
        f"Юз: {html.escape(str(record.get('username') or '—'))}",
        f"Желаемое время собеса: {html.escape(str(record.get('interview_datetime', '—')))}",
    ]

    tickets = record.get("tickets", [])
    if tickets:
        lines.append(f"\n💬 <i>Сообщений в тикете: {len(tickets)}</i>")

    return "\n".join(lines)


def format_ticket_history(record: dict) -> str:
    tickets = record.get("tickets", [])
    header = (
        f"📜 <b>История тикета по заявке #{record['id']}</b>\n"
        f"👤 Кандидат: <b>{html.escape(str(record['candidate_info']))}</b>\n"
        f"📞 Телефон: <code>{html.escape(str(record['phone']))}</code>\n"
        f"💬 Юз: {html.escape(str(record.get('username') or '—'))}\n"
        "────────────────────\n"
    )

    if not tickets:
        return header + "<i>История сообщений пуста. Нажмите «Написать сообщение», чтобы связаться с кандидатом.</i>"

    body_lines = []
    for msg in tickets:
        created = format_dt(msg.get("created_at"))
        author = html.escape(str(msg.get("author_name", "—")))
        text = html.escape(str(msg.get("text", "")))
        icon = "👔" if msg.get("sender_type") == "hr" else "👤"
        body_lines.append(f"[{created}] {icon} <b>{author}</b>:\n{text}\n")

    return header + "\n".join(body_lines)


def format_record_card(record: dict) -> str:
    return "\n".join(
        [
            f"<b>Запись #{record['id']}</b>",
            "",
            f"Кого и сколько лет: {html.escape(str(record['candidate_info']))}",
            f"Телефон: <code>{html.escape(str(record['phone']))}</code>",
            f"Юз: {html.escape(str(record.get('username') or '—'))}",
            f"Дата и время собеса: {html.escape(str(record.get('interview_datetime', record.get('interview_date', '—'))))}",
            f"Записал: {html.escape(str(record.get('hr_username') or record.get('recorded_by') or '—'))}",
            f"Статус: {html.escape(str(record.get('status', 'approved')))}",
        ]
    )
