from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from conversation_analyzer import QuestionAnswers

INCLUDE_BOTLISTBOT_SEARCH_RESULTS = True


@dataclass
class TrainingItem:
    prompt: str
    answer: str


FORBIDDEN_PREFIXES = [
    "/new",
    "/contribute",
    "/offline",
    "#new",
    "#contribute",
    "#offline",
    "!",
    "Fresh new bots since",
]

FORBIDDEN_REGEXES = [
    re.compile(x, re.MULTILINE | re.IGNORECASE) for x in [r"gave [0-9]+ tacos to"]
]


def should_include_question(item: str) -> bool:
    if item.strip() == "":
        return False

    if any((re.match(pattern, item) for pattern in FORBIDDEN_REGEXES)):
        return False

    if any((item.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)):
        return False

    if "Share your bots, comment, test and have fun" in item:
        return False

    return True


BOT_REGEX = re.compile(
    r"(@[a-zA-Z0-9_]+bot|@bold|@gif|@pic|@like|@sticker|@vid|@vote)", re.IGNORECASE
)


def should_include_answer(item: str) -> bool:
    if any((item.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)):
        return False

    if any((re.match(pattern, item) for pattern in FORBIDDEN_REGEXES)):
        return False

    if "Share your bots, comment, test and have fun" in item:
        return False

    if not BOT_REGEX.search(item) and "t.me/" not in item:
        return False

    if not INCLUDE_BOTLISTBOT_SEARCH_RESULTS:
        if "bots in the @BotList for" in item:
            return False

    return True


REMOVE_PATTERNS = [
    re.compile(x, re.MULTILINE) for x in [r"^.*suggests to search and I found .*?:"]
]


def preprocess(item: str) -> str:
    return re.sub(r"^/s(earch)?(@BotListBot)? ", "", item, re.MULTILINE)


def postprocess(item: str) -> str:
    result = item
    for remove_pattern in REMOVE_PATTERNS:
        result = re.sub(remove_pattern, "", item)
    result = re.sub(r"\n+", "\n", result)
    return result


def clean_qa_pair(qa_pair: QuestionAnswers) -> Optional[TrainingItem]:
    question = postprocess(preprocess(qa_pair.question))
    answers = map(preprocess, qa_pair.answers)

    if not should_include_question(question):
        return None

    answers = list(filter(should_include_answer, answers))
    completion = postprocess("\n".join(answers))

    if completion.strip().replace("\n", "") == "":
        return None

    return TrainingItem(
        prompt=question,
        answer=completion,
    )
