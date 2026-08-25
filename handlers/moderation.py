import html
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import storage
from config import TELEGRAM_CHANNEL_ID
from filters import IsChannelAdmin
from formatting import format_moderation_card, format_ticket_history
from keyboards import (
    cancel_keyboard,
    moderation_keyboard,
    ticket_dialog_keyboard,
    user_ticket_keyboard,
)
from states import ModeratorReplyTicket, UserReplyTicket

router = Router()


async def _can_moderate(callback: CallbackQuery) -> bool:
    if storage.is_hr(callback.from_user.id):
        return True
    return await IsChannelAdmin()(callback, callback.bot)


@router.callback_query(F.data.startswith("modrec:"))
async def moderate_record(callback: CallbackQuery, state: FSMContext, bot: Bot):
    parts = callback.data.split(":")
    action = parts[1]
    record_id = int(parts[2])
    record = storage.get_record(record_id)
    if not record:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if not await _can_moderate(callback):
        await callback.answer("У вас нет прав модерировать заявки.", show_alert=True)
        return

    reviewer = callback.from_user
    reviewer_username = f"@{reviewer.username}" if reviewer.username else f"ID {reviewer.id}"

    if action == "view":
        await callback.answer()
        tickets = storage.get_ticket_messages(record_id)
        card_text = format_moderation_card(record)
        await callback.message.edit_text(
            card_text,
            parse_mode="HTML",
            reply_markup=moderation_keyboard(record_id, len(tickets)),
        )
        return

    if action == "ticket":
        await callback.answer()
        history_text = format_ticket_history(record)
        await callback.message.edit_text(
            history_text,
            parse_mode="HTML",
            reply_markup=ticket_dialog_keyboard(record_id),
        )
        return

    if action == "reply":
        await callback.answer()
        await state.update_data(record_id=record_id)
        await state.set_state(ModeratorReplyTicket.waiting_text)
        await callback.message.answer(
            f"✍️ <b>Ответ по заявке #{record_id}</b>\n\n"
            f"Кандидат: <b>{html.escape(str(record['candidate_info']))}</b>\n\n"
            "Введите сообщение, которое будет отправлено кандидату в Telegram через бота:",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        return

    if action == "postpone":
        storage.update_record(
            record_id,
            status="postponed",
            handled_by_id=reviewer.id,
            handled_by_username=reviewer_username,
            handled_at=datetime.now().isoformat(),
        )
        storage.log_record_action(record_id, "postponed", reviewer.id, reviewer_username, "Заявка отложена")
        record = storage.get_record(record_id)
        tickets = storage.get_ticket_messages(record_id)
        await callback.answer("Заявка отложена ⏳")
        await callback.message.edit_text(
            format_moderation_card(record),
            parse_mode="HTML",
            reply_markup=moderation_keyboard(record_id, len(tickets)),
        )

        settings = storage.get_settings()
        topic_id = settings.get("target_topic_id")
        try:
            await bot.send_message(
                TELEGRAM_CHANNEL_ID,
                f"⏳ <b>Заявка #{record_id} отложена на рассмотрение</b>\n"
                f"Кандидат: {html.escape(str(record['candidate_info']))}\n"
                f"Обработал: {html.escape(reviewer_username)}",
                message_thread_id=topic_id,
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    if action == "approve":
        if record.get("status") == "approved":
            await callback.answer("Эта заявка уже одобрена.", show_alert=True)
            return

        storage.update_record(
            record_id,
            status="approved",
            hr_id=reviewer.id,
            hr_username=reviewer_username,
            handled_by_id=reviewer.id,
            handled_by_username=reviewer_username,
            handled_at=datetime.now().isoformat(),
            approved_at=datetime.now().isoformat(),
        )
        storage.log_record_action(record_id, "approved", reviewer.id, reviewer_username, "Заявка одобрена")
        await callback.answer("Заявка одобрена ✅")

        requester_id = record.get("requester_id")
        if requester_id:
            try:
                await bot.send_message(
                    requester_id,
                    f"🎉 <b>Ваша заявка #{record_id} одобрена!</b>\n\n"
                    f"Желаемое время собеседования: <b>{html.escape(str(record['interview_datetime']))}</b>\n"
                    "С вами свяжется HR для проведения собеседования.",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        updated_record = storage.get_record(record_id)
        tickets = storage.get_ticket_messages(record_id)
        await callback.message.edit_text(
            format_moderation_card(updated_record),
            parse_mode="HTML",
            reply_markup=moderation_keyboard(record_id, len(tickets)),
        )

        settings = storage.get_settings()
        topic_id = settings.get("target_topic_id")
        try:
            await bot.send_message(
                TELEGRAM_CHANNEL_ID,
                f"✅ <b>Заявка #{record_id} одобрена</b>\n"
                f"Кандидат: {html.escape(str(record['candidate_info']))}\n"
                f"Телефон: <code>{html.escape(str(record['phone']))}</code>\n"
                f"Юз: {html.escape(str(record.get('username') or '—'))}\n"
                f"Время собеса: {html.escape(str(record['interview_datetime']))}\n"
                f"Одобрил(а): {html.escape(reviewer_username)}",
                message_thread_id=topic_id,
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    if action == "reject":
        if record.get("status") == "rejected":
            await callback.answer("Эта заявка уже отклонена.", show_alert=True)
            return

        storage.update_record(
            record_id,
            status="rejected",
            hr_id=reviewer.id,
            hr_username=reviewer_username,
            handled_by_id=reviewer.id,
            handled_by_username=reviewer_username,
            handled_at=datetime.now().isoformat(),
            rejected_at=datetime.now().isoformat(),
        )
        storage.log_record_action(record_id, "rejected", reviewer.id, reviewer_username, "Заявка отклонена")
        await callback.answer("Заявка отклонена ❌")

        requester_id = record.get("requester_id")
        if requester_id:
            try:
                await bot.send_message(
                    requester_id,
                    f"❌ <b>Ваша заявка #{record_id} была отклонена.</b>\n\n"
                    "Благодарим за проявленный интерес!",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        updated_record = storage.get_record(record_id)
        tickets = storage.get_ticket_messages(record_id)
        await callback.message.edit_text(
            format_moderation_card(updated_record),
            parse_mode="HTML",
            reply_markup=moderation_keyboard(record_id, len(tickets)),
        )

        settings = storage.get_settings()
        topic_id = settings.get("target_topic_id")
        try:
            await bot.send_message(
                TELEGRAM_CHANNEL_ID,
                f"❌ <b>Заявка #{record_id} отклонена</b>\n"
                f"Кандидат: {html.escape(str(record['candidate_info']))}\n"
                f"Отклонил(а): {html.escape(reviewer_username)}",
                message_thread_id=topic_id,
                parse_mode="HTML",
            )
        except Exception:
            pass
        return


@router.message(ModeratorReplyTicket.waiting_text)
async def mod_send_ticket_reply(message: Message, state: FSMContext, bot: Bot):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Введите текстовое сообщение для отправки.", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    record_id = data.get("record_id")
    record = storage.get_record(record_id)
    if not record:
        await state.clear()
        await message.answer("Заявка не найдена.")
        return

    sender_name = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else f"{message.from_user.first_name}"
    )

    storage.add_ticket_message(
        record_id=record_id,
        sender_type="hr",
        sender_id=message.from_user.id,
        author_name=sender_name,
        text=text,
    )
    await state.clear()

    requester_id = record.get("requester_id")
    delivery_info = ""
    if requester_id:
        try:
            await bot.send_message(
                requester_id,
                f"📩 <b>Сообщение от HR по заявке #{record_id}:</b>\n\n"
                f"{html.escape(text)}\n\n"
                "<i>Чтобы ответить, нажмите кнопку ниже:</i>",
                parse_mode="HTML",
                reply_markup=user_ticket_keyboard(record_id),
            )
            delivery_info = " (доставлено кандидату в ЛС)"
        except Exception as e:
            delivery_info = f" (не удалось отправить в ЛС: {e})"
    else:
        delivery_info = " (у кандидата нет привязанного Telegram ID)"

    await message.answer(
        f"✅ <b>Ответ записан в тикет #{record_id}</b>{delivery_info}",
        parse_mode="HTML",
        reply_markup=ticket_dialog_keyboard(record_id),
    )

    # Информационное уведомление в канал БЕЗ кнопок
    settings = storage.get_settings()
    topic_id = settings.get("target_topic_id")
    notify_text = "\n".join(
        [
            f"💬 <b>Ответ HR в тикете по заявке #{record_id}</b>",
            "",
            f"HR: {html.escape(sender_name)}",
            f"Кандидат: {html.escape(str(record['candidate_info']))}",
            "",
            f"<b>Сообщение:</b>\n{html.escape(text)}",
        ]
    )
    try:
        await bot.send_message(
            TELEGRAM_CHANNEL_ID,
            notify_text,
            message_thread_id=topic_id,
            parse_mode="HTML",
        )
    except Exception:
        pass


# ------------------------------------------------------------- ответ кандидата
@router.callback_query(F.data.startswith("user_reply_ticket:"))
async def user_start_ticket_reply(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    record_id = int(callback.data.split(":")[1])
    record = storage.get_record(record_id)
    if not record:
        await callback.message.answer("Заявка не найдена.")
        return

    await state.update_data(record_id=record_id)
    await state.set_state(UserReplyTicket.waiting_text)
    await callback.message.answer(
        f"✍️ Введите ваш ответ для HR по заявке #{record_id}:",
        reply_markup=cancel_keyboard(),
    )


@router.message(UserReplyTicket.waiting_text)
async def user_send_ticket_reply(message: Message, state: FSMContext, bot: Bot):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Введите текстовое сообщение.", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    record_id = data.get("record_id")
    record = storage.get_record(record_id)
    if not record:
        await state.clear()
        await message.answer("Заявка не найдена.")
        return

    sender_name = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else f"{message.from_user.first_name}"
    )

    storage.add_ticket_message(
        record_id=record_id,
        sender_type="user",
        sender_id=message.from_user.id,
        author_name=sender_name,
        text=text,
    )
    await state.clear()

    await message.answer("✅ Ваш ответ передан HR. Ожидайте сообщения.")

    # Информационное уведомление в канал/топик БЕЗ кнопок
    settings = storage.get_settings()
    topic_id = settings.get("target_topic_id")
    notify_text = "\n".join(
        [
            f"💬 <b>Новый ответ кандидата в тикете #{record_id}</b>",
            "",
            f"От: {html.escape(sender_name)} (<code>{message.from_user.id}</code>)",
            f"Кандидат: {html.escape(str(record['candidate_info']))}",
            "",
            f"<b>Сообщение:</b>\n{html.escape(text)}",
            "",
            "ℹ️ <i>Для ответа перейдите в личные сообщения с ботом.</i>",
        ]
    )
    try:
        await bot.send_message(
            TELEGRAM_CHANNEL_ID,
            notify_text,
            message_thread_id=topic_id,
            parse_mode="HTML",
        )
    except Exception:
        pass
