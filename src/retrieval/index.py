"""
FAISS index for fast similarity search over crossword clue embeddings.

Wraps a FAISS IndexFlatIP (inner product) index with metadata storage
for mapping vector indices back to clue-answer pairs.
"""

import os
import json
import numpy as np
import faiss


class ClueIndex:
    """
    A FAISS-backed index that stores clue vectors alongside their metadata
    (answer text, answer length, original clue).

    Usage:
        # Build
        index = ClueIndex(dimension=384)
        index.add(vectors, records)
        index.save("data/indexes/my_index")

        # Load and search
        index = ClueIndex.load("data/indexes/my_index")
        results = index.search(query_vector, top_k=10, answer_length=5)
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = None
        self.metadata = []  # Parallel list: metadata[i] corresponds to vector i

    def add(self, vectors: np.ndarray, records: list[dict]):
        """
        Build the FAISS index from vectors and their associated records.

        Args:
            vectors: numpy array of shape (n, dimension) — the encoded clues.
            records: list of dicts with 'clue', 'answer', 'answer_length'.
                     Must be same length as vectors.
        """
        assert len(vectors) == len(records), \
            f"Vector count ({len(vectors)}) != record count ({len(records)})"

        # Normalize for cosine similarity
        vectors = vectors.copy().astype(np.float32)
        faiss.normalize_L2(vectors)

        # Build the index
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product = cosine sim
        self.index.add(vectors)
        self.metadata = records

        print(f"Index built: {self.index.ntotal:,} vectors")

    def search(self, query_vector: np.ndarray, top_k: int = 10,
               answer_length: int = None) -> list[dict]:
        """
        Search for the most similar clues to a query vector.

        Args:
            query_vector: shape (1, dimension) — the encoded query clue.
            top_k: Number of results to return.
            answer_length: If set, only return answers of this exact length.

        Returns:
            List of dicts with 'answer', 'clue', 'answer_length', 'score'.
        """
        if self.index is None:
            raise RuntimeError("Index not built yet. Call add() or load() first.")

        # Normalize the query
        query = query_vector.copy().astype(np.float32)
        faiss.normalize_L2(query)

        # Search more than needed if filtering by length
        search_k = top_k * 10 if answer_length else top_k
        search_k = min(search_k, self.index.ntotal)

        scores, indices = self.index.search(query, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            record = self.metadata[idx]

            if answer_length and record["answer_length"] != answer_length:
                continue

            results.append({
                "answer": record["answer"],
                "clue": record["clue"],
                "answer_length": record["answer_length"],
                "score": float(score),
            })

            if len(results) >= top_k:
                break

        return results

    def save(self, directory: str):
        """Save the index and metadata to disk."""
        os.makedirs(directory, exist_ok=True)

        faiss.write_index(self.index, os.path.join(directory, "faiss.index"))

        with open(os.path.join(directory, "metadata.json"), "w") as f:
            json.dump(self.metadata, f)

        print(f"Index saved to {directory}/")

    @classmethod
    def load(cls, directory: str) -> "ClueIndex":
        """Load a previously saved index from disk."""
        index_path = os.path.join(directory, "faiss.index")
        meta_path = os.path.join(directory, "metadata.json")

        if not os.path.exists(index_path):
            raise FileNotFoundError(f"No FAISS index found at {index_path}")

        faiss_index = faiss.read_index(index_path)

        with open(meta_path, "r") as f:
            metadata = json.load(f)

        obj = cls(dimension=faiss_index.d)
        obj.index = faiss_index
        obj.metadata = metadata

        print(f"Index loaded: {obj.index.ntotal:,} vectors from {directory}/")
        return obj