import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import admin, common, hr, moderation, records_edit, self_apply, topics_listener

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    # Дефолтный таймаут HTTP-сессии в aiogram — 60 секунд: если запрос к
    # api.telegram.org подвисает (нестабильная сеть/провайдер до Telegram),
    # именно столько бот и ждёт, прежде чем упасть с ошибкой — это и
    # ощущалось как "минута на кнопку". Ограничиваем явно и жёстче.
    session = AiohttpSession(timeout=15)
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: сначала слушатель топиков (не мешает остальным чатам),
    # затем общая навигация, модерация и самозапись (не фильтруются по
    # ролям), затем роли admin/hr.
    dp.include_router(topics_listener.router)
    dp.include_router(common.router)
    dp.include_router(moderation.router)
    dp.include_router(self_apply.router)
    dp.include_router(records_edit.router)
    dp.include_router(admin.router)
    dp.include_router(hr.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
