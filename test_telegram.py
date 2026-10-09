import os
import asyncio

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = 1458762640  # Pon aquí TU chat_id


async def main():
    bot = Bot(token=TOKEN)

    await bot.send_message(
        chat_id=CHAT_ID,
        text="🤖 ¡Hola! Job Hunter IA está funcionando."
    )


asyncio.run(main())