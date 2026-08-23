from aiogram import F, Router
from aiogram.types import Message

import storage
from config import TELEGRAM_CHANNEL_ID

router = Router()


@router.message(F.chat.id == TELEGRAM_CHANNEL_ID)
async def track_topics(message: Message):
    """
    Telegram Bot API не предоставляет метод для получения списка всех
    топиков форума. Единственный способ их узнать — заметить сообщение,
    отправленное в этом топике (или служебное сообщение о его создании).
    Поэтому бот запоминает топики по мере появления в них активности.
    """
    thread_id = message.message_thread_id

    if thread_id is None:
        storage.register_topic(None, "Общий (General)")
        return

    name = None
    if message.forum_topic_created:
        name = message.forum_topic_created.name
    elif message.reply_to_message and message.reply_to_message.forum_topic_created:
        name = message.reply_to_message.forum_topic_created.name

    if name is None:
        existing = storage.get_topics()
        name = existing.get(thread_id, f"Топик #{thread_id}")

    storage.register_topic(thread_id, name)
