import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import admin, common, hr, topics_listener

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: сначала слушатель топиков (не мешает остальным чатам),
    # затем общий /start и навигация, затем ролевые панели.
    dp.include_router(topics_listener.router)
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(hr.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
