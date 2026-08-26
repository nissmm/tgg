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
    """Уведомление в топик о записи от HR (чистый текст, без кнопок)."""
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


def format_channel_self_apply_notification(record: dict) -> str:
    """Уведомление в топик о новой самозаписи (чистый текст, без кнопок)."""
    return "\n".join(
        [
            f"🆕 <b>Заявка на модерацию (самозапись) #{record['id']}</b>",
            "",
            f"От: {html.escape(str(record.get('requester_username') or '—'))} (<code>{record.get('requester_id') or '—'}</code>)",
            f"Кандидат: {html.escape(str(record['candidate_info']))}",
            f"Телефон: <code>{html.escape(str(record['phone']))}</code>",
            f"Юз: {html.escape(str(record.get('username') or '—'))}",
            f"Желаемое время собеса: {html.escape(str(record.get('interview_datetime', '—')))}",
            "",
            "ℹ️ <i>Рассмотрение заявок и общение — в личных сообщениях с ботом.</i>",
        ]
    )


def format_channel_event_notification(title: str, text: str) -> str:
    """Информационное уведомление о событии в чат/топик (чистый текст, без кнопок)."""
    return f"{title}\n\n{text}"


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
        f"Создана: {format_dt(record.get('created_at'))}",
    ]

    # Логи действий HR
    if record.get("handled_by_username"):
        handled_act = "Одобрил(а)" if record.get("status") == "approved" else "Отклонил(а)" if record.get("status") == "rejected" else "Обработал(а)"
        lines.append(f"\n👤 <b>{handled_act}:</b> {html.escape(str(record['handled_by_username']))} ({format_dt(record.get('handled_at'))})")

    tickets = record.get("tickets", [])
    if tickets:
        hr_repliers = {m.get("author_name") for m in tickets if m.get("sender_type") == "hr"}
        repliers_str = ", ".join(hr_repliers) if hr_repliers else "—"
        lines.append(f"💬 <b>Сообщений в тикете:</b> {len(tickets)} (отвечали: {html.escape(repliers_str)})")

    return "\n".join(lines)


def format_ticket_history(record: dict) -> str:
    tickets = record.get("tickets", [])
    status_label = {
        "pending": "🆕 На модерации",
        "postponed": "⏳ Отложена",
        "approved": "✅ Одобрена",
        "rejected": "❌ Отклонена",
    }.get(record.get("status", "pending"), record.get("status"))

    header = (
        f"📜 <b>История тикета по заявке #{record['id']}</b> ({status_label})\n"
        f"👤 Кандидат: <b>{html.escape(str(record['candidate_info']))}</b>\n"
        f"📞 Телефон: <code>{html.escape(str(record['phone']))}</code>\n"
        f"💬 Юз: {html.escape(str(record.get('username') or '—'))}\n"
        f"🕒 Время собеса: {html.escape(str(record.get('interview_datetime', '—')))}\n"
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


def build_self_apply_table_html(records: list) -> str:
    """HTML-таблица для самозаписей с полным логированием действий HR."""
    headers = ("ID", "Кандидат", "Телефон", "Юз", "Собес", "Статус", "Кто обработал", "Отвечали в тикете")
    header_row = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"

    status_map = {
        "pending": "🆕 На модерации",
        "postponed": "⏳ Отложена",
        "approved": "✅ Одобрена",
        "rejected": "❌ Отклонена",
    }

    body_rows = []
    for r in records:
        tickets = r.get("tickets", [])
        hr_repliers = {m.get("author_name") for m in tickets if m.get("sender_type") == "hr"}
        repliers_str = f"{', '.join(hr_repliers)} ({len(tickets)})" if hr_repliers else ("Есть сообщ." if tickets else "—")

        handled_str = r.get("handled_by_username") or (r.get("hr_username") if r.get("hr_username") != "Самозапись" else "—") or "—"
        status_text = status_map.get(r.get("status", "pending"), r.get("status", "pending"))

        cells = (
            f"#{r['id']}",
            r["candidate_info"],
            r["phone"],
            r.get("username") or "—",
            r.get("interview_datetime", "—"),
            status_text,
            handled_str,
            repliers_str,
        )
        body_rows.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in cells) + "</tr>")

    return "<table bordered striped>" + header_row + "".join(body_rows) + "</table>"


STATUS_LABELS = {
    "pending": "🆕 На модерации",
    "postponed": "⏳ Отложена",
    "approved": "✅ Одобрена",
    "rejected": "❌ Отклонена",
}

STATUS_EMOJIS = {
    "pending": "🆕",
    "postponed": "⏳",
    "approved": "✅",
    "rejected": "❌",
}


def is_self_apply_record(record: dict) -> bool:
    return bool(
        record.get("is_self_apply")
        or record.get("requester_id") is not None
        or record.get("hr_username") == "Самозапись"
    )


def get_status_label(status: Optional[str]) -> str:
    if not status:
        return "✅ Одобрена"
    return STATUS_LABELS.get(status, status)


def get_status_emoji(status: Optional[str]) -> str:
    if not status:
        return "✅"
    return STATUS_EMOJIS.get(status, "📄")


def format_record_card(record: dict) -> str:
    status_text = get_status_label(record.get("status", "approved"))
    is_self = is_self_apply_record(record)
    origin_text = "👤 Самозапись кандидата" if is_self else "💼 Запись через HR"
    recorded_by = record.get("hr_username") or record.get("recorded_by") or ("Самозапись" if is_self else "—")
    
    return "\n".join(
        [
            f"<b>Запись #{record['id']}</b> ({status_text})",
            "",
            f"Тип: <b>{origin_text}</b>",
            f"Кого и сколько лет: {html.escape(str(record['candidate_info']))}",
            f"Телефон: <code>{html.escape(str(record['phone']))}</code>",
            f"Юз: {html.escape(str(record.get('username') or '—'))}",
            f"Дата и время собеса: {html.escape(str(record.get('interview_datetime', record.get('interview_date', '—'))))}",
            f"Записал: {html.escape(str(recorded_by))}",
            f"Статус: {status_text}",
        ]
    )
