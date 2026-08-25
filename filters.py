import asyncio
import time

from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

import storage
from config import TELEGRAM_CHANNEL_ID

# Кэш результата get_chat_member: без него каждая кнопка в админ-панели
# делает отдельный сетевой запрос к Telegram (router.callback_query.filter
# висит на каждом callback). Если запрос к api.telegram.org подвисает,
# без явного таймаута aiogram ждёт до 60 секунд (дефолтный таймаут сессии) —
# именно это давало "минуту и больше" на клик. Поэтому: жёсткий таймаут на
# сам вызов + разный TTL кэша для успеха и для сбоя/таймаута.
_ADMIN_CACHE_TTL = 300       # успешная проверка — 5 минут
_ADMIN_CACHE_FAIL_TTL = 20   # ошибка/таймаут — 20 секунд, чтобы быстро попробовать снова
_ADMIN_CHECK_TIMEOUT = 5     # секунд на сам сетевой запрос к Telegram

_admin_cache: dict[int, tuple[bool, float]] = {}  # user_id -> (is_admin, expires_at)


class IsChannelAdmin(BaseFilter):
    """True, если пользователь является админом/создателем целевого канала/группы."""

    async def __call__(self, event: Message | CallbackQuery, bot: Bot) -> bool:
        user_id = event.from_user.id
        now = time.monotonic()

        cached = _admin_cache.get(user_id)
        if cached is not None and now < cached[1]:
            return cached[0]

        try:
            member = await asyncio.wait_for(
                bot.get_chat_member(TELEGRAM_CHANNEL_ID, user_id),
                timeout=_ADMIN_CHECK_TIMEOUT,
            )
            is_admin = member.status in ("administrator", "creator")
            ttl = _ADMIN_CACHE_TTL
        except Exception:
            is_admin = False
            ttl = _ADMIN_CACHE_FAIL_TTL

        _admin_cache[user_id] = (is_admin, now + ttl)
        return is_admin


class IsHR(BaseFilter):
    """True, если пользователю выдана роль HR внутри бота."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return storage.is_hr(event.from_user.id)
