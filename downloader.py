from __future__ import annotations
import asyncio
import json
from pathlib import Path
from dataclasses import asdict, dataclass

from dacite import from_dict
from pyrogram import Client

from decouple import config

from conversation_analyzer import Message

client = Client("josxi", config("API_ID"), config("API_HASH"))


@dataclass
class DBData:
    messages: list[Message]
    next_offset: int


def load() -> DBData:
    raw_data = json.loads(db_path.read_text(encoding="UTF-8"))
    return from_dict(DBData, raw_data)


def dump(db: DBData):
    print("Dumping db...", end="")
    db_path.write_text(json.dumps(asdict(db), indent=2), encoding="UTF-8")
    print(" done.")


database: DBData = DBData(messages=[], next_offset=0)
db_path = Path(__file__).parent / "db.json"
if db_path.exists():
    database = load()


async def analyze_conversation():
    await client.start()
    print(f"Starting at offset {database.next_offset}")

    while True:
        async for m in client.get_chat_history(
            "@botlistchat", limit=10000, offset=database.next_offset
        ):
            database.next_offset += 1
            if database.next_offset % 500 == 0:
                print(database.next_offset)
            if not m.text and not m.caption:
                continue
            msg = Message(
                id=m.id,
                text=m.text or m.caption,
                reply_to_message_id=m.reply_to_message_id,
            )

            database.messages.append(msg)

        if database.next_offset % 1000 == 0:
            dump(database)


if __name__ == "__main__":
    asyncio.run(analyze_conversation())
