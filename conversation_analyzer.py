from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from loguru import logger

import networkx as nx


MessageID = int


@dataclass
class Message:
    id: MessageID
    reply_to_message_id: Optional[int]
    text: str

    def __hash__(self):
        return self.id


@dataclass
class QuestionAnswers:
    question: str
    answers: list[str]


def all_successors(graph, node):
    visited = set()

    def dfs(current_node):
        if current_node not in visited:
            visited.add(current_node)
            for successor in graph.successors(current_node):
                dfs(successor)

    dfs(node)
    visited.remove(node)
    return list(visited)


async def get_question_answer_pairs(chat_history: list[Message]):
    graph = nx.DiGraph()

    replies = {}

    count = 0
    for msg in chat_history:
        if count % 10000 == 0:
            logger.info(f"Processing messages {count}-{count + 9999}")
        graph.add_node(msg)

        if msg.reply_to_message_id:
            replies.setdefault(msg.reply_to_message_id, []).append(msg)

        if replies_to_current := replies.get(msg.id, []):
            for reply_to_current in replies_to_current:
                graph.add_edge(msg, reply_to_current)

            del replies[msg.id]

        count += 1

    graph.remove_nodes_from(list(nx.isolates(graph)))

    source_nodes = [x for x in graph.nodes if graph.in_degree(x) == 0]

    results: list[QuestionAnswers] = []
    for node, successors in [(n, all_successors(graph, n)) for n in source_nodes]:
        results.append(
            QuestionAnswers(question=node.text, answers=[x.text for x in successors])
        )

    return results
