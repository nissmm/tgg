from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

import storage
from filters import IsChannelAdmin

router = Router()


async def _can_moderate(callback: CallbackQuery) -> bool:
    if storage.is_hr(callback.from_user.id):
        return True
    return await IsChannelAdmin()(callback, callback.bot)


@router.callback_query(F.data.startswith("modrec:"))
async def moderate_record(callback: CallbackQuery):
    if not await _can_moderate(callback):
        await callback.answer("У вас нет прав модерировать заявки.", show_alert=True)
        return

    _, action, raw_id = callback.data.split(":")
    record_id = int(raw_id)
    record = storage.get_record(record_id)
    if not record:
        await callback.answer("Заявка не найдена (возможно, уже обработана).", show_alert=True)
        return
    if record.get("status") != "pending":
        await callback.answer("Эта заявка уже обработана.", show_alert=True)
        return

    reviewer = callback.from_user
    reviewer_username = f"@{reviewer.username}" if reviewer.username else "(без username)"

    if action == "approve":
        storage.update_record(
            record_id,
            status="approved",
            hr_id=reviewer.id,
            hr_username=reviewer_username,
            approved_at=datetime.now().isoformat(),
        )
        new_text = "\n".join(
            [
                "✅ Заявка одобрена",
                "",
                f"Кандидат: {record['candidate_info']}",
                f"Телефон: {record['phone']}",
                f"Юз: {record.get('username') or '—'}",
                f"Время собеса: {record['interview_datetime']}",
                f"Одобрил: {reviewer_username}",
            ]
        )
        await callback.answer("Заявка одобрена ✅")
    else:
        storage.update_record(record_id, status="rejected")
        new_text = "\n".join(
            [
                "❌ Заявка отклонена",
                "",
                f"Кандидат: {record['candidate_info']}",
                f"Отклонил: {reviewer_username}",
            ]
        )
        await callback.answer("Заявка отклонена")

    await callback.message.edit_text(new_text)
