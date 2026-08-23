from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

import storage
from config import TELEGRAM_CHANNEL_ID


class IsChannelAdmin(BaseFilter):
    """True, если пользователь является админом/создателем целевого канала/группы."""

    async def __call__(self, event: Message | CallbackQuery, bot: Bot) -> bool:
        user_id = event.from_user.id
        try:
            member = await bot.get_chat_member(TELEGRAM_CHANNEL_ID, user_id)
        except Exception:
            return False
        return member.status in ("administrator", "creator")


class IsHR(BaseFilter):
    """True, если пользователю выдана роль HR внутри бота."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return storage.is_hr(event.from_user.id)
