import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
_raw_channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not _raw_channel_id:
    raise RuntimeError("TELEGRAM_CHANNEL_ID не задан в .env")

TELEGRAM_CHANNEL_ID = int(_raw_channel_id)
