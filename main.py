import asyncio
import sys
from dataclasses import asdict

import typer
from jsonlines import jsonlines

from conversation_analyzer import get_question_answer_pairs
from data_cleaning import clean_qa_pair, TrainingItem
from downloader import load, analyze_conversation

from loguru import logger

from asynctyper import AsyncTyper

app = AsyncTyper()


logger.remove()
logger.add(
    sys.stdout, colorize=True, format="<level>{level} | {message}</level>", level="INFO"
)


@app.command("read-conversations")
async def read_conversations():
    await analyze_conversation()


@app.command("write-conversations")
async def write_conversations():
    data = load().messages
    logger.info(f"Total messages: {len(data)}")
    qa_pairs = await get_question_answer_pairs(data)

    logger.info(f"After analyzing Q/A replies: {len(qa_pairs)}")
    training_items: list[TrainingItem] = []

    rejected = []
    for pair in qa_pairs:
        if result := clean_qa_pair(pair):
            training_items.append(result)
        else:
            rejected.append(pair)

    with jsonlines.open("rejected.jsonl", mode="w") as writer:
        for item in rejected:
            writer.write(asdict(item))

    logger.info(f"Number of items after cleaning: {len(training_items)}")

    with jsonlines.open("completions.jsonl", mode="w") as writer:
        for item in training_items:
            writer.write(asdict(item))

    logger.info(f"Wrote completions.jsonl")


if __name__ == "__main__":
    asyncio.run(app())
