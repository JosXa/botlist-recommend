import asyncio
import random
import sys
from loguru import logger
import re

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from decouple import config

from data_cleaning import BOT_REGEX
from recommend import SimilaritySearch

logger.remove()
logger.add(
    sys.stdout, colorize=True, format="<level>{level} | {message}</level>", level="INFO"
)


similarity_search = SimilaritySearch()
dp = Dispatcher()


PREAMBLES_MANY = [
    "How about one of these:",
    "Here are some ideas:",
    "Try one of these bots:",
    "May wanna try one of these:",
    "Give these a shot:",
    "Have you tried any of these yet?",
]
PREAMBLES_ONE = [
    "I only found one that might help:",
    "Unfortunately only one result:",
    "Here, maybe this one:",
]
PREAMBLES_ZERO = [
    "Sorry, I found no results for that :/",
    "Couldn't find anything for that query. Try something else?",
    "Sorry, i don't have anything for that.",
]


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        f"Hi {hbold(message.from_user.full_name)}!\nI can help you find Telegram bots. What are you looking for?"
    )


@dp.message()
async def recommend(message: types.Message) -> None:
    query = message.text
    try:
        found_bots = similarity_search.query_bots(query)

        preamble = random.choice(PREAMBLES_ZERO if len(found_bots) == 0 else PREAMBLES_ONE if len(found_bots) == 1 else PREAMBLES_MANY)

        res = "\n".join([f"({round(sim)}%) {bot}" for sim, bot in found_bots])
        await message.reply(preamble + "\n\n" + res)
    except Exception as err:
        logger.exception(err)
        await message.reply(random.choice(PREAMBLES_ZERO))



async def main() -> None:
    bot = Bot(config("BOT_TOKEN"), parse_mode=ParseMode.HTML)
    logger.info("Listening...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
