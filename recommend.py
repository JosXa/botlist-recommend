import os
import pickle
import re
import sys
from pathlib import Path

import jsonlines
import hnswlib
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import time
from loguru import logger

from data_cleaning import BOT_REGEX

MODEL_NAME = "thenlper/gte-small"
DATASET_PATH = Path(__file__).parent / "completions.jsonl"
INDEX_FILE = Path(__file__).parent / "hnsw_index.bin"
EMBEDDING_DIMENSION = 384
MAX_EF_CONSTRUCTION = 200
M_VALUE = 16
TOP_K_SIMILAR_QUESTIONS = 5


class SimilaritySearch:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.data = self.load_dataset(DATASET_PATH)
        self.num_elements = len(self.data)
        self.index = self.load_or_create_hnsw_index()

    def load_dataset(self, dataset_path):
        with jsonlines.open(dataset_path) as reader:
            return list(reader)

    def load_or_create_hnsw_index(self):
        if os.path.exists(INDEX_FILE):
            logger.info("Loading precomputed index...")
            with open(INDEX_FILE, "rb") as index_f:
                return pickle.load(index_f)
        else:
            logger.info("Computing the index...")
            index = hnswlib.Index(space="cosine", dim=EMBEDDING_DIMENSION)
            self.index_embeddings(index)
            self.save_hnsw_index(index)
            return index

    def index_embeddings(self, index):
        embeddings = []
        for entry in tqdm(self.data, desc="Indexing", unit="data"):
            text = entry["prompt"]
            embedding = self.model.encode(text, convert_to_tensor=False).tolist()
            embeddings.append(embedding)

        embeddings = np.array(embeddings)
        index.init_index(
            max_elements=self.num_elements,
            ef_construction=MAX_EF_CONSTRUCTION,
            M=M_VALUE,
        )
        index.add_items(embeddings)

    def save_hnsw_index(self, index):
        with open(INDEX_FILE, "wb") as index_f:
            pickle.dump(index, index_f)

    def find_similar_questions(self, query_text, top_k=TOP_K_SIMILAR_QUESTIONS):
        query_embedding = self.model.encode(
            query_text, convert_to_tensor=False
        ).tolist()
        labels, distances = self.index.knn_query(query_embedding, k=top_k)

        similar_questions = []

        for label, distance in zip(labels[0], distances[0]):
            prompt = self.data[label]["prompt"]
            answer = self.data[label]["answer"]
            similarity_score = (1 - distance) * 100  # Assuming distance is cosine distance
            similar_questions.append([prompt, answer, similarity_score])

        return similar_questions

    def query_bots(self, query_text, top_k=TOP_K_SIMILAR_QUESTIONS) -> list[tuple[float, str]]:
        similar_questions = self.find_similar_questions(query_text, top_k)

        results = []

        for _, answer, similarity_score in similar_questions:
            bots_in_answer = BOT_REGEX.findall(answer)

            for b in bots_in_answer:
                results.append((similarity_score, b))

        return results



def main():
    similarity_search = SimilaritySearch()

    query = None

    logger.info("Enter q to exit.")
    while True:
        logger.info("===========================")
        query = input("Question: ")
        if query.strip() == "":
            continue
        if query.strip() in ("q", "exit"):
            sys.exit(0)

        results = similarity_search.query_bots(query)
        logger.info("\n".join([f"({round(sim)}%) {bot}" for sim, bot in results]))


if __name__ == "__main__":
    main()
